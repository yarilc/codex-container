"""Codex-specific launcher checks: the real entry script with Codex's agent part.

The launcher behavior is tested once, for every wrapper, by the shared
tests/test_launcher.py against fixture agent parts. These cases cover what only
Codex's own profile and agent part show: the approval bypass hook and its help,
the protected Codex arguments in each mode, and the API key that follows the
selected policy profile.
"""
import itertools
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
WRAPPER = ROOT / 'codex-container.sh'
FAKE = (ROOT / 'tests/fake_podman.py').read_text()
sys.path.insert(0, str(ROOT / 'tests'))
from test_launcher import build_inputs_hash, synthetic_install  # noqa: E402

EXEC = '/usr/local/bin/codex'
RESTRICTED = ['--no-daemon', '-c', 'sandbox_mode="danger-full-access"']
PROVIDER_ONLY = ['-c', 'check_for_update_on_startup=false', '-c', 'analytics.enabled=false',
                 '-c', 'feedback.enabled=false', '-c', 'otel.exporter="none"',
                 '-c', 'otel.trace_exporter="none"', '-c', 'otel.metrics_exporter="none"',
                 '-c', 'features.apps=false', '-c', 'features.plugins=false',
                 '-c', 'features.remote_plugin=false', '-c', 'features.plugin_discovery_prefetch=false']
RELAY = ['/usr/bin/python3', '-I', '/opt/sandbox-egress/relay.py']
BYPASS = '--yolo'
TRUE = ('1', 'true', 'TrUe', 'yes', 'YeS')
FALSE = ('', '0', 'false', 'FaLsE', 'no', 'nO')


class WrapperTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='codex-wrapper-', dir=os.environ.get('SANDBOX_TEST_TMPDIR'))
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.bin = self.base / 'bin'
        self.bin.mkdir()
        podman = self.bin / 'podman'
        podman.write_text(FAKE)
        podman.chmod(0o755)
        self.project = self.base / 'parent with spaces' / 'my project'
        self.project.mkdir(parents=True)
        self.log = self.base / 'calls.jsonl'
        self.env = {'PATH': str(self.bin) + ':' + os.environ['PATH'], 'HOME': str(self.base / 'host-home'),
                    'CODEX_CONTAINER_NETWORK': 'unrestricted', 'CODEX_CONTAINER_MAINTENANCE': '1',
                    'FAKE_LABEL_HASH': build_inputs_hash(ROOT), 'FAKE_LOG': str(self.log)}

    def run_wrapper(self, *args, wrapper=WRAPPER, **env):
        self.log.unlink(missing_ok=True)
        return subprocess.run([str(wrapper), *args], cwd=self.project, env=self.env | env, input='input payload',
                              text=True, capture_output=True, timeout=30)

    def calls(self):
        return [json.loads(s) for s in self.log.read_text().splitlines()] if self.log.exists() else []

    def agent_create(self):
        return next(c for c in self.calls() if c[0] == 'create' and not any('.egress=' in a for a in c))

    @staticmethod
    def environment(create):
        return [create[i + 1] for i, arg in enumerate(create) if arg == '--env']

    @staticmethod
    def command(create):
        """Everything after the image: the entrypoint's arguments."""
        return create[next(i for i, a in enumerate(create) if a.startswith('localhost/codex-cli')) + 1:]

    def test_help_documents_the_bypass_and_the_provider_hosts(self):
        result = subprocess.run(['/bin/bash', str(WRAPPER), '--container-help'], cwd=self.project,
                                env={'PATH': '/usr/bin:/bin', 'HOME': self.env['HOME']},
                                text=True, capture_output=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
        for text in ('CODEX_YOLO', BYPASS, 'OPENAI_API_KEY', 'openai-api-docs',
                     'openai-account: auth.openai.com, chatgpt.com, developers.openai.com',
                     'openai-api: api.openai.com'):
            self.assertIn(text, result.stdout)
        self.assertLess(result.stdout.index('CODEX_CONTAINER_NETWORK'), result.stdout.index('CODEX_YOLO'))
        self.assertIn('Host Podman delegation was removed: CODEX_CONTAINER_PODMAN=1 stops startup.', result.stdout)
        self.assertFalse(self.log.exists())

    def test_yolo_case_insensitive_and_no_socket(self):
        # Host Podman delegation was removed: no combination mounts a Podman socket.
        for shell, value in itertools.product((False, True), TRUE + FALSE):
            with self.subTest(shell=shell, value=value):
                options = ['--container-shell'] if shell else []
                result = self.run_wrapper(*options, 'exec', 'prompt with spaces', '', CODEX_YOLO=value)
                self.assertEqual(result.returncode, 0, result.stderr)
                create = self.agent_create()
                self.assertEqual(BYPASS in create, not shell and value in TRUE)
                self.assertFalse(any('podman.sock' in a for a in create))
                expected = ['exec', 'prompt with spaces', '']
                if not shell and value in TRUE:
                    expected.insert(0, BYPASS)
                self.assertEqual(create[-len(expected):], expected)
        # A user --yolo is an ordinary Codex argument, not the wrapper's bypass.
        result = self.run_wrapper('--yolo', 'exec', 'prompt', CODEX_YOLO='FaLsE')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.command(self.agent_create()), ['--yolo', 'exec', 'prompt'])
        for shell, value in itertools.product((False, True), ('enabled', '2', ' true ', 'YeS ', ' FaLsE')):
            with self.subTest(shell=shell, invalid=value):
                options = ['--container-shell'] if shell else []
                result = self.run_wrapper(*options, CODEX_YOLO=value)
                self.assertEqual(result.returncode, 1)
                self.assertIn('CODEX_YOLO', result.stderr)
                self.assertFalse(any(c[0] in ('build', 'create') for c in self.calls()))

    def test_permissions_and_hardening_independent_of_yolo(self):
        # The leftover CODEX_CONTAINER_PODMAN opt-in is refused by the shared core
        # (tests/test_launcher.py); here only the bypass hook varies.
        for yolo in ('0', '1'):
            with self.subTest(yolo=yolo):
                result = self.run_wrapper('exec', 'a prompt', '', CODEX_YOLO=yolo)
                self.assertEqual(result.returncode, 0, result.stderr)
                create = self.agent_create()
                self.assertEqual(BYPASS in create, yolo == '1')
                self.assertFalse(any('podman.sock' in a for a in create))
                self.assertEqual(create[-3:], ['exec', 'a prompt', ''])
                self.assertNotIn('--privileged', create)
                self.assertEqual([a for a in create if a.startswith('--security-opt')],
                                 ['--security-opt=no-new-privileges'])
                self.assertFalse(any('label=disable' in a for a in create))

    def test_unrestricted_codex_keeps_its_own_sandbox(self):
        for yolo in ('', '1'):
            with self.subTest(yolo=yolo):
                result = self.run_wrapper('exec', 'x', CODEX_YOLO=yolo, OPENAI_API_KEY='host-key')
                self.assertEqual(result.returncode, 0, result.stderr)
                create = self.agent_create()
                self.assertEqual(self.command(create), [*([BYPASS] if yolo else []), 'exec', 'x'])
                self.assertFalse(any('sandbox_mode' in a for a in create))
                self.assertNotIn('--no-daemon', create)
                self.assertFalse(any(a.startswith('check_for_update') for a in create))
                self.assertNotIn('OPENAI_API_KEY', self.environment(create))

    def test_unrestricted_api_key_only_by_explicit_name(self):
        result = self.run_wrapper('exec', 'x', OPENAI_API_KEY='host-key', CODEX_CONTAINER_ENV_VARS='OPENAI_API_KEY')
        self.assertEqual(result.returncode, 0, result.stderr)
        create = self.agent_create()
        self.assertIn('OPENAI_API_KEY', self.environment(create))
        self.assertNotIn('host-key', ' '.join(create))

    def test_shell_mode_receives_no_codex_arguments(self):
        result = self.run_wrapper('--container-shell', '-c', 'echo ok', CODEX_YOLO='1')
        self.assertEqual(result.returncode, 0, result.stderr)
        create = self.agent_create()
        self.assertEqual(create[create.index('--entrypoint') + 1], '/bin/bash')
        self.assertEqual(self.command(create), ['-c', 'echo ok'])


class RestrictedTests(WrapperTests):
    """Offline and provider sessions through a synthetic installation (argument instrumentation only)."""
    def setUp(self):
        super().setUp()
        self.wrapper = synthetic_install(self.base, ROOT, WRAPPER.name)
        self.policy = self.wrapper.parent / 'agent/policies/default.json'
        self.policy.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / 'agent/policies/default.json', self.policy)
        self.runtime = self.base / 'runtime'
        self.runtime.mkdir(mode=0o700)
        self.restricted = {'OPENAI_API_KEY': 'host-key', 'FAKE_NETWORK': '1',
                           'FAKE_INFO': 'true linux true', 'CONTAINER_HOST': 'unix:///run/service.sock'}

    def run_offline(self, *args, **env):
        return self.run_wrapper(*args, wrapper=self.wrapper, CODEX_CONTAINER_NETWORK='offline',
                                **(self.restricted | env))

    def run_provider(self, *args, profile='openai-api', **env):
        return self.run_wrapper(*args, wrapper=self.wrapper, CODEX_CONTAINER_NETWORK='provider',
                                CODEX_CONTAINER_NETWORK_PROFILE=profile,
                                CODEX_CONTAINER_NETWORK_POLICY=str(self.policy),
                                CODEX_CONTAINER_NETWORK_RUNTIME_DIR=str(self.runtime),
                                CODEX_CONTAINER_EGRESS_IMAGE='sha256:' + 'e' * 64, **(self.restricted | env))

    def tail(self, create):
        """The Codex command after the guard's mode separator and, in provider mode, the relay."""
        command = create[create.index('--') + 1:]
        return command[len(RELAY):] if command[:len(RELAY)] == RELAY else command

    def test_offline_protected_arguments_precede_the_bypass_and_user_arguments(self):
        for yolo in ('', '1'):
            with self.subTest(yolo=yolo):
                result = self.run_offline('-c', 'sandbox_mode="read-only"', 'exec', 'hello world', '',
                                          CODEX_YOLO=yolo)
                self.assertEqual(result.returncode, 0, result.stderr)
                create = self.agent_create()
                self.assertIn('--network=none', create)
                self.assertEqual(self.tail(create), [EXEC, *RESTRICTED, *([BYPASS] if yolo else []),
                                                     '-c', 'sandbox_mode="read-only"', 'exec', 'hello world', ''])
                self.assertNotIn('OPENAI_API_KEY', self.environment(create))

    def test_provider_protected_arguments_and_api_key_per_profile(self):
        for profile, yolo in (('openai-api', ''), ('openai-account', '1'), ('openai-api-docs', '1')):
            with self.subTest(profile=profile, yolo=yolo):
                result = self.run_provider('-c', 'analytics.enabled=true', 'exec', 'x', profile=profile,
                                           CODEX_YOLO=yolo)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn(f'network profile={profile}', result.stderr)
                create = self.agent_create()
                self.assertEqual(self.tail(create), [EXEC, *RESTRICTED, *PROVIDER_ONLY, *([BYPASS] if yolo else []),
                                                     '-c', 'analytics.enabled=true', 'exec', 'x'])
                self.assertEqual('OPENAI_API_KEY' in self.environment(create), profile != 'openai-account')
                self.assertNotIn('host-key', ' '.join(create))

    def test_operator_profile_follows_its_authentication_method(self):
        value = json.loads(self.policy.read_text())
        base = value['profiles']['openai-api']
        value['profiles']['custom-api'] = json.loads(json.dumps(base))
        self.policy.write_text(json.dumps(value))
        result = self.run_provider('exec', 'x', profile='custom-api')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('network profile=custom-api', result.stderr)
        self.assertNotIn('OPENAI_API_KEY', self.environment(self.agent_create()))

    def test_account_profile_never_receives_the_api_key(self):
        result = self.run_provider('exec', 'x', profile='openai-account', CODEX_CONTAINER_ENV_VARS='OPENAI_API_KEY')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn('OPENAI_API_KEY', self.environment(self.agent_create()))
        self.assertIn('OPENAI_API_KEY', result.stderr)

    def test_restricted_shell_receives_no_codex_arguments(self):
        for run in (self.run_offline, self.run_provider):
            with self.subTest(mode=run.__name__):
                result = run('--container-shell', '-c', 'echo ok', CODEX_YOLO='1')
                self.assertEqual(result.returncode, 0, result.stderr)
                create = self.agent_create()
                self.assertEqual(self.tail(create), ['/bin/bash', '-c', 'echo ok'])
                self.assertNotIn(BYPASS, create)

    def test_qualification_probe_receives_no_codex_arguments(self):
        control = self.wrapper.parent / 'network/control.py'
        control.write_text(control.read_text() + "if args[0]=='qualification-input': print('f'*32+' 0')\n")
        result = self.run_offline('--container-qualify-probe', CODEX_YOLO='1')
        self.assertEqual(result.returncode, 0, result.stderr)
        create = self.agent_create()
        self.assertEqual(self.tail(create), ['/usr/bin/python3', '-I', '/opt/sandbox-egress/qualification_probe.py',
                                             'probe'])
        for argument in (BYPASS, '--no-daemon', 'sandbox_mode="danger-full-access"', EXEC):
            self.assertNotIn(argument, create)

    # The unrestricted cases of the parent class run once, there.
    test_help_documents_the_bypass_and_the_provider_hosts = None
    test_yolo_case_insensitive_and_no_socket = None
    test_permissions_and_hardening_independent_of_yolo = None
    test_unrestricted_codex_keeps_its_own_sandbox = None
    test_unrestricted_api_key_only_by_explicit_name = None
    test_shell_mode_receives_no_codex_arguments = None


if __name__ == '__main__':
    unittest.main()
