"""Opt-in real rootless Podman checks using disposable state and no credentials."""
import base64
import errno
import hashlib
import io
import json
import os
from pathlib import Path
import pty
import select
import shlex
import shutil
import signal
import subprocess
import sys
import tarfile
import tempfile
import termios
import time
import unittest
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'network'))
import agent_budgets  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
WRAPPER = ROOT / 'codex-container.sh'
IMAGE = os.environ.get('CODEX_CONTAINER_IMAGE', 'localhost/codex-cli:latest')
ENGINE_IMAGE = os.environ.get('CODEX_CONTAINER_ENGINE_IMAGE', 'localhost/codex-cli-engine:latest')
# A small local image the library copies into its store (pinned, already in the engine).
SAMPLE = os.environ.get('SANDBOX_TEST_ENGINE_SAMPLE', 'docker.io/library/alpine@sha256:'
                        'c64c687cbea9300178b30c95835354e34c4e4febc4badfe27102879de0483b5e')
ENABLED = os.environ.get('CODEX_RUNTIME_TESTS') == '1'


def engine_budgets(env):
    """Delegated controllers and process mechanism of the engine, by the launcher's rule."""
    def info(template):
        return subprocess.run(['podman', 'info', '--format', template], env=env, check=True,
                              capture_output=True, text=True, timeout=60).stdout.strip()
    delegated = agent_budgets.delegated(info('{{.Host.CgroupControllers}}'), info('{{.Host.CgroupManager}}'))
    return delegated, agent_budgets.process_mechanism(delegated, info('{{.Host.Kernel}}'))


def start_crowd(test, env, count):
    """A container of the caller holding count sleeping processes, removed at cleanup."""
    name = 'codex-test-crowd-' + uuid.uuid4().hex[:12]
    test.addCleanup(subprocess.run, ['podman', 'rm', '--force', '--time', '0', '--ignore', name],
                    env=env, capture_output=True, timeout=60)
    subprocess.run(['podman', 'run', '--detach', '--rm', '--name', name, '--userns=keep-id',
                    '--user', f'{os.getuid()}:{os.getgid()}', '--network=none', '--entrypoint', '/bin/sh', IMAGE,
                    '-c', f'i=0; while [ $i -lt {count} ]; do sleep 600 & i=$((i + 1)); done; wait'],
                   env=env, check=True, capture_output=True, text=True, timeout=60)
    deadline = time.monotonic() + 60
    while True:
        top = subprocess.run(['podman', 'top', name, 'pid'], env=env, capture_output=True, text=True, timeout=30)
        # The header line, the shell and its sleeping children.
        if len(top.stdout.splitlines()) >= count + 2 or time.monotonic() > deadline:
            break
        time.sleep(0.5)
    test.assertGreaterEqual(len(top.stdout.splitlines()), count + 2, top.stdout + top.stderr)
    return name


def terminal_shell(command, script, env, cwd, timeout=90):
    """Wait for interactive Bash, then feed one command through a PTY."""
    master, slave = pty.openpty()
    settings = termios.tcgetattr(slave)
    settings[3] &= ~termios.ECHO
    termios.tcsetattr(slave, termios.TCSANOW, settings)
    process = subprocess.Popen(command, stdin=slave, stdout=slave, stderr=slave,
                               cwd=cwd, env=env, start_new_session=True)
    os.close(slave)
    output = bytearray()
    sent = False
    encoded = base64.b64encode(script.encode()).decode()
    payload = f'exec /bin/bash -euc "$(printf %s {encoded} | base64 -d)"\n'.encode()
    deadline = time.monotonic() + timeout
    try:
        while time.monotonic() < deadline:
            if select.select([master], [], [], 0.1)[0]:
                try:
                    chunk = os.read(master, 65536)
                except OSError as exc:
                    if exc.errno == errno.EIO:
                        break
                    raise
                if not chunk:
                    break
                output.extend(chunk)
            if not sent and (b'$ ' in output or b'# ' in output):
                os.write(master, payload)
                sent = True
            if process.poll() is not None and not select.select([master], [], [], 0)[0]:
                break
        else:
            raise AssertionError('Runtime terminal timed out:\n' + output.decode(errors='replace'))
        status = process.wait(timeout=5)
        return subprocess.CompletedProcess(command, status, output.decode(errors='replace'), '')
    finally:
        if process.poll() is None:
            # Terminate this test's process group, including the attached client.
            import signal
            os.killpg(process.pid, signal.SIGTERM)
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()
        os.close(master)


@unittest.skipUnless(ENABLED, 'set CODEX_RUNTIME_TESTS=1 for real rootless Podman checks')
class RuntimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Explicit opt-in failures remain failures, not skipped verification.
        info = subprocess.run(['podman', 'info', '--format',
                               '{{.Host.Security.Rootless}} {{.Host.OS}}'],
                              capture_output=True, text=True, timeout=20)
        if info.returncode or info.stdout.strip() != 'true linux':
            raise AssertionError('Real Linux rootless Podman is required:\n' + info.stdout + info.stderr)
        image = subprocess.run(['podman', 'image', 'exists', IMAGE], timeout=20)
        if image.returncode:
            raise AssertionError('Build the runtime image before opting into tests: ' + IMAGE)

    def setUp(self):
        parent = Path(os.environ.get('CODEX_TEST_ROOT', str(ROOT / '.test-state')))
        parent.mkdir(parents=True, exist_ok=True)
        self.base = Path(tempfile.mkdtemp(prefix='codex-runtime-', dir=parent)).resolve()
        self.addCleanup(shutil.rmtree, self.base)
        self.project = self.base / 'project with spaces'
        self.project.mkdir()
        self.state = self.base / 'private-state'
        self.state.mkdir(mode=0o700)
        self.assertEqual(self.state.stat().st_mode & 0o777, 0o700,
                         'Select a native Linux CODEX_TEST_ROOT or use tests/run-runtime.sh')
        self.env = {k: v for k, v in os.environ.items()
                    if not k.startswith('CODEX_') and k != 'CONTAINER_CONNECTION'}
        self.host_home = self.base / 'synthetic-host-home'
        self.host_home.mkdir(mode=0o700)
        self.env.update(HOME=str(self.host_home), CODEX_HOME=str(self.state), CODEX_CONTAINER_IMAGE=IMAGE,
                        CODEX_YOLO='0', CODEX_CONTAINER_NETWORK='unrestricted', CODEX_CONTAINER_MAINTENANCE='1')

    def shell(self, script, *options, **env):
        return terminal_shell(['bash', str(WRAPPER), '--container-shell', *options],
                              script, self.env | env, self.project)

    def assert_success(self, result):
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def engine(self, *args, **kwargs):
        return subprocess.run(['podman', *args], capture_output=True, text=True,
                              timeout=kwargs.pop('timeout', 30), **kwargs)

    def pipe_shell(self, script, timeout=60):
        return subprocess.run(['bash', str(WRAPPER), '--container-shell'],
                              input=script, capture_output=True, text=True,
                              env=self.env, cwd=self.project, timeout=timeout)

    def start_shell(self, script):
        process = subprocess.Popen(['bash', str(WRAPPER), '--container-shell'],
                                   stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, text=True, env=self.env,
                                   cwd=self.project, start_new_session=True)
        def stop():
            if process.poll() is None:
                process.send_signal(signal.SIGTERM)
                try:
                    process.wait(timeout=25)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
            process.communicate(timeout=5)
        self.addCleanup(stop)
        process.stdin.write(script)
        process.stdin.close()
        process.stdin = None
        return process

    def wait_file(self, path, process):
        deadline = time.monotonic() + 30
        while not path.exists():
            if process.poll() is not None:
                out, err = process.communicate()
                self.fail('Runtime wrapper exited before readiness:\n' + out + err)
            self.assertLess(time.monotonic(), deadline, 'runtime readiness timed out')
            time.sleep(0.05)

    def session_names(self):
        listing = self.engine('ps', '--all', '--format', '{{.Names}}')
        self.assertEqual(listing.returncode, 0, listing.stderr)
        return [name for name in listing.stdout.splitlines()
                if name.startswith(self.project.name + '-')]

    def unique_project(self):
        self.project = self.base / ('project-' + self.base.name)
        self.project.mkdir()

    def test_nonterminal_input_exit_status_and_pty(self):
        self.unique_project()
        result = self.pipe_shell('test ! -t 0\nprintf "pipe payload\\n"\nexit 125\n')
        self.assertEqual(result.returncode, 125, result.stdout + result.stderr)
        self.assertIn('pipe payload\n', result.stdout)
        self.assertEqual(self.session_names(), [])
        source = self.base / 'commands.sh'
        source.write_text('test ! -t 0\nprintf "file payload\\n"\n')
        with source.open() as stream:
            result = subprocess.run(['bash', str(WRAPPER), '--container-shell'],
                                    stdin=stream, capture_output=True, text=True,
                                    env=self.env, cwd=self.project, timeout=60)
        self.assert_success(result)
        self.assertIn('file payload\n', result.stdout)
        self.assert_success(self.shell('test -t 0\ntest -t 1'))

    def test_pseudo_terminals_and_device_masks(self):
        # Interactive tools open their own PTY: the session must allocate one,
        # while /dev/shm and /run/secrets stay empty read-only masks.
        probe = r'''import os
import pathlib
import pty
master, slave = pty.openpty()
assert os.ttyname(slave).startswith('/dev/pts/'), os.ttyname(slave)
os.close(master); os.close(slave)
for path in ('/dev/shm', '/run/secrets'):
    assert list(pathlib.Path(path).iterdir()) == [], path
    try:
        (pathlib.Path(path) / 'probe').write_text('x')
    except OSError:
        pass
    else:
        raise AssertionError(path + ' is writable')
print('pty-and-masks-ok')
'''
        result = self.shell('python3 -c ' + shlex.quote(probe) + '\n')
        self.assert_success(result)
        self.assertIn('pty-and-masks-ok', result.stdout)

    def test_concurrent_reservation_with_stopped_container(self):
        self.unique_project()
        stopped = self.engine('create', '--name', self.project.name + '-08',
                              '--entrypoint', '/bin/true', IMAGE)
        self.assertEqual(stopped.returncode, 0, stopped.stderr)
        stopped_id = stopped.stdout.strip()
        self.addCleanup(self.engine, 'rm', '--force', '--ignore', stopped_id)
        processes = []
        for index in range(2):
            process = self.start_shell(f'touch ready-{index}\nwhile test ! -e release; do sleep 0.05; done\n')
            processes.append(process)
        for index, process in enumerate(processes):
            self.wait_file(self.project / f'ready-{index}', process)
        self.assertEqual(set(self.session_names()),
                         {self.project.name + suffix for suffix in ('-08', '-9', '-10')})
        (self.project / 'release').touch()
        for process in processes:
            out, err = process.communicate(timeout=30)
            self.assertEqual(process.returncode, 0, out + err)
        self.assertEqual(self.session_names(), [self.project.name + '-08'])

    def test_signal_delivery_owned_cleanup_and_stubborn_process(self):
        self.unique_project()
        unrelated = self.engine('create', '--name', self.project.name + '-08',
                                '--entrypoint', '/bin/true', IMAGE)
        self.assertEqual(unrelated.returncode, 0, unrelated.stderr)
        self.addCleanup(self.engine, 'rm', '--force', '--ignore', unrelated.stdout.strip())
        for sig, status in ((signal.SIGTERM, 143), (signal.SIGINT, 130), (signal.SIGHUP, 129)):
            with self.subTest(signal=sig):
                (self.project / 'ready').unlink(missing_ok=True)
                signame = signal.Signals(sig).name[3:]
                process = self.start_shell(f"trap 'printf {signame} > received; exit 0' {signame}\n"
                                           'touch ready\nwhile :; do sleep 0.1; done\n')
                self.wait_file(self.project / 'ready', process)
                process.send_signal(sig)
                out, err = process.communicate(timeout=25)
                self.assertEqual(process.returncode, status, out + err)
                self.assertEqual((self.project / 'received').read_text(), signame)
                self.assertEqual(self.session_names(), [self.project.name + '-08'])
        (self.project / 'ready').unlink()
        process = self.start_shell("trap '' TERM\ntouch ready\nwhile :; do sleep 0.1; done\n")
        self.wait_file(self.project / 'ready', process)
        start = time.monotonic()
        process.send_signal(signal.SIGTERM)
        out, err = process.communicate(timeout=25)
        self.assertEqual(process.returncode, 143, out + err)
        self.assertLess(time.monotonic() - start, 24)
        self.assertEqual(self.session_names(), [self.project.name + '-08'])

    def test_tmpfs_capacities_noexec_and_exhaustion(self):
        script = '''python3 - <<'PYTHON'
import errno, os, shutil, stat, subprocess
for path, expected in [('/tmp', 512 << 20), ('/var/tmp', 512 << 20), ('/run', 32 << 20),
                       ('/codex-home', 512 << 20)]:
    info = os.statvfs(path)
    assert info.f_blocks * info.f_frsize == expected, (path, info)
    assert info.f_flag & os.ST_NOSUID
    assert info.f_flag & os.ST_NODEV
    assert info.f_flag & os.ST_NOEXEC, path
    if path == '/run':
        # Only /tmp, /var/tmp and the home are mode 1777 (contract L7).
        assert not os.access(path, os.W_OK)
        continue
    assert stat.S_IMODE(os.stat(path).st_mode) == 0o1777
    executable = os.path.join(path, 'codex-test-executable')
    shutil.copy('/bin/true', executable)
    os.chmod(executable, 0o755)
    try:
        subprocess.run([executable], check=True)
    except PermissionError as error:
        assert error.errno == errno.EACCES
    else:
        raise AssertionError('execution allowed from ' + path)
try:
    with open('/tmp/exhaust', 'wb', buffering=0) as target:
        block = b'x' * (1024 * 1024)
        for _ in range(514): target.write(block)
except OSError as error:
    assert error.errno == errno.ENOSPC, error
else:
    raise AssertionError('/tmp exceeded its capacity')
finally:
    os.unlink('/tmp/exhaust')
PYTHON
printf persistent > "$CODEX_HOME/capacity-sentinel"
printf workspace > capacity-sentinel
'''
        result = self.pipe_shell('set -e\n' + script)
        self.assert_success(result)
        self.assertEqual((self.state / 'capacity-sentinel').read_text(), 'persistent')
        self.assertEqual((self.project / 'capacity-sentinel').read_text(), 'workspace')
        self.assert_success(self.pipe_shell('''set -e
test ! -e /tmp/exhaust
test ! -e /tmp/codex-test-executable
test ! -e /var/tmp/codex-test-executable
test ! -e /codex-home/codex-test-executable
'''))

    def test_build_context_excludes_sensitive_and_unknown_inputs(self):
        context = self.base / 'build-context'
        context.mkdir()
        shutil.copyfile(ROOT / '.containerignore', context / '.containerignore')
        for relative in ('.git/config', '.codex/auth.json', '.env', 'nested/credentials',
                         'nested/cache/sentinel', '.test-state/sentinel', 'docs/sentinel',
                         'tests/sentinel', 'unknown-file', 'nested/Containerfile',
                         'network/bin/sandbox-egress-guard', 'network/policy.py', 'network/sentinel',
                         'agent/profile.json'):
            path = context / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('DUMMY-NOT-A-CREDENTIAL')
        for name in ('relay.py', 'mux.py'):
            (context / 'network' / name).write_text('# relay input')
        # Only the image recipe, the ignore file and the two relay inputs pass.
        (context / 'Containerfile').write_text(
            'FROM ' + IMAGE + '\nCOPY . /context\n'
            'RUN cd /context && test "$(find . -mindepth 1 -type f | sort | tr \'\\n\' \' \')" = '
            '"./.containerignore ./Containerfile ./network/mux.py ./network/relay.py "\n')
        iidfile = self.base / 'test-image-id'
        def remove_image():
            if iidfile.exists():
                self.engine('rmi', '--force', iidfile.read_text().strip())
        self.addCleanup(remove_image)
        result = self.engine('build', '--no-cache', '--iidfile', str(iidfile),
                             '--file', str(context / 'Containerfile'), str(context), timeout=180)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_image_and_mount_boundaries(self):
        sentinel = self.base / 'outside-sentinel'
        sentinel.write_text('outside')
        script = f'''test "$PWD" = {shlex.quote(str(self.project))}
        test ! -e {shlex.quote(str(sentinel))}
        test "$(id -u)" = {os.getuid()}
        test "$(id -g)" = {os.getgid()}
        test "$(findmnt -n -o OPTIONS / | tr , '\\n' | head -n 1)" = ro
        if touch /usr/codex-runtime-must-not-write 2>/dev/null; then exit 10; fi
        test ! -S /run/podman/podman.sock
        test -z "${{CONTAINER_HOST:-}}"
        command -v podman
        codex --version
        printf owned > owned-file
        '''
        self.assert_success(self.shell(script))
        self.assertEqual((self.project / 'owned-file').read_text(), 'owned')
        self.assertEqual((self.project / 'owned-file').stat().st_uid, os.getuid())
        self.assertEqual((self.project / 'owned-file').stat().st_gid, os.getgid())
        # Host Podman delegation was removed; the old opt-in stops the launch.
        result = self.piped('true\n', CODEX_CONTAINER_PODMAN='1')
        self.assertEqual(result.returncode, 1)
        self.assertIn('CODEX_CONTAINER_PODMAN=1: host Podman delegation was removed', result.stderr)

    def test_state_and_all_ephemeral_locations(self):
        paths = ['/tmp/codex-ephemeral', '/var/tmp/codex-ephemeral', '/codex-home/codex-ephemeral']
        create = '\n'.join(f'printf temporary > {shlex.quote(p)}' for p in paths)
        absent = '\n'.join(f'test ! -e {shlex.quote(p)}' for p in paths)
        self.assert_success(self.shell('printf persistent > "$CODEX_HOME/sentinel"\n' + create))
        self.assertEqual((self.state / 'sentinel').read_text(), 'persistent')
        self.assert_success(self.shell('test "$(cat "$CODEX_HOME/sentinel")" = persistent\n' + absent))
        self.assertEqual(self.state.stat().st_uid, os.getuid())

    def test_real_worktrees(self):
        # The exposed parent holds only the repositories, not the synthetic host
        # home with its toolchain library.
        main = self.base / 'repositories/main'
        main.parent.mkdir()
        subprocess.run(['git', 'init', '-q', str(main)], check=True)
        subprocess.run(['git', '-C', str(main), '-c', 'user.name=Test',
                        '-c', 'user.email=test@example.invalid', 'commit', '--allow-empty', '-qm', 'initial'], check=True)
        self.project = self.base / 'repositories/linked'
        subprocess.run(['git', '-C', str(main), 'worktree', 'add', '-qb', 'linked', str(self.project)], check=True)
        self.assert_success(self.shell('git status --porcelain\ngit rev-parse --git-common-dir\nprintf worktree > worktree-file',
                                       '--container-git-worktree'))
        self.assertEqual((self.project / 'worktree-file').read_text(), 'worktree')
        self.assertEqual((self.project / 'worktree-file').stat().st_uid, os.getuid())
        self.assertNotEqual(self.shell('git status --porcelain').returncode, 0)

    def launch_socket(self):
        """The launch engine's Unix socket in this runner: a Unix CONTAINER_HOST, else the runtime directory's."""
        connection = self.env.get('CONTAINER_HOST', '')
        if connection.startswith('unix:///'):
            return connection.removeprefix('unix://')
        return str(Path(os.environ.get('XDG_RUNTIME_DIR', f'/run/user/{os.getuid()}')) / 'podman/podman.sock')

    def test_containerized_caller_with_remapped_socket(self):
        # A wrapper inside a container launches through a remapped launch socket;
        # the session it starts gets no Podman socket.
        query = subprocess.run(['podman', '--remote', '--url', 'unix://' + self.launch_socket(),
                                'info', '--format', '{{.Host.RemoteSocket.Path}}'],
                               capture_output=True, text=True, timeout=20)
        self.assertEqual(query.returncode, 0, query.stderr)
        host_socket = query.stdout.strip()
        self.assertTrue(host_socket.startswith('/'), host_socket)
        visible = '/run/codex-test-service/socket.sock'
        self.assertNotEqual(host_socket, visible)
        command = ['podman', 'run', '--rm', '--interactive', '--tty', '--read-only',
                   '--userns=keep-id', '--user', f'{os.getuid()}:{os.getgid()}',
                   '--volume', f'{ROOT}:{ROOT}:ro',
                   '--volume', f'{self.base}:{self.base}:rw',
                   '--volume', f'{host_socket}:{visible}:rw',
                   '--workdir', str(self.project),
                   '--env', 'CONTAINER_HOST=unix://' + visible,
                   '--env', 'CODEX_HOME=' + str(self.state),
                   '--env', 'HOME=' + str(self.host_home),
                   '--env', 'CODEX_CONTAINER_IMAGE=' + IMAGE,
                   '--env', 'CODEX_CONTAINER_NETWORK=unrestricted',
                   '--entrypoint', '/bin/bash', IMAGE, str(WRAPPER), '--container-shell']
        self.assert_success(terminal_shell(command,
            'test ! -S /run/podman/podman.sock\ntest -z "${CONTAINER_HOST:-}"\nprintf nested > nested-file',
            self.env, self.project))
        self.assertEqual((self.project / 'nested-file').read_text(), 'nested')
        self.assertEqual((self.project / 'nested-file').stat().st_uid, os.getuid())

    # Session hardening baseline (B01-B05), ported from claude-container.
    def piped(self, script, timeout=90, **env):
        return subprocess.run(['bash', str(WRAPPER), '--container-shell'], input=script,
                              capture_output=True, text=True, env=self.env | env,
                              cwd=self.project, timeout=timeout)

    def engine_budgets(self):
        return engine_budgets(self.env)

    def test_effective_hardening_and_budgets(self):
        # Budgets apply as the engine allows: cgroup limits only for delegated
        # controllers, the process rlimit as fallback, and a notice otherwise.
        delegated, mechanism = self.engine_budgets()
        script = """python3 - "$@" <<'CHECK'
import pathlib, sys
memory, nano, pids = map(int, sys.argv[1:4])
delegated, mechanism = sys.argv[4].split(','), sys.argv[5]
status = dict(line.split(':', 1) for line in pathlib.Path('/proc/self/status').read_text().splitlines())
assert all(int(status[k], 16) == 0 for k in ('CapInh', 'CapPrm', 'CapEff', 'CapBnd', 'CapAmb')), status
assert int(status['NoNewPrivs']) == 1
root = pathlib.Path('/sys/fs/cgroup')
assert pathlib.Path('/proc/self/cgroup').read_text() == '0::/\\n'
def limit(name):
    path = root / name
    return path.read_text().split() if path.exists() else ['max']
if 'memory' in delegated:
    assert int(limit('memory.max')[0]) == memory
else:
    assert limit('memory.max') == ['max'], limit('memory.max')
quota, *period = limit('cpu.max')
if 'cpu' in delegated:
    assert int(quota) * 10**9 == nano * int(period[0])
else:
    assert quota == 'max', quota
if mechanism == 'cgroup':
    assert int(limit('pids.max')[0]) == pids
else:
    assert limit('pids.max') == ['max'], limit('pids.max')
if mechanism == 'rlimit':
    line = next(l for l in pathlib.Path('/proc/self/limits').read_text().splitlines() if l.startswith('Max processes'))
    assert line.split()[2:4] == [str(pids), str(pids)], line
print('EFFECTIVE_HARDENING_OK')
CHECK
git --version >/dev/null && openspec --version >/dev/null && codex --version >/dev/null
"""
        cases = ((dict(), (4 << 30, 2 * 10**9, 512)),
                 (dict(CODEX_CONTAINER_MEMORY_LIMIT='1536m', CODEX_CONTAINER_CPU_LIMIT='1.5',
                       CODEX_CONTAINER_PIDS_LIMIT='256'), (1536 << 20, 1500000000, 256)))
        for env, expected in cases:
            with self.subTest(env=env):
                arguments = 'set -- ' + ' '.join(map(shlex.quote, [*map(str, expected),
                                                 ','.join(delegated) or 'none', mechanism])) + '\n'
                result = self.piped(arguments + script, **env)
                self.assert_success(result)
                self.assertIn('EFFECTIVE_HARDENING_OK', result.stdout)
                for budget, controller in (('memory', 'memory'), ('CPU', 'cpu')):
                    notice = f'agent {budget} budget not enforced'
                    if controller in delegated:
                        self.assertNotIn(notice, result.stderr)
                    else:
                        self.assertIn(notice, result.stderr)
                rlimit = f'agent process budget enforced through the process rlimit ({expected[2]} tasks'
                self.assertEqual(rlimit in result.stderr, mechanism == 'rlimit', result.stderr)
                self.assertEqual('agent process budget not enforced' in result.stderr,
                                 mechanism == 'none', result.stderr)
        if mechanism == 'none':
            return
        # A process budget is enforced, not just reported.
        result = self.piped('python3 - <<\'CHECK\'\nimport subprocess\nchildren = []\ntry:\n'
                            '    for _ in range(200):\n        children.append(subprocess.Popen(["sleep", "30"]))\n'
                            'except (BlockingIOError, OSError):\n    print("PIDS_BUDGET_ENFORCED")\n'
                            'finally:\n    [child.kill() for child in children]\nCHECK\n',
                            CODEX_CONTAINER_PIDS_LIMIT='128')
        self.assert_success(result)
        self.assertIn('PIDS_BUDGET_ENFORCED', result.stdout)

    def test_tools_and_codex_sandbox_without_capabilities(self):
        script = """git init -q repo && git -C repo -c user.name=t -c user.email=t@example.invalid commit -q --allow-empty -m x
openspec --version >/dev/null
bwrap --ro-bind / / --dev /dev --proc /proc --unshare-all true && echo BWRAP_OK
codex sandbox -- sh -c 'echo CODEX_SANDBOX_RAN; touch denied-file 2>/dev/null && echo CODEX_SANDBOX_WRITE_ALLOWED || echo CODEX_SANDBOX_WRITE_DENIED'
"""
        result = self.piped(script, timeout=120)
        self.assert_success(result)
        for marker in ('BWRAP_OK', 'CODEX_SANDBOX_RAN', 'CODEX_SANDBOX_WRITE_DENIED'):
            self.assertIn(marker, result.stdout, result.stderr)
        self.assertFalse((self.project / 'denied-file').exists())

    def test_process_rlimit_counts_per_container(self):
        # set-process-limits-inside-containers, design D4: on the rlimit fallback, other
        # containers of the user do not consume the session's budget. A limit applied at
        # creation would count them, and the session could not even start.
        _, mechanism = self.engine_budgets()
        if mechanism != 'rlimit':
            self.skipTest('the engine does not use the process rlimit fallback')
        start_crowd(self, self.env, 150)
        result = self.piped('python3 - <<\'CHECK\'\nimport subprocess\nchildren = []\n'
                            'def spawn(total):\n    try:\n        while len(children) < total:\n'
                            '            children.append(subprocess.Popen(["sleep", "60"]))\n'
                            '    except (BlockingIOError, OSError):\n        pass\n    return len(children)\n'
                            'first, second = spawn(100), spawn(200)\n[child.kill() for child in children]\n'
                            'print("PROCESSES", first, second)\nCHECK\n', CODEX_CONTAINER_PIDS_LIMIT='128')
        self.assert_success(result)
        counts = next(line.split()[1:] for line in result.stdout.splitlines() if line.startswith('PROCESSES'))
        first, second = map(int, counts)
        self.assertEqual(first, 100, result.stdout)
        # The session's own processes count as well: the shell, Python and the init process.
        self.assertTrue(115 <= second < 128, result.stdout)

    def test_session_lifetime_limit_and_early_exit(self):
        started = time.monotonic()
        result = self.piped('sleep 60\n', CODEX_CONTAINER_RUN_TIMEOUT='3')
        self.assertLess(time.monotonic() - started, 45)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(f'session lifetime limit reached (3 s); exit status {result.returncode}', result.stderr)
        print(f'lifetime expiry status: {result.returncode}')
        self.assertEqual(self.session_names(), [])
        result = self.piped('exit 7\n', CODEX_CONTAINER_RUN_TIMEOUT='30')
        self.assertEqual(result.returncode, 7)
        self.assertNotIn('lifetime limit', result.stderr)

    def test_sensitive_workspace_refused_before_engine(self):
        result = self.piped('true\n', HOME=str(self.project))
        self.assertEqual(result.returncode, 1)
        self.assertIn('refusing sensitive workspace ' + str(self.project), result.stderr)
        self.assertEqual(self.session_names(), [])

    # Toolchain library

    def toolchain(self, *args, **env):
        return subprocess.run(['bash', str(WRAPPER), '--container-toolchain', *args], cwd=self.project,
                              env=self.env | env, text=True, capture_output=True, timeout=300)

    def archive_recipe(self, name, commands, **values):
        buffer = io.BytesIO()
        with tarfile.open(fileobj=buffer, mode='w:gz') as archive:
            for directory in (name + '-1', name + '-1/bin'):
                info = tarfile.TarInfo(directory)
                info.type, info.mode = tarfile.DIRTYPE, 0o755
                archive.addfile(info)
            for command, output in commands.items():
                data = ('#!/bin/sh\necho ' + output + '-"$*"\n').encode()
                info = tarfile.TarInfo(name + '-1/bin/' + command)
                info.size, info.mode = len(data), 0o755
                archive.addfile(info, io.BytesIO(data))
        path = self.base / (name + '.tar.gz')
        path.write_bytes(buffer.getvalue())
        recipe = {'schema': 1, 'name': name, 'version': '1', 'default': True, 'path': ['bin'],
                  'env': {name.upper() + '_HOME': {'toolchain': ''}}, 'check': [next(iter(commands)), 'check'],
                  'source': {'archive': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                             'strip_components': 1}}
        recipe.update(values)
        recipe_path = self.base / (name + '.json')
        recipe_path.write_text(json.dumps(recipe))
        return recipe_path

    def test_toolchain_library_sources_environment_and_read_only_mount(self):
        library = self.host_home / '.local/share/sandbox-toolchains'
        self.assert_success(self.toolchain('add', str(self.archive_recipe('hello', {'hello': 'hello'}))))
        # A default toolchain providing node and python3 never replaces the runtime's own.
        self.assert_success(self.toolchain('add', str(self.archive_recipe(
            'shadow', {'node': 'fake-node', 'python3': 'fake-python'}, env={}))))
        failing = self.archive_recipe('broken', {'broken': 'broken'}, check=['false'], env={})
        result = self.toolchain('add', str(failing))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('toolchain check failed for broken', result.stderr)
        self.assertFalse((library / 'broken').exists())
        context = self.base / 'image-context'
        (context / 'opt/imgtool/bin').mkdir(parents=True)
        (context / 'opt/imgtool/bin/imgtool').write_text('#!/bin/sh\necho image-tool\n')
        (context / 'opt/imgtool/bin/imgtool').chmod(0o755)
        (context / 'Containerfile').write_text('FROM scratch\nCOPY opt /opt\n')
        image = 'localhost/codex-toolchain-test-' + uuid.uuid4().hex
        self.addCleanup(self.engine, 'image', 'rm', '--force', '--ignore', image + ':latest', timeout=60)
        self.assert_success(self.engine('build', '--tag', image + ':latest', str(context), timeout=120))
        digest = self.engine('image', 'inspect', '--format', '{{.Digest}}', image + ':latest').stdout.strip()
        recipe = self.base / 'imgtool.json'
        recipe.write_text(json.dumps({'schema': 1, 'name': 'imgtool', 'version': '1', 'default': False,
                                      'source': {'image': image + '@' + digest, 'path': '/opt/imgtool'},
                                      'check': ['imgtool']}))
        self.assert_success(self.toolchain('add', str(recipe)))
        listing = self.toolchain('list')
        self.assert_success(listing)
        for name in ('hello', 'shadow', 'imgtool'):
            self.assertIn(name + '\t', listing.stdout)
        result = self.shell('''test "$(hello a)" = hello-a
test "$HELLO_HOME" = /toolchains/hello
test "$(command -v node)" = /usr/local/bin/node
test "$(command -v python3)" = /usr/bin/python3
test "$(. /toolchains/shadow/env.sh && node b)" = fake-node-b
test "$(. /toolchains/imgtool/env.sh && imgtool)" = image-tool
if command -v imgtool; then exit 9; fi
grep -q 'hello 1' /toolchains/toolchains.md
python3 -c 'import json; assert [t["name"] for t in json.load(open("/toolchains/index.json"))["toolchains"]] == ["hello", "imgtool", "shadow"]'
if touch /toolchains/new 2>/dev/null; then exit 10; fi
if rm /toolchains/hello/bin/hello 2>/dev/null; then exit 11; fi
test -x /toolchains/hello/bin/hello
echo toolchains-ok
''')
        self.assert_success(result)
        self.assertIn('toolchains-ok', result.stdout)
        self.assert_success(self.toolchain('remove', 'imgtool'))
        self.assertFalse((library / 'imgtool').exists())

    def test_toolchain_library_can_be_omitted(self):
        result = self.shell('test ! -e /toolchains\necho omitted\n', CODEX_CONTAINER_TOOLCHAINS='0')
        self.assert_success(result)
        self.assertIn('omitted', result.stdout)



@unittest.skipUnless(ENABLED, 'set CODEX_RUNTIME_TESTS=1 for real rootless Podman checks')
class SessionEngineTests(unittest.TestCase):
    """The session container engine on a real rootless engine (session-container-engine)."""

    @classmethod
    def setUpClass(cls):
        for image in (ENGINE_IMAGE, SAMPLE):
            if subprocess.run(['podman', 'image', 'exists', image], capture_output=True).returncode:
                raise unittest.SkipTest('prepare ' + image + ' in the engine first')
        cls.sample_id = subprocess.run(['podman', 'image', 'inspect', '--format', '{{.Id}}', SAMPLE],
                                       capture_output=True, text=True, check=True).stdout.strip()

    def setUp(self):
        # The default runtime mode mounts the checkout read-only: the workspace lives
        # in the runner's native volume, as for RuntimeTests.
        workspace_root = Path(os.environ.get('CODEX_TEST_ROOT', str(ROOT / '.test-state')))
        workspace_root.mkdir(parents=True, exist_ok=True)
        self.base = Path(tempfile.mkdtemp(prefix='engine-', dir=workspace_root))
        self.addCleanup(shutil.rmtree, self.base, True)
        self.project = self.base / 'project'
        self.project.mkdir()
        # Bind sources (the session's hosts file, the store) must exist at the same
        # path for the engine service: the disposable runner supplies a native volume.
        self.native = Path(tempfile.mkdtemp(prefix='sandbox-engine-', dir=os.environ.get('SANDBOX_TEST_STATE_ROOT')))
        self.addCleanup(shutil.rmtree, self.native, True)
        self.host_home = self.native / 'home'
        self.host_home.mkdir(mode=0o700)
        self.env = {'PATH': os.environ['PATH'], 'HOME': str(self.host_home), 'TMPDIR': str(self.native),
                    'CODEX_CONTAINER_NETWORK': 'unrestricted', 'CODEX_CONTAINER_MAINTENANCE': '1',
                    'CODEX_CONTAINER_IMAGE': IMAGE, 'CODEX_CONTAINER_ENGINE_IMAGE': ENGINE_IMAGE,
                    'CODEX_CONTAINER_STATE_DIR': str(self.native / 'state')}
        if os.environ.get('CONTAINER_HOST'):
            self.env['CONTAINER_HOST'] = os.environ['CONTAINER_HOST']
        self.add_image('sample', 'localhost/sandbox-test-sample:1')

    def toolchain(self, *args):
        # Operator recipes stay outside the directory the command runs from.
        result = subprocess.run([sys.executable, '-I', str(ROOT / 'setup/toolchains.py'), *args], env=self.env,
                                cwd=self.project, capture_output=True, text=True, timeout=300)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result

    def add_image(self, name, reference):
        recipe = self.native / (name + '.json')
        recipe.write_text(json.dumps({
            'schema': 2, 'name': name, 'version': '1', 'default': False,
            'images': [{'local': 'sha256:' + self.sample_id.removeprefix('sha256:'), 'name': reference}],
            'check': ['podman', 'run', '--rm', '--network=none', reference, 'true']}))
        self.toolchain('add', str(recipe))
        self.addCleanup(subprocess.run, [sys.executable, '-I', str(ROOT / 'setup/toolchains.py'), 'remove', name],
                        env=self.env, cwd=self.project, capture_output=True, timeout=300)

    def shell(self, script, timeout=180):
        return subprocess.run([str(WRAPPER), '--container-shell'], cwd=self.project, env=self.env,
                              input='set -Eeuo pipefail\n' + script, text=True, capture_output=True, timeout=timeout)

    def assert_success(self, result):
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def engines(self):
        listing = subprocess.run(['podman', 'ps', '--all', '--filter', 'label=sandbox-engine.owner',
                                  '--format', '{{.Names}}'], capture_output=True, text=True, check=True).stdout
        return [name for name in listing.split() if name.startswith('project-engine-')]

    def test_session_engine_runs_library_images_inside_the_session_boundaries(self):
        # session-container-engine: Loopback endpoint / Library images run offline from a read-only store /
        # Nested containers have private process and host-name views / Engine mounts only the workspace /
        # Engine carries no secrets / Session-owned engine storage.
        result = self.shell(r"""
test "$CONTAINER_HOST" = tcp://127.0.0.1:2375
test "$DOCKER_HOST" = tcp://127.0.0.1:2375
test "$(podman info --format '{{.Host.Security.Rootless}}')" = true
view=$(podman run --rm --network=none localhost/sandbox-test-sample:1 sh -c \
  'echo "$(cat /proc/1/comm) $(ls /proc | grep -c "^[0-9]") $(cat /proc/sys/kernel/hostname) $(ls -A /run/secrets 2>/dev/null | wc -l)"')
set -- $view
test "$1" = sh && test "$2" -le 4 && test "$3" != "$(cat /proc/sys/kernel/hostname)" && test "$4" = 0
echo "NESTED_VIEW $view"
podman run --rm --network=none -v "$PWD:$PWD" -w "$PWD" localhost/sandbox-test-sample:1 sh -c 'echo nested > nested-file'
test "$(stat -c %u nested-file)" = "$(id -u)"
podman run --rm --network=none -v /etc:/outside:ro localhost/sandbox-test-sample:1 grep -q k8s-file /outside/containers/containers.conf
! podman rmi localhost/sandbox-test-sample:1
podman image exists localhost/sandbox-test-sample:1
# Builds and the extraction of new layers (pull, load) chroot (design D4).
mkdir .build-context && printf 'FROM localhost/sandbox-test-sample:1\nRUN echo built > /built\n' > .build-context/Containerfile
podman build --quiet --pull=never --tag localhost/sandbox-test-built:1 .build-context >/dev/null
test "$(podman run --rm --network=none localhost/sandbox-test-built:1 cat /built)" = built
podman save --quiet --output .built.tar localhost/sandbox-test-built:1
podman rmi localhost/sandbox-test-built:1 >/dev/null
podman load --quiet --input .built.tar >/dev/null
podman image exists localhost/sandbox-test-built:1
rm -rf .build-context .built.tar
echo ENGINE_SESSION_OK
""")
        self.assert_success(result)
        self.assertIn('ENGINE_SESSION_OK', result.stdout)
        self.assertEqual((self.project / 'nested-file').stat().st_uid, os.getuid())
        self.assertEqual(self.engines(), [])

    def test_engine_process_rlimit_counts_per_container(self):
        # set-process-limits-inside-containers, design D4: on the rlimit fallback, an engine
        # session starts and runs a nested container beside a container holding more
        # processes than its budget. A limit applied at creation would count that container.
        if engine_budgets(self.env)[1] != 'rlimit':
            self.skipTest('the engine does not use the process rlimit fallback')
        start_crowd(self, self.env, 520)
        result = self.shell('test "$(grep "^Max processes" /proc/self/limits | tr -s " " | cut -d" " -f3,4)" = "512 512"\n'
                            'podman run --rm --network=none localhost/sandbox-test-sample:1 true\n'
                            'echo NESTED_BESIDE_CROWD_OK\n')
        self.assert_success(result)
        self.assertIn('NESTED_BESIDE_CROWD_OK', result.stdout)
        self.assertEqual(self.engines(), [])

    def test_no_engine_without_library_images(self):
        # session-container-engine: Library without images.
        self.toolchain('remove', 'sample')
        result = self.shell('test -z "${CONTAINER_HOST+x}${DOCKER_HOST+x}"\necho NO_ENGINE_OK\n')
        self.assert_success(result)
        self.assertNotIn('container engine', result.stderr)

    def test_live_image_and_isolated_concurrent_sessions(self):
        # session-container-engine: Image added during a session / Two sessions.
        marker = self.project / '.image-added'
        first = subprocess.Popen([str(WRAPPER), '--container-shell'], cwd=self.project, env=self.env,
                                 stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self.addCleanup(lambda: first.poll() is None and first.kill())
        first.stdin.write(r"""set -Eeuo pipefail
podman run -d --name first-session-marker --network=none localhost/sandbox-test-sample:1 sleep 120 >/dev/null
echo FIRST_READY
while [ ! -e .image-added ]; do sleep 0.2; done
podman run --rm --network=none localhost/sandbox-test-live:1 true
echo LIVE_IMAGE_OK
podman rm -f -t 0 first-session-marker >/dev/null
""")
        first.stdin.close()
        first.stdin = None
        self.assertEqual(first.stdout.readline().strip(), 'FIRST_READY', first.stderr.read() if first.poll() else '')
        second = self.shell('! podman container exists first-session-marker\n'
                            'test -z "$(podman ps --all --quiet)"\necho SECOND_ISOLATED\n')
        self.assert_success(second)
        self.add_image('live', 'localhost/sandbox-test-live:1')
        marker.touch()
        stdout, stderr = first.communicate(timeout=180)
        self.assertEqual(first.returncode, 0, stdout + stderr)
        self.assertIn('LIVE_IMAGE_OK', stdout)
        self.assertEqual(self.engines(), [])


if __name__ == '__main__':
    unittest.main()
