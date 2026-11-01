"""Opt-in real rootless Podman checks using disposable state and no credentials."""
import base64
import errno
import os
from pathlib import Path
import pty
import select
import shlex
import shutil
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
    """Wait for Bash, then feed one command through the wrapper's required TTY."""
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
                        CODEX_CONTAINER_PODMAN='0', CODEX_YOLO='0')
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
        self.assertEqual(result.returncode, 0, result.stdout)

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
                   '--entrypoint', '/bin/bash', IMAGE, str(WRAPPER), '--container-shell']
        self.assert_success(terminal_shell(command,
            'test -S /run/podman/podman.sock\npodman info >/dev/null\nprintf nested > nested-file',
            self.env, self.project))
        self.assertEqual((self.project / 'nested-file').read_text(), 'nested')
        self.assertEqual((self.project / 'nested-file').stat().st_uid, os.getuid())


if __name__ == '__main__':
    unittest.main()
