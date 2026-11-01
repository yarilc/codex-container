"""Wrapper contracts with synthetic Podman responses; no engine or credentials."""
import itertools
import json
import os
from pathlib import Path
import pty
import signal
import socket
import subprocess
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
WRAPPER = ROOT / 'codex-container.sh'
FAKE = r'''#!/usr/bin/env python3
import json, os, pathlib, signal, sys, time
args = sys.argv[1:]
with open(os.environ['FAKE_LOG'], 'a') as log:
    log.write(json.dumps(args) + '\n')
if args[0] == 'info':
    sys.stdout.write(os.environ['FAKE_INFO_RAW']) if 'FAKE_INFO_RAW' in os.environ else print(os.environ.get('FAKE_INFO', 'true linux false'))
    sys.exit(int(os.environ.get('FAKE_INFO_STATUS', '0')))
elif args[:2] == ['--remote', '--url']:
    sys.stdout.write(os.environ['FAKE_SOCKET_INFO_RAW']) if 'FAKE_SOCKET_INFO_RAW' in os.environ else print(os.environ.get('FAKE_SOCKET_INFO', 'true\n/host/podman.sock'))
    sys.exit(int(os.environ.get('FAKE_SOCKET_STATUS', '0')))
elif args[0] == 'ps':
    print(os.environ.get('FAKE_NAMES', ''))
    sys.exit(int(os.environ.get('FAKE_LIST_STATUS', '0')))
elif args[0] == 'image':
    sys.exit(int(os.environ.get('FAKE_IMAGE_STATUS', '0')))
elif args[0] == 'build':
    sys.exit(int(os.environ.get('FAKE_BUILD_STATUS', '0')))
elif args[:2] == ['container', 'exists']:
    sys.exit(int(os.environ.get('FAKE_EXISTS_STATUS', '0')))
elif args[0] == 'create':
    calls = [json.loads(line) for line in pathlib.Path(os.environ['FAKE_LOG']).read_text().splitlines()]
    attempt = sum(c[0] == 'create' for c in calls)
    if attempt <= int(os.environ.get('FAKE_COLLISIONS', '0')):
        print('synthetic collision', file=sys.stderr)
        sys.exit(125)
    status = int(os.environ.get('FAKE_CREATE_STATUS', '0'))
    if status:
        print('synthetic create failure', file=sys.stderr)
        sys.exit(status)
    cid = 'a' * 64
    pathlib.Path(args[args.index('--cidfile') + 1]).write_text(cid + '\n')
    if os.environ.get('FAKE_CREATE_BARRIER'):
        barrier = pathlib.Path(os.environ['FAKE_CREATE_BARRIER'])
        barrier.with_suffix('.ready').touch()
        while not barrier.with_suffix('.release').exists(): time.sleep(0.01)
    print(cid)
elif args[0] in ('kill', 'rm'):
    if os.environ.get('FAKE_CONTROL_STALL') == args[0]: time.sleep(30)
    status = int(os.environ.get('FAKE_' + args[0].upper() + '_STATUS', '0'))
    if not status and os.environ.get('FAKE_SESSION'):
        if args[0] == 'rm' or not os.environ.get('FAKE_IGNORE_SIGNAL'):
            pathlib.Path(os.environ['FAKE_SESSION'] + '.done').touch()
    sys.exit(status)
elif args[0] in ('run', 'start'):
    if os.environ.get('FAKE_CLIENT_IGNORE_TERM'):
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
    print('mask:' + oct(os.umask(0)))
    if os.environ.get('FAKE_ECHO_INPUT'):
        sys.stdout.write(sys.stdin.read())
    if os.environ.get('FAKE_SESSION'):
        session = pathlib.Path(os.environ['FAKE_SESSION'])
        session.with_suffix('.ready').touch()
        while not session.with_suffix('.done').exists(): time.sleep(0.01)
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
        self.assertFalse(any(call[0] in ('image', 'build', 'ps', 'run', 'create', 'start') for call in self.calls()))

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
        self.assertEqual(self.run_args()[-3:], ['exec', 'prompt with spaces', ''])

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
        self.assertIn('--unsetenv', self.run_args())

    def test_slash_only_endpoints_rejected_before_podman(self):
        endpoints = ('unix://', 'unix:///', 'unix:////', 'unix:////////', 'unix://relative')
        for shell, build, endpoint in itertools.product((False, True), (False, True), endpoints):
            with self.subTest(shell=shell, build=build, endpoint=endpoint):
                options = (['--container-shell'] if shell else []) + (['--container-build'] if build else [])
                self.assert_rejected(self.run_wrapper(*options, CONTAINER_HOST=endpoint))
                self.assertEqual(self.calls(), [])
                self.assertFalse(self.state.exists())
        for endpoint in ('unix:///run/user/1000/podman/podman.sock', 'unix:////visible/socket with spaces.sock'):
            result = self.run_wrapper(CONTAINER_HOST=endpoint, FAKE_INFO='true linux true')
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_verification_normal_terminators_and_socket_spaces(self):
        for shell, build, launch_end, socket_end in itertools.product((False, True), (False, True), ('', '\n'), ('', '\n')):
            with self.subTest(shell=shell, build=build, launch_end=launch_end, socket_end=socket_end):
                options = (['--container-shell'] if shell else []) + (['--container-build'] if build else [])
                result = self.run_wrapper(*options, CODEX_CONTAINER_PODMAN='1',
                                          CODEX_CONTAINER_PODMAN_SOCKET=str(self.sock_path),
                                          FAKE_INFO_RAW='true linux false' + launch_end,
                                          FAKE_SOCKET_INFO_RAW='true\n/host/socket with spaces.sock' + socket_end)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn('/host/socket with spaces.sock:/run/podman/podman.sock:rw', self.run_args())

    def test_extra_launch_records_are_not_trimmed(self):
        valid = 'true linux false'
        invalid = [valid + '\n\n', valid + '\n\n\n', '\n' + valid + '\n',
                   valid + '\nextra\n', valid + '\r\n', 'true\nlinux false\n',
                   'true linux false extra\n', '\n', '']
        for shell, build, access, response in itertools.product((False, True), (False, True), ('0', '1'), invalid):
            with self.subTest(shell=shell, build=build, access=access, response=response):
                options = (['--container-shell'] if shell else []) + (['--container-build'] if build else [])
                self.assert_rejected(self.run_wrapper(*options, CODEX_CONTAINER_PODMAN=access,
                                                      FAKE_INFO_RAW=response))
                self.assertFalse(any(c[0] == '--remote' for c in self.calls()))
                self.assertFalse(self.state.exists())

    def test_extra_delegation_records_are_not_trimmed(self):
        valid = 'true\n/host/podman.sock'
        invalid = [valid + '\n\n', valid + '\n\n\n', '\n' + valid + '\n',
                   'true\n\n/host/podman.sock\n', valid + '\nextra\n', valid + '\r\n',
                   'true\n', 'true\nrelative\n', 'false\n/host/podman.sock\n', '']
        for shell, build, response in itertools.product((False, True), (False, True), invalid):
            with self.subTest(shell=shell, build=build, response=response):
                options = (['--container-shell'] if shell else []) + (['--container-build'] if build else [])
                self.assert_rejected(self.run_wrapper(*options, CODEX_CONTAINER_PODMAN='1',
                                                      CODEX_CONTAINER_PODMAN_SOCKET=str(self.sock_path),
                                                      FAKE_SOCKET_INFO_RAW=response))
                self.assertFalse(self.state.exists())

    def test_failed_queries_with_valid_looking_raw_output(self):
        for shell, build, endpoint in itertools.product((False, True), (False, True), ('launch', 'delegation')):
            with self.subTest(shell=shell, build=build, endpoint=endpoint):
                options = (['--container-shell'] if shell else []) + (['--container-build'] if build else [])
                response = {'FAKE_INFO_RAW': 'true linux false\n', 'FAKE_INFO_STATUS': '125'} if endpoint == 'launch' else {
                    'FAKE_SOCKET_INFO_RAW': 'true\n/host/podman.sock\n', 'FAKE_SOCKET_STATUS': '125'}
                self.assert_rejected(self.run_wrapper(*options, CODEX_CONTAINER_PODMAN='1',
                                                      CODEX_CONTAINER_PODMAN_SOCKET=str(self.sock_path), **response))

    def test_yolo_case_insensitive_and_delegation_independent(self):
        values = ('1', 'true', 'TrUe', 'yes', 'YeS', '', '0', 'false', 'FaLsE', 'no', 'nO')
        for shell, access, value in itertools.product((False, True), ('1', 'TrUe', 'YeS'), values):
            with self.subTest(shell=shell, access=access, value=value):
                options = ['--container-shell'] if shell else []
                result = self.run_wrapper(*options, 'exec', 'prompt with spaces', '',
                                          CODEX_YOLO=value, CODEX_CONTAINER_PODMAN=access,
                                          CODEX_CONTAINER_PODMAN_SOCKET=str(self.sock_path))
                self.assertEqual(result.returncode, 0, result.stderr)
                args = self.run_args()
                self.assertEqual('--yolo' in args, not shell and value.lower() in ('1', 'true', 'yes'))
                self.assertEqual(any(c[0] == '--remote' for c in self.calls()), access == '1')
                self.assertIn('--read-only', args)
                self.assertIn(f'{self.project}:{self.project}:rw', args)
                if not shell:
                    self.assertEqual(args[-3:], ['exec', 'prompt with spaces', ''])
                    if value.lower() in ('1', 'true', 'yes'):
                        self.assertEqual(args[-4], '--yolo')
        result = self.run_wrapper('--yolo', 'exec', 'prompt', CODEX_YOLO='FaLsE')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.run_args()[-4:], ['localhost/codex-cli:latest', '--yolo', 'exec', 'prompt'])
        for shell, value in itertools.product((False, True), ('enabled', '2', ' true ', 'YeS ', ' FaLsE')):
            options = ['--container-shell'] if shell else []
            result = self.run_wrapper(*options, CODEX_YOLO=value)
            self.assert_rejected(result)
            self.assertEqual(self.calls(), [])
            self.assertIn('CODEX_YOLO must be', result.stderr)


    def run_args(self):
        return next(call for call in self.calls() if call[0] == 'create')

    def creates(self):
        return [c for c in self.calls() if c[0] == 'create']

    def wait_path(self, path, process, timeout=5):
        deadline = time.monotonic() + timeout
        while not path.exists():
            self.assertIsNone(process.poll(), 'wrapper exited before fixture barrier')
            self.assertLess(time.monotonic(), deadline, 'fixture barrier timed out')
            time.sleep(0.01)

    def start_wrapper(self, *args, **env):
        process = subprocess.Popen(['bash', str(WRAPPER), *args], cwd=self.project,
                                   env=self.env | env, stdin=subprocess.DEVNULL,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   text=True, start_new_session=True)
        def stop():
            if process.poll() is None:
                os.killpg(process.pid, signal.SIGKILL)
            process.communicate(timeout=5)
        self.addCleanup(stop)
        return process

    def assert_owned_cleanup(self):
        removals = [c for c in self.calls() if c[0] == 'rm']
        self.assertEqual(len(removals), 1)
        self.assertEqual(removals[0][-1], 'a' * 64)
        self.assertEqual(removals[0][removals[0].index('--time') + 1], '0')
        cidfile = Path(self.run_args()[self.run_args().index('--cidfile') + 1])
        self.assertFalse(cidfile.parent.exists())

    def test_all_names_decimal_bounds_and_listing_error(self):
        names = '\n'.join(['my-project-08', 'my-project-2', 'my-project-no',
                           'my-project-9999999999', 'other-80', 'my-project--1'])
        result = self.run_wrapper(FAKE_NAMES=names)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('--all', next(c for c in self.calls() if c[0] == 'ps'))
        self.assertIn('my-project-9', self.run_args())
        result = self.run_wrapper(FAKE_LIST_STATUS='125')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Cannot list', result.stderr)
        self.assertEqual(self.creates(), [])

    def test_root_prefix_and_numeric_upper_bound(self):
        result = subprocess.run(['bash', str(WRAPPER)], cwd='/', env=self.env,
                                text=True, capture_output=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('codex-container-0', self.run_args())
        result = self.run_wrapper(FAKE_NAMES='my-project-999999999')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('my-project-1000000000', self.run_args())

    def test_collision_retries_and_exhaustion(self):
        result = self.run_wrapper(FAKE_COLLISIONS='2')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual([c[c.index('--name') + 1] for c in self.creates()],
                         ['my-project-0', 'my-project-1', 'my-project-2'])
        self.assert_owned_cleanup()
        result = self.run_wrapper(FAKE_COLLISIONS='20')
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(len(self.creates()), 20)
        self.assertIn('20 attempts', result.stderr)
        self.assertFalse(any(c[0] in ('start', 'rm') for c in self.calls()))

    def test_creation_and_collision_query_failures(self):
        for exists in ('1', '125'):
            with self.subTest(exists=exists):
                result = self.run_wrapper(FAKE_CREATE_STATUS='42', FAKE_EXISTS_STATUS=exists)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(len(self.creates()), 1)
                self.assertIn('synthetic create failure', result.stderr)
                self.assertFalse(any(c[0] in ('start', 'rm') for c in self.calls()))
                if exists == '1':
                    self.assertEqual(result.returncode, 42)
                else:
                    self.assertIn('Cannot verify', result.stderr)

    def test_application_status_and_cleanup_failure(self):
        for status, removal in itertools.product((0, 23, 125), ('0', '125')):
            with self.subTest(status=status, removal=removal):
                result = self.run_wrapper(FAKE_EXIT=str(status), FAKE_RM_STATUS=removal)
                self.assertEqual(result.returncode, status, result.stderr)
                self.assertEqual(len(self.creates()), 1)
                self.assert_owned_cleanup()
                self.assertEqual('Cannot remove owned' in result.stderr, removal != '0')

    def test_signals_during_creation(self):
        for sig, status in ((signal.SIGTERM, 143), (signal.SIGINT, 130), (signal.SIGHUP, 129)):
            with self.subTest(sig=sig):
                self.log.unlink(missing_ok=True)
                barrier = self.base / f'create-{sig}'
                process = self.start_wrapper(FAKE_CREATE_BARRIER=str(barrier))
                self.wait_path(barrier.with_suffix('.ready'), process)
                process.send_signal(sig)
                # The client completes only after the parent has received the signal.
                time.sleep(0.05)
                barrier.with_suffix('.release').touch()
                out, err = process.communicate(timeout=10)
                self.assertEqual(process.returncode, status, out + err)
                self.assertFalse(any(c[0] == 'start' for c in self.calls()))
                self.assert_owned_cleanup()

    def test_attached_signals_both_modes(self):
        for shell, sig in itertools.product((False, True),
                                           (signal.SIGTERM, signal.SIGINT, signal.SIGHUP)):
            expected = {signal.SIGTERM: 143, signal.SIGINT: 130, signal.SIGHUP: 129}[sig]
            with self.subTest(shell=shell, sig=sig):
                self.log.unlink(missing_ok=True)
                session = self.base / f'session-{shell}-{sig}'
                process = self.start_wrapper(*(['--container-shell'] if shell else []),
                                             FAKE_SESSION=str(session))
                self.wait_path(session.with_suffix('.ready'), process)
                process.send_signal(sig)
                out, err = process.communicate(timeout=10)
                self.assertEqual(process.returncode, expected, out + err)
                kills = [c for c in self.calls() if c[0] == 'kill']
                self.assertEqual(kills, [['kill', '--signal', signal.Signals(sig).name[3:], 'a' * 64]])
                self.assert_owned_cleanup()
                self.assertIn('--sig-proxy=false', next(c for c in self.calls() if c[0] == 'start'))

    def test_stubborn_application_and_stalled_cleanup_are_bounded(self):
        for stall in ('', 'kill', 'rm', 'failed-kill'):
            with self.subTest(stall=stall):
                self.log.unlink(missing_ok=True)
                session = self.base / ('stubborn-' + (stall or 'application'))
                process = self.start_wrapper(FAKE_SESSION=str(session), FAKE_IGNORE_SIGNAL='1',
                                             FAKE_CONTROL_STALL=stall,
                                             FAKE_KILL_STATUS='125' if stall == 'failed-kill' else '0',
                                             FAKE_CLIENT_IGNORE_TERM='1' if stall == 'rm' else '')
                self.wait_path(session.with_suffix('.ready'), process)
                start = time.monotonic()
                process.send_signal(signal.SIGTERM)
                time.sleep(0.1)
                process.send_signal(signal.SIGHUP)
                out, err = process.communicate(timeout=23)
                self.assertEqual(process.returncode, 143, out + err)
                self.assertLess(time.monotonic() - start, 22)
                self.assert_owned_cleanup()
                if stall == 'rm':
                    self.assertIn('Cannot remove owned', err)

    def test_terminal_matrix(self):
        for terminal_in, terminal_out in itertools.product((False, True), repeat=2):
            with self.subTest(stdin=terminal_in, stdout=terminal_out):
                self.log.unlink(missing_ok=True)
                master, slave = pty.openpty()
                try:
                    process = subprocess.Popen(['bash', str(WRAPPER)], cwd=self.project,
                                               env=self.env, stdin=slave if terminal_in else subprocess.DEVNULL,
                                               stdout=slave if terminal_out else subprocess.PIPE,
                                               stderr=subprocess.PIPE, text=True)
                    out, err = process.communicate(timeout=10)
                    self.assertEqual(process.returncode, 0, (out or '') + err)
                    self.assertEqual('--tty' in self.run_args(), terminal_in and terminal_out)
                finally:
                    os.close(master)
                    os.close(slave)

    def test_pipe_and_file_input_reach_eof(self):
        for shell in (False, True):
            args = ['--container-shell'] if shell else ['exec', 'prompt with spaces', '']
            result = subprocess.run(['bash', str(WRAPPER), *args], cwd=self.project,
                                    env=self.env | {'FAKE_ECHO_INPUT': '1'}, input='payload\n',
                                    text=True, capture_output=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('payload\n', result.stdout)
        source = self.base / 'input'
        source.write_text('file payload\n')
        with source.open() as stream:
            result = subprocess.run(['bash', str(WRAPPER), '--container-shell'], cwd=self.project,
                                    env=self.env | {'FAKE_ECHO_INPUT': '1'}, stdin=stream,
                                    text=True, capture_output=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('file payload\n', result.stdout)

    def test_image_and_build_status_matrix(self):
        for shell, access, yolo, image in itertools.product((False, True), ('0', '1'), ('0', '1'), (0, 1, 125, 42)):
            with self.subTest(shell=shell, access=access, yolo=yolo, image=image):
                result = self.run_wrapper(*(['--container-shell'] if shell else []),
                                          CODEX_CONTAINER_PODMAN=access, CODEX_YOLO=yolo,
                                          CODEX_CONTAINER_PODMAN_SOCKET=str(self.sock_path),
                                          FAKE_IMAGE_STATUS=str(image))
                self.assertEqual(result.returncode, image if image not in (0, 1) else 0, result.stderr)
                self.assertEqual(any(c[0] == 'build' for c in self.calls()), image == 1)
                self.assertEqual(bool(self.creates()), image in (0, 1))
        result = self.run_wrapper('--container-build', FAKE_IMAGE_STATUS='125')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(any(c[0] == 'image' for c in self.calls()))
        for options in ([], ['--container-build']):
            result = self.run_wrapper(*options, FAKE_IMAGE_STATUS='1', FAKE_BUILD_STATUS='42')
            self.assertEqual(result.returncode, 42)
            self.assertEqual(self.creates(), [])

    def test_tmpfs_capacities_and_options(self):
        for shell, access, yolo in itertools.product((False, True), ('0', '1'), ('0', '1')):
            result = self.run_wrapper(*(['--container-shell'] if shell else []),
                                      CODEX_CONTAINER_PODMAN=access, CODEX_YOLO=yolo,
                                      CODEX_CONTAINER_PODMAN_SOCKET=str(self.sock_path))
            self.assertEqual(result.returncode, 0, result.stderr)
            args = self.run_args()
            mounts = [args[i + 1] for i, a in enumerate(args) if a == '--tmpfs']
            self.assertEqual(mounts, ['/tmp:rw,exec,nosuid,nodev,mode=1777,size=512m',
                                      '/var/tmp:rw,exec,nosuid,nodev,mode=1777,size=512m',
                                      '/run:rw,nosuid,nodev,mode=1777,size=32m',
                                      '/codex-home:rw,exec,nosuid,nodev,mode=1777'])

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
