"""Wrapper contracts with synthetic Podman responses; no engine or credentials."""
import itertools
import json
import os
from pathlib import Path
import pty
import shutil
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
proxy = 'b' * 64
if args[0] in os.environ.get('FAKE_STALL', '').split(','):
    signal.signal(signal.SIGTERM, signal.SIG_IGN)
    pathlib.Path(os.environ['FAKE_LOG'] + '.stalled-' + args[0]).write_text(str(os.getpid()))
    while True: time.sleep(0.05)
if args[0] == 'info' and args[-1] == '{{json .Host}}':
    print(json.dumps({'kernel': '6.6.87.2-microsoft-standard-WSL2', 'arch': 'amd64',
        'security': {'seccompEnabled': True, 'selinuxEnabled': False, 'apparmorEnabled': False}}))
elif args[0] == 'info' and args[-1] == '{{.Host.NetworkBackend}}':
    print(os.environ.get('FAKE_BACKEND', 'netavark'))
elif args[0] == 'version':
    print(os.environ.get('FAKE_SERVER_VERSION', '4.9.3'))
elif args[:2] == ['image', 'inspect']:
    print(os.environ.get('FAKE_IMAGE_ID', 'd' * 64))
elif args[:2] == ['image', 'exists'] and args[-1] == os.environ.get('FAKE_EGRESS_IMAGE', '-'):
    sys.exit(int(os.environ.get('FAKE_EGRESS_STATUS', '0')))
elif args[0] == 'pull':
    sys.exit(0)
elif args[0] == 'create' and any(a.startswith('io.codex-container.egress=') for a in args):
    pathlib.Path(args[args.index('--cidfile') + 1]).write_text(proxy + '\n')
    print(proxy)
elif args[0] == 'inspect' and args[-1] == proxy:
    print(os.environ.get('FAKE_PROXY_CONFIG', '{"PidsLimit":128,"Memory":268435456}'))
elif args[0] == 'exec' and args[1] == proxy:
    print(os.environ.get('FAKE_PROXY_EFFECTIVE', '{"pids":128,"memory":268435456,"capabilities":[0,0,0,0,0],"no_new_privs":1,"seccomp":2}'))
elif args[0] in ('start', 'rm') and args[-1] == proxy:
    sys.exit(0)
elif args[0] == 'ps' and '--filter' in args:
    print('')
elif args[0] == 'info':
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
    cidfile = pathlib.Path(args[args.index('--cidfile') + 1])
    mode = os.environ.get('FAKE_CREATE_MODE', '')
    def publish():
        cidfile.write_text(cid + '\0\n' if os.environ.get('FAKE_CID_NUL')
                           else os.environ.get('FAKE_CID_RAW', cid + '\n'))
    if mode == 'cid-on-term':
        def on_term(signum, frame):
            publish()
            sys.exit(42)
        signal.signal(signal.SIGTERM, on_term)
    elif os.environ.get('FAKE_CLIENT_IGNORE_TERM'):
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
    if mode not in ('stall', 'cid-on-term'):
        publish()
    if os.environ.get('FAKE_CREATE_BARRIER'):
        barrier = pathlib.Path(os.environ['FAKE_CREATE_BARRIER'])
        barrier.with_suffix('.pid').write_text(str(os.getpid()))
        barrier.with_suffix('.ready').touch()
        if mode:
            while True: time.sleep(0.01)
        while not barrier.with_suffix('.release').exists(): time.sleep(0.01)
    print(cid)
elif args[0] == 'inspect':
    if 'FAKE_AGENT_BUDGETS' in os.environ:
        print(os.environ['FAKE_AGENT_BUDGETS'])
    else:
        calls = [json.loads(line) for line in pathlib.Path(os.environ['FAKE_LOG']).read_text().splitlines()]
        create = [c for c in calls if c[0] == 'create'][-1]
        value = lambda prefix: next(a[len(prefix):] for a in create if a.startswith(prefix))
        whole, _, frac = value('--cpus=').partition('.')
        nano = int(whole) * 10**9 + int((frac + '000')[:3]) * 10**6
        print(value('--memory='), nano, value('--pids-limit='))
    sys.exit(int(os.environ.get('FAKE_INSPECT_STATUS', '0')))
elif args[0] in ('kill', 'rm'):
    if os.environ.get('FAKE_CONTROL_STALL') == args[0]:
        if os.environ.get('FAKE_CONTROL_IGNORE_TERM'):
            signal.signal(signal.SIGTERM, signal.SIG_IGN)
        while True: time.sleep(0.01)
    status = int(os.environ.get('FAKE_' + args[0].upper() + '_STATUS', '0'))
    if not status and os.environ.get('FAKE_SESSION'):
        if args[0] == 'rm' or not os.environ.get('FAKE_IGNORE_SIGNAL'):
            pathlib.Path(os.environ['FAKE_SESSION'] + '.done').touch()
    sys.exit(status)
elif args[0] in ('run', 'start'):
    if os.environ.get('FAKE_CLIENT_IGNORE_TERM'):
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
    if os.environ.get('FAKE_START_STDERR'):
        sys.stderr.write(os.environ['FAKE_START_STDERR']); sys.stderr.flush()
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
                        CODEX_HOME=str(self.state), FAKE_LOG=str(self.log),
                        CODEX_CONTAINER_NETWORK='unrestricted', CODEX_CONTAINER_MAINTENANCE='1')
        self.sock = socket.socket(socket.AF_UNIX)
        self.sock_path = self.base / 'service.sock'
        self.sock.bind(str(self.sock_path))
        self.addCleanup(self.sock.close)

    def run_wrapper(self, *args, **env):
        self.log.unlink(missing_ok=True)
        return subprocess.run(['bash', str(getattr(self, 'wrapper', WRAPPER)), *args], cwd=self.project,
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
        process = subprocess.Popen(['bash', str(getattr(self, 'wrapper', WRAPPER)), *args], cwd=self.project,
                                   env=self.env | env, stdin=subprocess.DEVNULL,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   text=True, start_new_session=True)
        def stop():
            # Also terminate leaked children when a broken wrapper exits early.
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
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
        # The root workspace is refused by default; the exact override keeps this prefix check reachable.
        result = subprocess.run(['bash', str(WRAPPER)], cwd='/',
                                env=self.env | {'CODEX_CONTAINER_ALLOW_UNSAFE_WORKSPACE': '1'},
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
        for shell, (sig, status) in itertools.product((False, True), (
                (signal.SIGTERM, 143), (signal.SIGINT, 130), (signal.SIGHUP, 129))):
            with self.subTest(shell=shell, sig=sig):
                self.log.unlink(missing_ok=True)
                barrier = self.base / f'create-{shell}-{sig}'
                process = self.start_wrapper(*(['--container-shell'] if shell else []),
                                             FAKE_CREATE_BARRIER=str(barrier))
                self.wait_path(barrier.with_suffix('.ready'), process)
                process.send_signal(sig)
                # The client completes only after the parent has received the signal.
                time.sleep(0.05)
                barrier.with_suffix('.release').touch()
                out, err = process.communicate(timeout=10)
                self.assertEqual(process.returncode, status, out + err)
                self.assertFalse(any(c[0] == 'start' for c in self.calls()))
                self.assert_owned_cleanup()

    def test_permanently_stalled_creation_signal_matrix(self):
        for shell, sig, mode in itertools.product(
                (False, True), (signal.SIGTERM, signal.SIGINT, signal.SIGHUP),
                ('stall', 'stall-owned', 'cid-on-term')):
            with self.subTest(shell=shell, signal=sig, mode=mode):
                self.log.unlink(missing_ok=True)
                barrier = self.base / f'stall-{shell}-{sig}-{mode}'
                process = self.start_wrapper(*(['--container-shell'] if shell else []),
                                             FAKE_CREATE_BARRIER=str(barrier),
                                             FAKE_CREATE_MODE=mode,
                                             FAKE_CLIENT_IGNORE_TERM='1' if mode == 'stall' else '')
                self.wait_path(barrier.with_suffix('.ready'), process)
                child = int(barrier.with_suffix('.pid').read_text())
                started = time.monotonic()
                process.send_signal(sig)
                # Repeated mixed signals must neither replace status nor renew waits.
                for later in (signal.SIGHUP, signal.SIGTERM, signal.SIGINT):
                    time.sleep(0.1)
                    process.send_signal(later)
                out, err = process.communicate(timeout=25)
                elapsed = time.monotonic() - started
                self.assertLess(elapsed, 25, out + err)
                # A permanent stall was cancelled, never released to finish normally.
                self.assertFalse(barrier.with_suffix('.release').exists())
                self.assertGreater(elapsed, 3)
                self.assertEqual(process.returncode, 128 + sig, out + err)
                self.assertFalse(any(c[0] == 'start' for c in self.calls()))
                self.assertEqual(len(self.creates()), 1)
                with self.assertRaises(ProcessLookupError):
                    os.kill(child, 0)
                cidfile = Path(self.run_args()[self.run_args().index('--cidfile') + 1])
                self.assertFalse(cidfile.parent.exists())
                if mode == 'stall':
                    self.assertIn('Creation outcome unresolved', err)
                    self.assertFalse(any(c[0] in ('rm', 'kill') for c in self.calls()))
                else:
                    self.assert_owned_cleanup()
                    self.assertNotIn('Creation outcome unresolved', err)

    def test_interrupted_creation_invalid_identity_and_control_failures(self):
        cases = (
            {'FAKE_CID_NUL': '1'},
            {'FAKE_CID_RAW': 'invalid\n'},
            {'FAKE_CID_RAW': 'a' * 64 + '\n' + 'b' * 64 + '\n'},
            {'FAKE_CID_RAW': 'a' * 64 + '\n\n'},
            {'FAKE_CID_RAW': 'a' * 64 + '\r\n'},
            {'FAKE_RM_STATUS': '125'},
            {'FAKE_CONTROL_STALL': 'rm', 'FAKE_CONTROL_IGNORE_TERM': '1'},
        )
        for index, env in enumerate(cases):
            with self.subTest(env=env):
                self.log.unlink(missing_ok=True)
                barrier = self.base / f'invalid-control-{index}'
                process = self.start_wrapper(FAKE_CREATE_BARRIER=str(barrier),
                                             FAKE_CREATE_MODE='stall-owned', **env)
                self.wait_path(barrier.with_suffix('.ready'), process)
                started = time.monotonic()
                process.send_signal(signal.SIGINT)
                out, err = process.communicate(timeout=25)
                self.assertLess(time.monotonic() - started, 25)
                self.assertEqual(process.returncode, 130, out + err)
                self.assertFalse(any(c[0] == 'start' for c in self.calls()))
                cidfile = Path(self.run_args()[self.run_args().index('--cidfile') + 1])
                self.assertFalse(cidfile.parent.exists())
                if 'FAKE_CID_RAW' in env or 'FAKE_CID_NUL' in env:
                    self.assertIn('Invalid container ID', err)
                    self.assertIn('Creation outcome unresolved', err)
                    self.assertFalse(any(c[0] == 'rm' for c in self.calls()))
                else:
                    self.assert_owned_cleanup()
                    self.assertIn('Cannot remove owned container ' + 'a' * 64, err)

    def test_stopped_creation_client_is_cancelled(self):
        barrier = self.base / 'stopped-create'
        process = self.start_wrapper(FAKE_CREATE_BARRIER=str(barrier),
                                     FAKE_CREATE_MODE='stall-owned')
        self.wait_path(barrier.with_suffix('.ready'), process)
        child = int(barrier.with_suffix('.pid').read_text())
        os.kill(child, signal.SIGSTOP)
        process.send_signal(signal.SIGTERM)
        out, err = process.communicate(timeout=25)
        self.assertEqual(process.returncode, 143, out + err)
        with self.assertRaises(ProcessLookupError):
            os.kill(child, 0)
        self.assert_owned_cleanup()
        self.assertFalse(any(c[0] == 'start' for c in self.calls()))

    def test_unreapable_client_reports_without_waiting(self):
        # Fault injection models a child still present after KILL without leaking
        # a real uninterruptible process. Exercise the production helper verbatim.
        source = WRAPPER.read_text()
        helpers = source[source.index('client_running() {'):source.index('cleanup() {')]
        harness = helpers + '''
client_pid=424242
client_running() { return 0; }
wait_for_client_until() { return 1; }
kill() { printf '%s\\n' "$*"; }
wait() { printf 'unexpected wait\\n'; exit 99; }
reap_client
[[ -z "$client_pid" ]]
'''
        result = subprocess.run(['bash', '-euc', harness], text=True,
                                capture_output=True, timeout=2)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(result.stdout.splitlines(), ['-TERM 424242', '-KILL 424242'])
        self.assertIn('Cannot reap Podman client 424242', result.stderr)

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
                self.assertEqual([a for a in args if a.startswith('--security-opt')],
                                 ['--security-opt=no-new-privileges'])
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

    # Session hardening baseline (B01-B05), same rules as claude-container.
    BUDGET_REJECTIONS = {
        'CODEX_CONTAINER_MEMORY_LIMIT': ['', ' ', '0g', '-1g', 'max', '4', '4gb', '4t', '1.5g', '04g',
                                         '99999999999g', '1048577g'],
        'CODEX_CONTAINER_CPU_LIMIT': ['', ' ', '0', '0.000', '-1', 'max', '1.5555', '1025', '.5', '1e3', '2 '],
        'CODEX_CONTAINER_PIDS_LIMIT': ['', ' ', '0', '-1', 'max', '4194305', '01', '1.5', 'x'],
        'CODEX_CONTAINER_RUN_TIMEOUT': [' ', '-1', '1.5', 'x', '01', '2147483648', '10s'],
    }

    def option(self, args, prefix):
        return next(a[len(prefix):] for a in args if a.startswith(prefix))

    def test_hardening_and_default_budgets_in_every_mode(self):
        modes = [([], {}), (['--container-shell'], {}), ([], {'CODEX_YOLO': '1'}),
                 ([], {'CODEX_CONTAINER_PODMAN': '1', 'CODEX_CONTAINER_PODMAN_SOCKET': str(self.sock_path)})]
        for flags, env in modes:
            with self.subTest(flags=flags, env=env):
                result = self.run_wrapper(*flags, **env)
                self.assertEqual(result.returncode, 0, result.stderr)
                args = self.run_args()
                self.assertIn('--cap-drop=all', args)
                self.assertIn('--security-opt=no-new-privileges', args)
                self.assertNotIn('--cap-add', ' '.join(args))
                self.assertEqual(self.option(args, '--memory='), str(4 << 30))
                self.assertEqual(self.option(args, '--cpus='), '2')
                self.assertEqual(self.option(args, '--pids-limit='), '512')
                self.assertNotIn('--timeout', args)
                calls = [c[0] for c in self.calls()]
                self.assertLess(calls.index('inspect'), calls.index('start'))

    def test_budget_overrides(self):
        for memory, cpus, pids, expected in (('8g', '1.5', '1024', 8 << 30), ('512M', '0.25', '1', 512 << 20),
                                             ('4096k', '1024', '4194304', 4 << 20)):
            with self.subTest(memory=memory):
                result = self.run_wrapper(CODEX_CONTAINER_MEMORY_LIMIT=memory, CODEX_CONTAINER_CPU_LIMIT=cpus,
                                          CODEX_CONTAINER_PIDS_LIMIT=pids)
                self.assertEqual(result.returncode, 0, result.stderr)
                args = self.run_args()
                self.assertEqual(self.option(args, '--memory='), str(expected))
                self.assertEqual(self.option(args, '--cpus='), cpus)
                self.assertEqual(self.option(args, '--pids-limit='), pids)

    def test_invalid_budgets_and_lifetime_rejected_before_engine(self):
        for name, values in self.BUDGET_REJECTIONS.items():
            for value in values:
                with self.subTest(name=name, value=value):
                    result = self.run_wrapper(**{name: value})
                    self.assertEqual(result.returncode, 1, result.stderr)
                    self.assertIn(name, result.stderr)
                    self.assertEqual(self.calls(), [])
                    self.assertFalse(self.state.exists())

    def test_budget_mismatch_and_inspection_failure_stop_before_start(self):
        for env in ({'FAKE_AGENT_BUDGETS': '0 2000000000 512'}, {'FAKE_AGENT_BUDGETS': f'{4 << 30} 2000000000 2048'},
                    {'FAKE_AGENT_BUDGETS': f'{4 << 30} 0 512'}, {'FAKE_INSPECT_STATUS': '125'}):
            with self.subTest(env=env):
                result = self.run_wrapper(**env)
                self.assertEqual(result.returncode, 1, result.stderr)
                self.assertIn('codex-container:', result.stderr)
                if 'FAKE_AGENT_BUDGETS' in env:
                    self.assertIn('cgroup v2', result.stderr)
                calls = self.calls()
                self.assertFalse(any(c[0] == 'start' for c in calls))
                self.assertIn(['rm', '--force', '--ignore', '--time', '0', 'a' * 64], calls)

    def test_lifetime_argument_and_notice(self):
        for value in ('', '0'):
            result = self.run_wrapper(CODEX_CONTAINER_RUN_TIMEOUT=value)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertNotIn('--timeout', self.run_args())
        result = self.run_wrapper(CODEX_CONTAINER_RUN_TIMEOUT='3600')
        self.assertEqual(result.returncode, 0, result.stderr)
        args = self.run_args()
        self.assertEqual(args[args.index('--timeout') + 1], '3600')
        self.assertNotIn('lifetime', result.stderr)
        script = self.bin / 'podman'
        script.write_text(script.read_text().replace("elif args[0] in ('run', 'start'):",
                                                     "elif args[0] in ('run', 'start') and os.environ.get('FAKE_SLOW'):\n"
                                                     "    time.sleep(1.2); sys.exit(255)\nelif args[0] in ('run', 'start'):"))
        result = self.run_wrapper(CODEX_CONTAINER_RUN_TIMEOUT='1', FAKE_SLOW='1')
        self.assertEqual(result.returncode, 255, result.stderr)
        self.assertIn('session lifetime limit reached (1 s); exit status 255', result.stderr)
        result = self.run_wrapper(CODEX_CONTAINER_RUN_TIMEOUT='1', FAKE_EXIT='3')
        self.assertEqual(result.returncode, 3)
        self.assertNotIn('lifetime', result.stderr)

    def assert_refused(self, result, path):
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn(f'refusing sensitive workspace {path}', result.stderr)
        self.assertIn('CODEX_CONTAINER_ALLOW_UNSAFE_WORKSPACE=1', result.stderr)
        self.assertEqual(self.calls(), [])
        self.assertFalse(self.state.exists())

    def test_sensitive_workspaces_refused_before_engine(self):
        home = self.base / 'home-link'
        home.symlink_to(self.project, target_is_directory=True)
        self.assert_refused(self.run_wrapper(HOME=str(home)), self.project)
        self.assert_refused(self.run_wrapper('--container-git-worktree', HOME=str(self.project.parent)),
                            self.project.parent)
        etc = self.base / 'etc-link'
        etc.symlink_to('/etc', target_is_directory=True)
        for cwd, path in ((etc, '/etc'), (Path('/'), '/'), (Path('/tmp'), '/tmp'), (Path('/usr'), '/usr')):
            with self.subTest(cwd=cwd):
                self.project = cwd
                self.assert_refused(self.run_wrapper(), path)

    def test_wsl_drive_roots(self):
        drive = Path('/mnt/d')
        if not drive.is_dir():
            self.skipTest('no /mnt/d drive root on this host')
        self.project = drive
        self.assert_refused(self.run_wrapper(), '/mnt/d')
        project = Path(os.environ.get('CODEX_WRAPPER_DRIVE_PROJECT', ROOT))
        if not str(project.resolve()).startswith('/mnt/d/'):
            self.skipTest('no project below /mnt/d')
        self.project = project
        result = self.run_wrapper()
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_unsafe_workspace_override_is_exact(self):
        for value in ('true', 'yes', '01', '1 '):
            with self.subTest(value=value):
                self.assert_refused(self.run_wrapper(HOME=str(self.project),
                                                     CODEX_CONTAINER_ALLOW_UNSAFE_WORKSPACE=value), self.project)
        result = self.run_wrapper(HOME=str(self.project), CODEX_CONTAINER_ALLOW_UNSAFE_WORKSPACE='1')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(f'WARNING: sensitive workspace explicitly exposed read/write: {self.project}', result.stderr)
        self.assertIn(f'{self.project}:{self.project}:rw', self.run_args())

    def test_help_documents_hardening(self):
        result = self.run_wrapper('--container-help')
        self.assertEqual(result.returncode, 0, result.stderr)
        for text in ('CODEX_CONTAINER_MEMORY_LIMIT', '(default: 4g)', 'CODEX_CONTAINER_CPU_LIMIT', '(default: 2)',
                     'CODEX_CONTAINER_PIDS_LIMIT', '(default: 512)', 'CODEX_CONTAINER_RUN_TIMEOUT',
                     'disabled by default', 'CODEX_CONTAINER_ALLOW_UNSAFE_WORKSPACE', 'drops all capabilities',
                     'do not limit workspace', '/mnt/<letter>'):
            self.assertIn(text, result.stdout)
        self.assertEqual(self.calls(), [])

    # Restricted modes. Argument and lifecycle instrumentation only: the real
    # guard, platform and protected-path acceptance live in the runtime suites.
    def restricted_fixture(self):
        install = self.base / 'install'
        (install / 'network/bin').mkdir(parents=True)
        self.wrapper = install / 'codex-container.sh'
        shutil.copyfile(WRAPPER, self.wrapper)
        guard = install / 'network/bin/sandbox-egress-guard'
        guard.write_text('#!/bin/sh\nexit 0\n')
        guard.chmod(0o700)
        (guard.parent / 'sandbox-egress-guard.sha256').write_text('c' * 64 + '  sandbox-egress-guard\n')
        for name in ('network/session.py', 'network/agent_profile.py', 'network/policy.py', 'network/revisions.py',
                     'network/platform_check.py', 'network/proxy_hardening.py', 'agent/profile.json'):
            (install / name).parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / name, install / name)
        record = ("import json,os,pathlib,sys\n"
                  "pathlib.Path(os.environ['FAKE_LOG']).open('a').write(json.dumps([pathlib.Path(sys.argv[0]).name,"
                  " *sys.argv[1:], os.environ.get('CODEX_CONTAINER_IMAGE', '')]) + '\\n')\n")
        (install / 'network/qualify.py').write_text(record + (
            "if os.environ.get('FAKE_QUALIFY_STALL'):\n"
            " import signal,time; signal.signal(signal.SIGTERM, signal.SIG_IGN)\n"
            " pathlib.Path(os.environ['FAKE_LOG'] + '.stalled-qualify').touch()\n"
            " time.sleep(60)\n"
            "sys.exit(int(os.environ.get('FAKE_QUALIFY_STATUS', '0')))\n"))
        (install / 'network/control.py').write_text(record + (
            "sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))\n"
            "import socket\nfrom revisions import TLS_ENFORCEMENT\nargs=sys.argv[1:]\n"
            "if args[0]=='preflight' and os.environ.get('FAKE_PREFLIGHT_FAILURE'):\n"
            " print('codex-container: network policy preflight failed: synthetic invalid policy', file=sys.stderr); sys.exit(1)\n"
            "if args[0]=='snapshot':\n"
            " p=pathlib.Path(args[args.index('--session')+1]); (p/'transport').mkdir(); (p/'config').mkdir(); (p/'logs').mkdir()\n"
            " s=socket.socket(socket.AF_UNIX); s.bind(str(p/'transport/proxy.sock')); s.close()\n"
            " (p/'transport/ready').write_text('fixture-policy guard='+'c'*64+' mux=1 tls='+TLS_ENFORCEMENT+'\\n')\n"
            " print('fixture-policy')\n"))
        runtime = self.base / 'runtime'
        runtime.mkdir(mode=0o700, exist_ok=True)
        return dict(FAKE_INFO='true linux true', CONTAINER_HOST='unix:///run/service.sock',
                    CODEX_CONTAINER_NETWORK_POLICY=str(install / 'policy.json'),
                    CODEX_CONTAINER_NETWORK_PROFILE='openai-api',
                    CODEX_CONTAINER_NETWORK_RUNTIME_DIR=str(runtime),
                    CODEX_CONTAINER_EGRESS_IMAGE='e' * 64, FAKE_EGRESS_IMAGE='e' * 64)

    def names(self):
        return [Path(c[0]).name if c[0].endswith('.py') else c[0] for c in self.calls()]

    def test_missing_mode_stops_before_engine_state_and_other_checks(self):
        options = ('--container-shell', '--container-build', '--container-git-worktree')
        for enabled in itertools.product((False, True), repeat=3):
            for mode in (None, ''):
                with self.subTest(enabled=enabled, mode=mode):
                    env = self.env | {'CODEX_YOLO': 'invalid', 'CODEX_CONTAINER_TRUST_HOST_CA': 'invalid',
                                      'CODEX_CONTAINER_PODMAN': '1', 'CONTAINER_HOST': 'invalid',
                                      'CODEX_CONTAINER_STATE_DIR': str(self.base / 'isolated'),
                                      'CODEX_CONTAINER_MEMORY_LIMIT': 'invalid', 'PATH': ''}
                    env.pop('CODEX_CONTAINER_NETWORK')
                    if mode is not None:
                        env['CODEX_CONTAINER_NETWORK'] = mode
                    args = [option for option, use in zip(options, enabled) if use]
                    self.log.unlink(missing_ok=True)
                    result = subprocess.run(['/bin/bash', str(WRAPPER), *args, '-p', 'x'], cwd=self.project,
                                            env=env, text=True, capture_output=True, timeout=10)
                    self.assertEqual(result.returncode, 1, result.stderr)
                    self.assertIn('setup required: run bash ' + str(WRAPPER).replace(' ', '\\ ') + ' --container-setup', result.stderr)
                    self.assertIn('explicitly set CODEX_CONTAINER_NETWORK', result.stderr)
                    self.assertIn('offline, provider, or unrestricted', result.stderr)
                    self.assertIn('unrestricted keeps the previous networking behavior', result.stderr)
                    self.assertEqual(self.calls(), [])
                    self.assertFalse(self.state.exists())
                    self.assertFalse((self.base / 'isolated').exists())

    def test_mode_and_delegation_rejections_precede_engine(self):
        cases = (({'CODEX_CONTAINER_NETWORK': 'invalid'}, 'must be offline, provider, or unrestricted'),
                 ({'CODEX_CONTAINER_NETWORK': 'Offline'}, 'must be offline, provider, or unrestricted'),
                 ({'CODEX_CONTAINER_NETWORK': 'provider'}, 'requires CODEX_CONTAINER_NETWORK_PROFILE'),
                 ({'CODEX_CONTAINER_NETWORK': 'offline', 'CODEX_CONTAINER_PODMAN': '1'}, 'rejects CODEX_CONTAINER_PODMAN=1'),
                 ({'CODEX_CONTAINER_NETWORK': 'provider', 'CODEX_CONTAINER_PODMAN': '1'}, 'rejects CODEX_CONTAINER_PODMAN=1'),
                 ({'CODEX_CONTAINER_STATE_DIR': str(self.base / 'isolated')}, 'conflicts with CODEX_HOME'))
        for values, message in cases:
            for flags in ((), ('--container-shell',), ('--container-build', '--container-git-worktree')):
                for yolo in ('', '1'):
                    with self.subTest(values=values, flags=flags, yolo=yolo):
                        result = self.run_wrapper(*flags, CODEX_YOLO=yolo, **values)
                        self.assertEqual(result.returncode, 1, result.stderr)
                        self.assertIn(message, result.stderr)
                        self.assertEqual(self.calls(), [])
                        self.assertFalse((self.base / 'isolated').exists())
        fixture = self.restricted_fixture()
        for values in ({'FAKE_BACKEND': 'cni'}, {'FAKE_SERVER_VERSION': '4.8.0'}):
            with self.subTest(values=values):
                result = self.run_wrapper(**(fixture | values | {'CODEX_CONTAINER_NETWORK': 'offline'}))
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('ineligible restricted platform', result.stderr)
                self.assertFalse(any(c[0] in ('image', 'build', 'create') for c in self.calls()))

    def test_help_documents_modes_migration_and_provider_limits(self):
        result = self.run_wrapper('--container-help', CODEX_CONTAINER_NETWORK='')
        self.assertEqual(result.returncode, 0, result.stderr)
        for text in ('--container-qualify', 'CODEX_CONTAINER_NETWORK ', 'CODEX_CONTAINER_NETWORK_PROFILE',
                     'CODEX_CONTAINER_NETWORK_POLICY', 'CODEX_CONTAINER_NETWORK_RUNTIME_DIR',
                     'CODEX_CONTAINER_EGRESS_IMAGE', 'CODEX_CONTAINER_MAINTENANCE', 'CODEX_CONTAINER_STATE_DIR',
                     'CODEX_CONTAINER_TRUST_HOST_CA', 'CODEX_CONTAINER_CA_BUNDLE', 'OPENAI_API_KEY',
                     'CODEX_CONTAINER_NETWORK=unrestricted to keep the previous networking behavior',
                     'api.openai.com', 'auth.openai.com, chatgpt.com and', 'Only offline removes this',
                     'codex login --device-auth', 'outside this boundary'):
            self.assertIn(text, result.stdout)
        self.assertEqual(self.calls(), [])

    def test_maintenance_gates_every_build(self):
        for maintenance in ('', '0', 'true', 'yes', '01', ' 1'):
            for explicit, status in ((True, '0'), (False, '1')):
                with self.subTest(maintenance=maintenance, explicit=explicit):
                    result = self.run_wrapper(*(['--container-build'] if explicit else []),
                                              CODEX_CONTAINER_MAINTENANCE=maintenance, FAKE_IMAGE_STATUS=status)
                    self.assertEqual(result.returncode, 1, result.stderr)
                    self.assertIn('CODEX_CONTAINER_MAINTENANCE=1', result.stderr)
                    self.assertFalse(any(c[0] in ('build', 'pull', 'create') for c in self.calls()))
        result = self.run_wrapper(CODEX_CONTAINER_MAINTENANCE='', FAKE_IMAGE_STATUS='0')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(any(c[0] == 'build' for c in self.calls()))
        for explicit, status in ((True, '0'), (False, '1')):
            result = self.run_wrapper(*(['--container-build'] if explicit else []), FAKE_IMAGE_STATUS=status)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual([c[0] for c in self.calls()].count('build'), 1)
        result = self.run_wrapper(FAKE_IMAGE_STATUS='125')
        self.assertEqual(result.returncode, 125, result.stderr)
        self.assertFalse(any(c[0] in ('build', 'create') for c in self.calls()))
        fixture = self.restricted_fixture()
        for mode in ('offline', 'provider'):
            with self.subTest(mode=mode, preflight='invalid policy'):
                result = self.run_wrapper('--container-build', **(fixture | {
                    'CODEX_CONTAINER_NETWORK': mode, 'FAKE_PREFLIGHT_FAILURE': '1'}))
                self.assertEqual(result.returncode, 1, result.stderr)
                self.assertIn('network policy preflight failed', result.stderr)
                self.assertFalse(any(c[0] in ('image', 'build', 'pull', 'create') for c in self.calls()))

    def test_proxy_image_acquisition_requires_maintenance_and_digest(self):
        fixture = self.restricted_fixture() | {'CODEX_CONTAINER_NETWORK': 'provider', 'FAKE_EGRESS_STATUS': '1'}
        digest = 'localhost/codex-egress@sha256:' + 'e' * 64
        for maintenance, image in (('', digest), ('1', 'e' * 64), ('1', 'localhost/codex-egress:local')):
            with self.subTest(maintenance=maintenance, image=image):
                result = self.run_wrapper(**(fixture | {'CODEX_CONTAINER_MAINTENANCE': maintenance,
                                                       'CODEX_CONTAINER_EGRESS_IMAGE': image,
                                                       'FAKE_EGRESS_IMAGE': image}))
                self.assertEqual(result.returncode, 1, result.stderr)
                self.assertIn('proxy image is absent', result.stderr)
                self.assertFalse(any(c[0] in ('pull', 'create') for c in self.calls()))
        result = self.run_wrapper(**(fixture | {'CODEX_CONTAINER_EGRESS_IMAGE': digest, 'FAKE_EGRESS_IMAGE': digest}))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(['pull', digest], self.calls())

    def test_isolated_home_mounts_and_privacy(self):
        isolated = self.base / 'isolated'
        result = self.run_wrapper(CODEX_HOME='', CODEX_CONTAINER_STATE_DIR=str(isolated))
        self.assertEqual(result.returncode, 0, result.stderr)
        create = self.run_args()
        self.assertIn(f'{isolated}:/codex-home:rw', create)
        self.assertIn('CODEX_HOME=/codex-home/.codex', create)
        self.assertIn('HOME=/codex-home', create)
        self.assertFalse(any(a.startswith('/codex-home:') for a in create))
        self.assertFalse(any(a.endswith(':/codex-home/.codex:rw') for a in create))
        self.assertFalse(self.state.exists())
        for path in (isolated, isolated / '.codex'):
            self.assertEqual(path.stat().st_mode & 0o777, 0o700)
        for target, message in ((isolated, 'Isolated Codex home must be private'),
                                (isolated / '.codex', 'Isolated Codex configuration must be private')):
            with self.subTest(target=target):
                target.chmod(0o750)
                result = self.run_wrapper(CODEX_HOME='', CODEX_CONTAINER_STATE_DIR=str(isolated))
                self.assertEqual(result.returncode, 1, result.stderr)
                self.assertIn(message, result.stderr)
                self.assertEqual(target.stat().st_mode & 0o777, 0o750)
                self.assertFalse(any(c[0] in ('image', 'build', 'create') for c in self.calls()))
                target.chmod(0o700)
        escaped = self.base / 'escaped'
        (isolated / '.codex').rmdir()
        (isolated / '.codex').symlink_to(escaped)
        for trust, name in (('0', '.codex'), ('1', 'ca')):
            if name == 'ca':
                (isolated / '.codex').unlink()
                (isolated / 'ca').symlink_to(escaped)
            with self.subTest(name=name):
                result = self.run_wrapper(CODEX_HOME='', CODEX_CONTAINER_STATE_DIR=str(isolated),
                                          CODEX_CONTAINER_TRUST_HOST_CA=trust,
                                          CODEX_CONTAINER_CA_BUNDLE=str(self.base / 'bundle.pem'))
                self.assertEqual(result.returncode, 1, result.stderr)
                self.assertIn('escapes state home', result.stderr)
                self.assertFalse(escaped.exists())
                self.assertFalse(any(c[0] in ('image', 'build', 'create') for c in self.calls()))

    def test_host_ca_trust_modes(self):
        bundle = self.base / 'bundle.pem'
        bundle.write_text('synthetic certificate bundle')
        variables = ('SSL_CERT_FILE', 'REQUESTS_CA_BUNDLE', 'CURL_CA_BUNDLE', 'NODE_EXTRA_CA_CERTS')
        for isolated in ('', str(self.base / 'isolated')):
            for trust in ('', '0', 'no', '1', 'TrUe', 'yes'):
                with self.subTest(isolated=isolated, trust=trust):
                    result = self.run_wrapper(CODEX_HOME='' if isolated else str(self.state),
                                              CODEX_CONTAINER_STATE_DIR=isolated,
                                              CODEX_CONTAINER_TRUST_HOST_CA=trust,
                                              CODEX_CONTAINER_CA_BUNDLE=str(bundle))
                    self.assertEqual(result.returncode, 0, result.stderr)
                    create = self.run_args()
                    enabled = trust.lower() in ('1', 'true', 'yes')
                    self.assertEqual(f'{bundle}:/codex-home/ca/bundle.pem:ro' in create, enabled)
                    for variable in variables:
                        self.assertEqual(f'{variable}=/codex-home/ca/bundle.pem' in create, enabled)
                    self.assertFalse(any('/etc/ssl/certs:' in a for a in create))
                    if isolated and enabled:
                        self.assertEqual((Path(isolated) / 'ca').stat().st_mode & 0o777, 0o700)
        result = self.run_wrapper(CODEX_CONTAINER_TRUST_HOST_CA='maybe')
        self.assertEqual(result.returncode, 1)
        self.assertIn('CODEX_CONTAINER_TRUST_HOST_CA must be 0, 1, true, false, yes, or no', result.stderr)
        self.assertEqual(self.calls(), [])
        result = self.run_wrapper(CODEX_CONTAINER_TRUST_HOST_CA='1', CODEX_CONTAINER_CA_BUNDLE='/missing/bundle.pem')
        self.assertEqual(result.returncode, 1)
        self.assertIn('CODEX_CONTAINER_CA_BUNDLE is not a file: /missing/bundle.pem', result.stderr)
        self.assertFalse(any(c[0] in ('image', 'build', 'create') for c in self.calls()))
        self.wrapper = self.base / 'no-default-ca.sh'
        self.wrapper.write_text(WRAPPER.read_text().replace(
            'for candidate in /etc/ssl/certs/ca-certificates.crt /etc/pki/tls/certs/ca-bundle.crt',
            'for candidate in /missing/one.crt /missing/two.crt'))
        result = self.run_wrapper(CODEX_CONTAINER_TRUST_HOST_CA='1')
        self.assertEqual(result.returncode, 1)
        self.assertIn('no default CA bundle found', result.stderr)
        self.assertFalse(any(c[0] in ('image', 'build', 'create') for c in self.calls()))

    def test_offline_order_arguments_and_status(self):
        fixture = self.restricted_fixture() | {'CODEX_CONTAINER_NETWORK': 'offline',
                                               'OPENAI_API_KEY': 'synthetic-not-a-real-key'}
        sandbox = ['--no-daemon', '-c', 'sandbox_mode="danger-full-access"']
        for flags, yolo, tail in (((), '', ['/usr/local/bin/codex', *sandbox, '-p', 'hello world']),
                                  ((), '1', ['/usr/local/bin/codex', *sandbox, '--yolo', '-p', 'hello world']),
                                  (('--container-shell',), '1', ['/bin/bash'])):
            with self.subTest(flags=flags, yolo=yolo):
                result = self.run_wrapper(*flags, '-p', 'hello world', CODEX_YOLO=yolo, FAKE_EXIT='7', **fixture)
                self.assertEqual(result.returncode, 7, result.stderr)
                self.assertIn('network mode=offline', result.stderr)
                names = self.names()
                order = [n for n in names if n in ('control.py', 'image', 'qualify.py', 'ps', 'create', 'start')]
                self.assertEqual(order, ['control.py', 'image', 'image', 'qualify.py', 'ps', 'create', 'start'])
                preflight = next(c for c in self.calls() if c[0].endswith('control.py'))
                for value in (str(self.project), '/codex-home', str(self.state)):
                    self.assertIn(value, preflight)
                self.assertEqual(preflight[preflight.index('--mount-target') + 1], str(self.project))
                qualify = next(c for c in self.calls() if c[0] == 'qualify.py')
                self.assertEqual(qualify[1:], ['check', 'd' * 64])
                create = self.run_args()
                for value in ('--network=none', '--cap-drop=all', '--security-opt=no-new-privileges'):
                    self.assertIn(value, create)
                self.assertEqual(create[create.index('--entrypoint', create.index('--network=none')) + 1],
                                 '/opt/sandbox-egress/guard')
                self.assertTrue(any(a.startswith('io.codex-container.session=session') or
                                    a.startswith('io.codex-container.session=tmp') for a in create))
                image = create.index('d' * 64)
                self.assertEqual(create[image + 1:], ['--offline', '--', *tail])
                self.assertNotIn('OPENAI_API_KEY', create)
                self.assertFalse(any(a.startswith('check_for_update') for a in create))
                self.assertFalse(any(c[0] in ('build', 'pull') for c in self.calls()))

    def test_provider_order_protected_overrides_and_api_key(self):
        fixture = self.restricted_fixture() | {'CODEX_CONTAINER_NETWORK': 'provider',
                                               'OPENAI_API_KEY': 'synthetic-not-a-real-key'}
        protected = ['--no-daemon', '-c', 'sandbox_mode="danger-full-access"', '-c', 'check_for_update_on_startup=false', '-c', 'analytics.enabled=false',
                     '-c', 'feedback.enabled=false', '-c', 'otel.exporter="none"',
                     '-c', 'otel.trace_exporter="none"', '-c', 'otel.metrics_exporter="none"',
                     '-c', 'features.apps=false', '-c', 'features.plugins=false',
                     '-c', 'features.remote_plugin=false', '-c', 'features.plugin_discovery_prefetch=false']
        relay = ['/usr/bin/python3', '-I', '/opt/sandbox-egress/relay.py']
        for profile, yolo in (('openai-api', ''), ('openai-account', '1'), ('custom-api', ''),
                              ('openai-api-docs', '1')):
            with self.subTest(profile=profile, yolo=yolo):
                result = self.run_wrapper('-c', 'analytics.enabled=true', 'exec', 'x', **(fixture | {
                    'FAKE_EXIT': '5', 'CODEX_YOLO': yolo, 'CODEX_CONTAINER_NETWORK_PROFILE': profile}))
                self.assertEqual(result.returncode, 5, result.stderr)
                self.assertIn('network mode=provider', result.stderr)
                self.assertIn(f'network profile={profile} policy=fixture-policy', result.stderr)
                names = self.names()
                order = [n for n in names if n in ('qualify.py', 'create', 'exec', 'start', 'rm')]
                self.assertEqual(order, ['qualify.py', 'create', 'start', 'exec', 'create', 'start', 'rm', 'rm'])
                creates = self.creates()
                self.assertIn('io.codex-container.egress=' + creates[0][creates[0].index('--name') + 1].split('-', 2)[2],
                              creates[0])
                agent = creates[1]
                self.assertIn('HTTPS_PROXY=http://127.0.0.1:18080', agent)
                tail = agent[agent.index('d' * 64) + 1:]
                user = ['-c', 'analytics.enabled=true', 'exec', 'x']
                expected = ['--provider', '--', *relay, '/usr/local/bin/codex', *protected,
                            *(['--yolo'] if yolo else []), *user]
                self.assertEqual(tail, expected)
                self.assertEqual('OPENAI_API_KEY' in agent, profile in ('openai-api', 'openai-api-docs'))
                self.assertEqual([c[-1] for c in self.calls() if c[0] == 'rm'], ['a' * 64, 'b' * 64])
        result = self.run_wrapper('--container-shell', CODEX_YOLO='1', **fixture)
        self.assertEqual(result.returncode, 0, result.stderr)
        agent = self.creates()[1]
        self.assertEqual(agent[agent.index('d' * 64) + 1:], ['--provider', '--', *relay, '/bin/bash'])

    def test_api_key_follows_the_policy_authentication_method(self):
        # Every shipped profile whose policy authentication is the API-key method
        # forwards OPENAI_API_KEY; every other profile does not.
        policy = json.loads((ROOT / 'agent/policies/default.json').read_text())
        text = WRAPPER.read_text()
        start = text.index('# The API key reaches only the API profiles')
        condition = text[start:text.index('podman_args+=(--env OPENAI_API_KEY)', start)]
        for name, profile in policy['profiles'].items():
            with self.subTest(profile=name):
                self.assertEqual(f'== {name} ' in condition, profile['authentication'] == 'api')
        help_text = self.run_wrapper('--container-help').stdout
        for name in ('openai-api-docs', 'developers.openai.com', '--no-daemon'):
            self.assertIn(name, help_text)

    def test_failed_qualification_stops_before_session_resources(self):
        for mode in ('offline', 'provider'):
            with self.subTest(mode=mode):
                result = self.run_wrapper(FAKE_QUALIFY_STATUS='3',
                                          **(self.restricted_fixture() | {'CODEX_CONTAINER_NETWORK': mode}))
                self.assertEqual(result.returncode, 3, result.stderr)
                self.assertFalse(any(c[0] == 'create' for c in self.calls()))
                shutil.rmtree(self.base / 'install')

    def test_interrupted_restricted_helpers_are_bounded_and_clean_owned_proxy(self):
        fixture = self.restricted_fixture() | {'CODEX_CONTAINER_NETWORK': 'provider'}
        for stall, marker in (('exec', '.stalled-exec'), ('qualify', '.stalled-qualify')):
            for interrupt in (False, True):
                if stall == 'qualify' and not interrupt:
                    continue
                with self.subTest(stall=stall, interrupt=interrupt):
                    self.log.unlink(missing_ok=True)
                    Path(str(self.log) + marker).unlink(missing_ok=True)
                    values = fixture | ({'FAKE_STALL': 'exec'} if stall == 'exec' else {'FAKE_QUALIFY_STALL': '1'})
                    process = self.start_wrapper(**values)
                    self.wait_path(Path(str(self.log) + marker), process, timeout=10)
                    started = time.monotonic()
                    if interrupt:
                        process.terminate()
                    stdout, stderr = process.communicate(timeout=25)
                    self.assertEqual(process.returncode, 143 if interrupt else 1, stdout + stderr)
                    self.assertLess(time.monotonic() - started, 21)
                    self.assertEqual(len(self.creates()), 1 if stall == 'exec' else 0)
                    self.assertEqual([c[-1] for c in self.calls() if c[0] == 'rm'], ['b' * 64] if stall == 'exec' else [])
                    self.assertEqual(list((self.base / 'runtime').iterdir()), [])

    def test_setup_entry_point_is_dedicated_and_help_takes_precedence(self):
        for args, message in ((('--container-setup',), 'requires an interactive terminal'),
                              (('--container-setup', '--container-shell'), 'must be used alone'),
                              (('-p', 'x', '--container-setup'), 'must be used alone')):
            with self.subTest(args=args):
                result = self.run_wrapper(*args, CODEX_CONTAINER_NETWORK='')
                self.assertEqual(result.returncode, 1)
                self.assertIn('--container-setup ' + message, result.stderr)
                self.assertEqual(self.calls(), [])
                self.assertFalse(self.state.exists())
        for args in (('--container-setup', '--container-help'), ('--container-help', '--container-setup')):
            result = self.run_wrapper(*args, CODEX_CONTAINER_NETWORK='')
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('--container-setup', result.stdout)
            self.assertIn('New users must first run', result.stdout)
            self.assertEqual(self.calls(), [])

    def test_client_stderr_passes_through_the_diagnostics_filter(self):
        restart = 'time="2026-11-09T21:38:10Z" level=error msg="Should restart: false"\n'
        for status in ('0', '3'):
            with self.subTest(status=status):
                result = self.run_wrapper(FAKE_EXIT=status, FAKE_START_STDERR=restart + 'Error: real failure\n')
                self.assertEqual(result.returncode, int(status), result.stderr)
                self.assertIn('level=info msg="Should restart: false"', result.stderr)
                self.assertNotIn('level=error msg="Should restart', result.stderr)
                self.assertIn('Error: real failure', result.stderr)
                self.assertIn('mask:', result.stdout)
        # Without the shared filter the client stderr is passed unchanged.
        install = self.base / 'no-filter'
        install.mkdir()
        self.wrapper = install / 'codex-container.sh'
        shutil.copyfile(WRAPPER, self.wrapper)
        result = self.run_wrapper(FAKE_START_STDERR=restart)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('level=error msg="Should restart: false"', result.stderr)

    def test_unrestricted_codex_keeps_its_own_sandbox(self):
        for yolo in ('', '1'):
            result = self.run_wrapper('exec', 'x', CODEX_YOLO=yolo)
            self.assertEqual(result.returncode, 0, result.stderr)
            create = self.run_args()
            self.assertFalse(any('sandbox_mode' in a for a in create))
            self.assertNotIn('--no-daemon', create)
            self.assertEqual(create[-2:], ['exec', 'x'])

    def test_qualification_entry_points(self):
        for args in (('--container-qualify', '--container-shell'), ('-p', 'x', '--container-qualify')):
            result = self.run_wrapper(*args)
            self.assertEqual(result.returncode, 1)
            self.assertIn('--container-qualify must be used alone', result.stderr)
            self.assertEqual(self.calls(), [])
        fixture = self.restricted_fixture()
        result = self.run_wrapper('--container-qualify', **fixture)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual([c[:2] for c in self.calls()], [['qualify.py', 'qualify']])
        result = self.run_wrapper('--container-qualify-probe', '-p', 'x', **fixture)
        self.assertEqual(result.returncode, 1)
        self.assertIn('fixed qualification probe must be used alone', result.stderr)
        result = self.run_wrapper('--container-qualify-probe', **fixture)
        self.assertEqual(result.returncode, 1)
        self.assertIn('qualification probes require restricted networking', result.stderr)
        self.assertFalse(any(c[0] in ('image', 'build', 'create') for c in self.calls()))


if __name__ == '__main__':
    unittest.main()
