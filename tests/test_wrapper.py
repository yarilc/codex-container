"""Wrapper contracts with synthetic Podman responses; no engine or credentials."""
import itertools
import json
import os
from pathlib import Path
import socket
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
WRAPPER = ROOT / 'codex-container.sh'
FAKE = r'''#!/usr/bin/env python3
import json, os, pathlib, sys
args = sys.argv[1:]
with open(os.environ['FAKE_LOG'], 'a') as log:
    log.write(json.dumps(args) + '\n')
if args[0] == 'info':
    print(os.environ.get('FAKE_INFO', 'true linux false'))
    sys.exit(int(os.environ.get('FAKE_INFO_STATUS', '0')))
elif args[:2] == ['--remote', '--url']:
    print(os.environ.get('FAKE_SOCKET_INFO', 'true\n/host/podman.sock'))
    sys.exit(int(os.environ.get('FAKE_SOCKET_STATUS', '0')))
elif args[0] == 'run':
    print('mask:' + oct(os.umask(0)))
    sys.exit(int(os.environ.get('FAKE_EXIT', '0')))
'''


class WrapperTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='codex-wrapper-')
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.bin = self.base / 'bin'
        self.bin.mkdir()
        fake = self.bin / 'podman'
        fake.write_text(FAKE)
        fake.chmod(0o755)
        self.project = self.base / 'parent with spaces' / 'my project'
        self.project.mkdir(parents=True)
        self.state = self.base / 'state'
        self.log = self.base / 'calls.jsonl'
        self.env = {k: v for k, v in os.environ.items()
                    if not k.startswith(('CODEX_', 'CONTAINER_', 'FAKE_'))}
        self.env.update(PATH=str(self.bin) + ':' + self.env['PATH'],
                        CODEX_HOME=str(self.state), FAKE_LOG=str(self.log))
        self.sock = socket.socket(socket.AF_UNIX)
        self.sock_path = self.base / 'service.sock'
        self.sock.bind(str(self.sock_path))
        self.addCleanup(self.sock.close)

    def run_wrapper(self, *args, **env):
        self.log.unlink(missing_ok=True)
        return subprocess.run(['bash', str(WRAPPER), *args], cwd=self.project,
                              env=self.env | env, text=True, capture_output=True,
                              timeout=10, umask=0o022)

    def calls(self):
        return [json.loads(line) for line in self.log.read_text().splitlines()] if self.log.exists() else []

    def assert_rejected(self, result):
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertIn('codex-container:', result.stderr)
        self.assertFalse(any(call[0] in ('image', 'build', 'ps', 'run') for call in self.calls()))

    def test_help_without_engine_or_state(self):
        result = self.run_wrapper('--container-help', CODEX_YOLO='invalid', CONTAINER_CONNECTION='bad')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.calls(), [])
        self.assertFalse(self.state.exists())

    def test_help_without_podman_installed(self):
        minimal = self.base / 'minimal-bin'
        minimal.mkdir()
        for name in ('dirname', 'sed', 'cat'):
            (minimal / name).symlink_to('/usr/bin/' + name)
        result = subprocess.run(['/bin/bash', str(WRAPPER), '--container-help'],
                                env=self.env | {'PATH': str(minimal)}, cwd=self.project,
                                capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(self.state.exists())
        self.assertEqual(self.calls(), [])

    def test_valid_launch_engine_without_delegation(self):
        result = self.run_wrapper('exec', 'prompt with spaces', '')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.calls()[0][0], 'info')
        self.assertFalse(any(c[0] == '--remote' for c in self.calls()))
        self.assertEqual(self.calls()[-1][-3:], ['exec', 'prompt with spaces', ''])

    def test_explicit_build_and_image_override(self):
        result = self.run_wrapper('--container-build', '--version', CODEX_CONTAINER_IMAGE='test/custom:tag')
        self.assertEqual(result.returncode, 0, result.stderr)
        build = next(c for c in self.calls() if c[0] == 'build')
        self.assertEqual(build, ['build', '--tag', 'test/custom:tag', '--file',
                                 str(ROOT / 'Containerfile'), str(ROOT)])
        self.assertEqual(self.run_args()[-2:], ['test/custom:tag', '--version'])

    def test_engine_failure_matrix_before_image_operations(self):
        infos = ['false linux false', 'true darwin false', '', 'true linux',
                 'true linux maybe', 'yes linux false', 'true linux false extra',
                 'true linux false\ntrue linux false']
        for shell, build, access, yolo, info in itertools.product(
                (False, True), (False, True), ('0', '1'), ('0', '1'), infos):
            with self.subTest(shell=shell, build=build, access=access, yolo=yolo, info=info):
                args = (['--container-shell'] if shell else []) + (['--container-build'] if build else [])
                result = self.run_wrapper(*args, FAKE_INFO=info,
                                          CODEX_CONTAINER_PODMAN=access, CODEX_YOLO=yolo)
                self.assert_rejected(result)
                self.assertFalse(self.state.exists())
                self.assertFalse(any(c[0] == '--remote' for c in self.calls()))
        self.assert_rejected(self.run_wrapper(FAKE_INFO_STATUS='125'))

    def test_unsupported_contexts(self):
        for env in ({'CONTAINER_CONNECTION': 'named'},
                    {'CONTAINER_HOST': 'ssh://host'},
                    {'CONTAINER_HOST': 'tcp://localhost:1234'},
                    {'CONTAINER_HOST': 'unix://relative'},
                    {'CONTAINER_HOST': 'unix:///'},
                    {'FAKE_INFO': 'true linux true'}):
            with self.subTest(env=env):
                self.assert_rejected(self.run_wrapper(**env))

    def test_explicit_unix_launch_connection(self):
        result = self.run_wrapper(CONTAINER_HOST='unix:///visible/launch.sock', FAKE_INFO='true linux true')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(any(c[0] == '--remote' for c in self.calls()))
        self.assertIn('--unsetenv', self.calls()[-1])


    def run_args(self):
        return next(call for call in self.calls() if call[0] == 'run')

    def test_private_state_creation_and_mask(self):
        result = self.run_wrapper()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.state.stat().st_mode & 0o777, 0o700)
        self.assertEqual(self.state.stat().st_uid, os.getuid())
        self.assertIn(f'{self.state}:/codex-home/.codex:rw', self.run_args())
        self.assertIn('mask:0o22', result.stdout)

    def test_existing_state_relative_symlink_and_spaces(self):
        target = self.base / 'private state with spaces'
        target.mkdir(mode=0o700)
        (target / 'sentinel').write_text('keep')
        link = self.project / 'state-link'
        link.symlink_to(target, target_is_directory=True)
        for path in ('state-link', str(link), str(target)):
            with self.subTest(path=path):
                result = self.run_wrapper(CODEX_HOME=path)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn(f'{target}:/codex-home/.codex:rw', self.run_args())
                self.assertEqual((target / 'sentinel').read_text(), 'keep')

    def test_invalid_state_before_image_operations(self):
        for mode in (0o755, 0o770, 0o707):
            self.state.mkdir(exist_ok=True)
            self.state.chmod(mode)
            result = self.run_wrapper('--container-build')
            self.assert_rejected(result)
            self.assertEqual(self.state.stat().st_mode & 0o777, mode)
        self.state.rmdir()
        self.state.write_text('untouched')
        self.assert_rejected(self.run_wrapper())
        self.assertEqual(self.state.read_text(), 'untouched')
        self.state.unlink()
        self.state.symlink_to(self.base / 'absent')
        self.assert_rejected(self.run_wrapper())
        self.assertTrue(self.state.is_symlink())

    @unittest.skipIf(os.getuid() == 0, 'root bypasses ordinary access checks')
    def test_inaccessible_state(self):
        self.state.mkdir(mode=0o700)
        for mode in (0o000, 0o500):
            with self.subTest(mode=mode):
                self.state.chmod(mode)
                try:
                    self.assert_rejected(self.run_wrapper())
                finally:
                    self.state.chmod(0o700)

    def install_stat_fixture(self, field, value):
        # Simulate metadata unavailable to an unprivileged test process.
        # This verifies branching, not a real chown or non-Unix filesystem.
        stat = self.bin / 'stat'
        stat.write_text('#!/usr/bin/env python3\n'
                        'import os, sys\n'
                        f'if sys.argv[2] == {field!r}: print({value!r})\n'
                        'else: os.execv("/usr/bin/stat", ["stat", *sys.argv[1:]])\n')
        stat.chmod(0o755)

    def test_wrong_owner_controlled_fixture(self):
        self.install_stat_fixture('%u', str(os.getuid() + 1))
        result = self.run_wrapper()
        self.assert_rejected(result)
        self.assertIn('belong to the calling user', result.stderr)

    def test_non_enforcing_modes_controlled_fixture(self):
        self.install_stat_fixture('%a', '777')
        result = self.run_wrapper()
        self.assert_rejected(result)
        self.assertIn('filesystem that enforces Unix permissions', result.stderr)

    def test_default_state_and_help_with_invalid_state(self):
        env = self.env.copy()
        env.pop('CODEX_HOME')
        env['HOME'] = str(self.base)
        result = subprocess.run(['bash', str(WRAPPER)], env=env, cwd=self.project,
                                capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(f'{self.base}/.codex:/codex-home/.codex:rw', self.run_args())
        self.state.write_text('not a directory')
        result = self.run_wrapper('--container-help')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.state.read_text(), 'not a directory')


    def test_socket_override_and_remapped_source(self):
        result = self.run_wrapper(CODEX_CONTAINER_PODMAN='1',
                                  CODEX_CONTAINER_PODMAN_SOCKET=str(self.sock_path),
                                  CONTAINER_HOST='unix:///different/launch.sock',
                                  FAKE_INFO='true linux true',
                                  FAKE_SOCKET_INFO='true\n/host/socket with spaces.sock')
        self.assertEqual(result.returncode, 0, result.stderr)
        query = next(c for c in self.calls() if c[0] == '--remote')
        self.assertEqual(query[2], 'unix://' + str(self.sock_path))
        self.assertIn('/host/socket with spaces.sock:/run/podman/podman.sock:rw', self.run_args())
        self.assertNotIn(f'{self.sock_path}:/run/podman/podman.sock:rw', self.run_args())
        self.assertIn('CONTAINER_HOST=unix:///run/podman/podman.sock', self.run_args())

    def test_socket_fallbacks_and_symlink(self):
        runtime = self.base / 'runtime'
        (runtime / 'podman').mkdir(parents=True)
        link = runtime / 'podman' / 'podman.sock'
        link.symlink_to(self.sock_path)
        cases = [dict(CONTAINER_HOST='unix://' + str(link), FAKE_INFO='true linux true'),
                 dict(XDG_RUNTIME_DIR=str(runtime)),
                 dict(XDG_RUNTIME_DIR=str(runtime), CODEX_CONTAINER_PODMAN_SOCKET='')]
        for env in cases:
            with self.subTest(env=env):
                result = self.run_wrapper(CODEX_CONTAINER_PODMAN='1', **env)
                self.assertEqual(result.returncode, 0, result.stderr)
                query = next(c for c in self.calls() if c[0] == '--remote')
                self.assertEqual(query[2], 'unix://' + str(self.sock_path))
        # A controlled resolver records selection without depending on whether
        # the machine running tests happens to have a real UID service socket.
        resolver = self.bin / 'readlink'
        selection = self.base / 'selected-path'
        resolver.write_text('#!/usr/bin/env python3\n'
                            'import pathlib, sys\n'
                            f'pathlib.Path({str(selection)!r}).write_text(sys.argv[-1])\n'
                            f'print({str(self.sock_path)!r})\n')
        resolver.chmod(0o755)
        for xdg in ('', None):
            self.env.pop('XDG_RUNTIME_DIR', None)
            env = {} if xdg is None else dict(XDG_RUNTIME_DIR=xdg)
            result = self.run_wrapper(CODEX_CONTAINER_PODMAN='1', **env)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(selection.read_text(), f'/run/user/{os.getuid()}/podman/podman.sock')

    def test_invalid_socket_paths(self):
        file = self.base / 'ordinary-file'
        file.write_text('not a socket')
        for path in ('relative.sock', str(file), str(self.base / 'missing'),
                     str(self.base / 'absent' / 'missing.sock')):
            with self.subTest(path=path):
                result = self.run_wrapper(CODEX_CONTAINER_PODMAN='1', CODEX_CONTAINER_PODMAN_SOCKET=path)
                self.assert_rejected(result)
                self.assertIn(path, result.stderr)

    @unittest.skipIf(os.getuid() == 0, 'root bypasses ordinary socket access checks')
    def test_inaccessible_socket(self):
        self.sock_path.chmod(0)
        try:
            self.assert_rejected(self.run_wrapper(CODEX_CONTAINER_PODMAN='1',
                                                 CODEX_CONTAINER_PODMAN_SOCKET=str(self.sock_path)))
        finally:
            self.sock_path.chmod(0o700)

    def test_service_failures_before_image_operations(self):
        infos = ['false\n/host/socket', 'true', 'true\n', 'true\nrelative',
                 '', 'maybe\n/host/socket', 'true\n/host/socket\nextra']
        for shell, build, info in itertools.product((False, True), (False, True), infos):
            with self.subTest(shell=shell, build=build, info=info):
                args = (['--container-shell'] if shell else []) + (['--container-build'] if build else [])
                self.assert_rejected(self.run_wrapper(
                    *args, CODEX_CONTAINER_PODMAN='1',
                    CODEX_CONTAINER_PODMAN_SOCKET=str(self.sock_path), FAKE_SOCKET_INFO=info))
        self.assert_rejected(self.run_wrapper(CODEX_CONTAINER_PODMAN='1',
                                             CODEX_CONTAINER_PODMAN_SOCKET=str(self.sock_path),
                                             FAKE_SOCKET_STATUS='125'))

    def test_permissions_independent_and_exact_opt_in(self):
        for access, yolo in itertools.product(('', '0', '1', 'true', 'yes', 'unexpected'), ('0', '1')):
            with self.subTest(access=access, yolo=yolo):
                result = self.run_wrapper('exec', 'a prompt', '', CODEX_YOLO=yolo,
                                          CODEX_CONTAINER_PODMAN=access,
                                          CODEX_CONTAINER_PODMAN_SOCKET=str(self.sock_path) if access == '1' else '/invalid')
                self.assertEqual(result.returncode, 0, result.stderr)
                args = self.run_args()
                self.assertEqual('--yolo' in args, yolo == '1')
                self.assertEqual(any(c[0] == '--remote' for c in self.calls()), access == '1')
                self.assertEqual('--unsetenv' in args, access != '1')
                self.assertEqual(args[-3:], ['exec', 'a prompt', ''])
                self.assertIn('--read-only', args)
                self.assertNotIn('--privileged', args)
                self.assertNotIn('--security-opt', args)
        result = self.run_wrapper('--container-shell', 'ignored', CODEX_YOLO='1')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn('--yolo', self.run_args())
        self.assertNotIn('ignored', self.run_args())

    def test_workspace_parent_symlink_and_mount_boundary(self):
        for flags, mount in (([], self.project), (['--container-git-worktree'] * 2, self.project.parent)):
            result = self.run_wrapper('--container-shell', *flags)
            self.assertEqual(result.returncode, 0, result.stderr)
            args = self.run_args()
            self.assertEqual(args[args.index('--workdir') + 1], str(self.project))
            volumes = [args[i + 1] for i, arg in enumerate(args[:-1]) if arg == '--volume']
            self.assertEqual(volumes, [f'{mount}:{mount}:rw', f'{self.state}:/codex-home/.codex:rw'])
            self.assertIn(f'{os.getuid()}:{os.getgid()}', args)
            self.assertIn('--read-only-tmpfs=false', args)
            self.assertEqual(sum(a == '--tmpfs' for a in args), 4)
        alias = self.base / 'alias'
        alias.symlink_to(self.project, target_is_directory=True)
        self.project = alias
        result = self.run_wrapper('--container-git-worktree')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(f'{alias.resolve().parent}:{alias.resolve().parent}:rw', self.run_args())


if __name__ == '__main__':
    unittest.main()
