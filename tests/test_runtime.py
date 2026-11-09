"""Opt-in real rootless Podman checks using disposable state and no credentials."""
import base64
import errno
import os
from pathlib import Path
import pty
import select
import shlex
import shutil
import signal
import subprocess
import tempfile
import termios
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
WRAPPER = ROOT / 'codex-container.sh'
IMAGE = os.environ.get('CODEX_CONTAINER_IMAGE', 'localhost/codex-cli:latest')
ENABLED = os.environ.get('CODEX_RUNTIME_TESTS') == '1'


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
        self.env.update(CODEX_HOME=str(self.state), CODEX_CONTAINER_IMAGE=IMAGE,
                        CODEX_CONTAINER_PODMAN='0', CODEX_YOLO='0',
                        CODEX_CONTAINER_NETWORK='unrestricted', CODEX_CONTAINER_MAINTENANCE='1')
        self.socket = os.environ.get('CODEX_CONTAINER_PODMAN_SOCKET', '')
        if not self.socket:
            connection = self.env.get('CONTAINER_HOST', '')
            if connection.startswith('unix:///'):
                self.socket = connection.removeprefix('unix://')
            else:
                self.socket = str(Path(os.environ.get('XDG_RUNTIME_DIR', f'/run/user/{os.getuid()}'))
                                  / 'podman/podman.sock')

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

    def test_tmpfs_capacities_execution_and_exhaustion(self):
        script = '''python3 - <<'PYTHON'
import errno, os, stat
for path, expected in [('/tmp', 512 * 1024 * 1024), ('/var/tmp', 512 * 1024 * 1024),
                       ('/run', 32 * 1024 * 1024)]:
    info = os.statvfs(path)
    assert info.f_blocks * info.f_frsize == expected, (path, info)
    assert stat.S_IMODE(os.stat(path).st_mode) == 0o1777
    assert info.f_flag & os.ST_NOSUID
    assert info.f_flag & os.ST_NODEV
for path in ('/tmp', '/var/tmp', '/codex-home'):
    assert not os.statvfs(path).f_flag & os.ST_NOEXEC
try:
    with open('/run/exhaust', 'wb', buffering=0) as target:
        block = b'x' * (1024 * 1024)
        for _ in range(34): target.write(block)
except OSError as error:
    assert error.errno == errno.ENOSPC, error
else:
    raise AssertionError('/run exceeded its capacity')
finally:
    os.unlink('/run/exhaust')
PYTHON
for directory in /tmp /var/tmp /codex-home; do
    printf '#!/bin/sh\\nexit 0\\n' > "$directory/executable"
    chmod +x "$directory/executable"
    "$directory/executable" || exit 1
done
printf persistent > "$CODEX_HOME/capacity-sentinel"
printf workspace > capacity-sentinel
'''
        result = self.pipe_shell('set -e\n' + script)
        self.assert_success(result)
        self.assertEqual((self.state / 'capacity-sentinel').read_text(), 'persistent')
        self.assertEqual((self.project / 'capacity-sentinel').read_text(), 'workspace')
        self.assert_success(self.pipe_shell('''set -e
test ! -e /run/exhaust
test ! -e /tmp/executable
test ! -e /var/tmp/executable
python3 - <<'PYTHON'
import os
info = os.statvfs('/var/tmp')
assert info.f_blocks * info.f_frsize == 536870912
assert not info.f_flag & os.ST_NOEXEC
PYTHON
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

    def test_state_and_all_ephemeral_locations(self):
        paths = ['/tmp/codex-ephemeral', '/var/tmp/codex-ephemeral',
                 '/run/codex-ephemeral', '/codex-home/codex-ephemeral']
        create = '\n'.join(f'printf temporary > {shlex.quote(p)}' for p in paths)
        absent = '\n'.join(f'test ! -e {shlex.quote(p)}' for p in paths)
        self.assert_success(self.shell('printf persistent > "$CODEX_HOME/sentinel"\n' + create))
        self.assertEqual((self.state / 'sentinel').read_text(), 'persistent')
        self.assert_success(self.shell('test "$(cat "$CODEX_HOME/sentinel")" = persistent\n' + absent))
        self.assertEqual(self.state.stat().st_uid, os.getuid())

    def test_real_worktrees(self):
        main = self.base / 'main'
        subprocess.run(['git', 'init', '-q', str(main)], check=True)
        subprocess.run(['git', '-C', str(main), '-c', 'user.name=Test',
                        '-c', 'user.email=test@example.invalid', 'commit', '--allow-empty', '-qm', 'initial'], check=True)
        self.project = self.base / 'linked'
        subprocess.run(['git', '-C', str(main), 'worktree', 'add', '-qb', 'linked', str(self.project)], check=True)
        self.assert_success(self.shell('git status --porcelain\ngit rev-parse --git-common-dir\nprintf worktree > worktree-file',
                                       '--container-git-worktree'))
        self.assertEqual((self.project / 'worktree-file').read_text(), 'worktree')
        self.assertEqual((self.project / 'worktree-file').stat().st_uid, os.getuid())
        self.assertNotEqual(self.shell('git status --porcelain').returncode, 0)

    def test_child_container_host_bind(self):
        script = '''test -S /run/podman/podman.sock
        test "$CONTAINER_HOST" = unix:///run/podman/podman.sock
        podman run --rm --read-only --userns=keep-id --user "$(id -u):$(id -g)" \\
            --volume "$PWD:$PWD:rw" --workdir "$PWD" --entrypoint /bin/sh \\
            ''' + shlex.quote(IMAGE) + ''' -ec 'printf child > child-file'
        test "$(cat child-file)" = child
        '''
        self.assert_success(self.shell(script, CODEX_CONTAINER_PODMAN='1',
                                       CODEX_CONTAINER_PODMAN_SOCKET=self.socket))
        self.assertEqual((self.project / 'child-file').read_text(), 'child')
        self.assertEqual((self.project / 'child-file').stat().st_uid, os.getuid())

    def test_containerized_caller_with_remapped_socket(self):
        query = subprocess.run(['podman', '--remote', '--url', 'unix://' + self.socket,
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
                   '--env', 'CODEX_CONTAINER_IMAGE=' + IMAGE,
                   '--env', 'CODEX_CONTAINER_PODMAN=1',
                   '--env', 'CODEX_CONTAINER_NETWORK=unrestricted',
                   '--entrypoint', '/bin/bash', IMAGE, str(WRAPPER), '--container-shell']
        self.assert_success(terminal_shell(command,
            'test -S /run/podman/podman.sock\npodman info >/dev/null\nprintf nested > nested-file',
            self.env, self.project))
        self.assertEqual((self.project / 'nested-file').read_text(), 'nested')
        self.assertEqual((self.project / 'nested-file').stat().st_uid, os.getuid())

    # Session hardening baseline (B01-B05), ported from claude-container.
    def piped(self, script, timeout=90, **env):
        return subprocess.run(['bash', str(WRAPPER), '--container-shell'], input=script,
                              capture_output=True, text=True, env=self.env | env,
                              cwd=self.project, timeout=timeout)

    def test_effective_hardening_and_budgets(self):
        script = """python3 - "$@" <<'CHECK'
import pathlib, sys
memory, nano, pids = map(int, sys.argv[1:4])
status = dict(line.split(':', 1) for line in pathlib.Path('/proc/self/status').read_text().splitlines())
assert all(int(status[k], 16) == 0 for k in ('CapInh', 'CapPrm', 'CapEff', 'CapBnd', 'CapAmb')), status
assert int(status['NoNewPrivs']) == 1
root = pathlib.Path('/sys/fs/cgroup')
assert pathlib.Path('/proc/self/cgroup').read_text() == '0::/\\n'
assert int((root / 'memory.max').read_text()) == memory
assert int((root / 'pids.max').read_text()) == pids
quota, period = (root / 'cpu.max').read_text().split()
assert int(quota) * 10**9 == nano * int(period)
print('EFFECTIVE_HARDENING_OK')
CHECK
git --version >/dev/null && openspec --version >/dev/null && codex --version >/dev/null
"""
        cases = ((dict(), (4 << 30, 2 * 10**9, 512)),
                 (dict(CODEX_CONTAINER_MEMORY_LIMIT='1536m', CODEX_CONTAINER_CPU_LIMIT='1.5',
                       CODEX_CONTAINER_PIDS_LIMIT='256'), (1536 << 20, 1500000000, 256)))
        for env, expected in cases:
            for service in ('0', '1'):
                with self.subTest(env=env, service=service):
                    arguments = 'set -- ' + ' '.join(map(str, expected)) + '\n'
                    result = self.piped(arguments + script, CODEX_CONTAINER_PODMAN=service,
                                        CODEX_CONTAINER_PODMAN_SOCKET=self.socket, **env)
                    self.assert_success(result)
                    self.assertIn('EFFECTIVE_HARDENING_OK', result.stdout)
        # A process budget is enforced, not just reported.
        result = self.piped('python3 - <<\'CHECK\'\nimport subprocess\nchildren = []\ntry:\n'
                            '    for _ in range(80):\n        children.append(subprocess.Popen(["sleep", "30"]))\n'
                            'except (BlockingIOError, OSError):\n    print("PIDS_BUDGET_ENFORCED")\n'
                            'finally:\n    [child.kill() for child in children]\nCHECK\n',
                            CODEX_CONTAINER_PIDS_LIMIT='32')
        self.assert_success(result)
        self.assertIn('PIDS_BUDGET_ENFORCED', result.stdout)

    def test_tools_and_codex_sandbox_without_capabilities(self):
        script = """git init -q repo && git -C repo -c user.name=t -c user.email=t@example.invalid commit -q --allow-empty -m x
openspec --version >/dev/null
bwrap --ro-bind / / --dev /dev --proc /proc --unshare-all true && echo BWRAP_OK
codex sandbox -- sh -c 'echo CODEX_SANDBOX_RAN; touch denied-file 2>/dev/null && echo CODEX_SANDBOX_WRITE_ALLOWED || echo CODEX_SANDBOX_WRITE_DENIED'
podman run --rm --pull=never --entrypoint true """ + shlex.quote(IMAGE) + """ && echo DELEGATED_CHILD_OK
"""
        result = self.piped(script, timeout=120, CODEX_CONTAINER_PODMAN='1', CODEX_CONTAINER_PODMAN_SOCKET=self.socket)
        self.assert_success(result)
        for marker in ('BWRAP_OK', 'CODEX_SANDBOX_RAN', 'CODEX_SANDBOX_WRITE_DENIED', 'DELEGATED_CHILD_OK'):
            self.assertIn(marker, result.stdout, result.stderr)
        self.assertFalse((self.project / 'denied-file').exists())

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


if __name__ == '__main__':
    unittest.main()
