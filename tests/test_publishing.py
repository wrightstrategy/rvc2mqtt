"""Release calculations use real git histories and the pinned release tool."""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'ci'))
from release import PSR, release_notes


class PublishingTests(unittest.TestCase):
    def test_release_notes_lead_with_deploy_steps_and_preserve_breaking_instructions(self):
        notes = release_notes([
            'fix!: require external INI\n\nBREAKING CHANGE: mount /app/rvc2mqtt.ini',
            'feat: support a declared MQTT port', 'docs: wording', 'chore: dependency refresh',
        ], '# Pending deployment steps\n\nMount the INI.', 'image@sha256:abc', 'commit')
        self.assertTrue(notes.startswith('# Pending deployment steps'))
        self.assertIn('BREAKING CHANGE: mount /app/rvc2mqtt.ini', notes)
        self.assertIn('feat: support', notes)
        self.assertNotIn('docs: wording', notes)
        self.assertNotIn('chore: dependency', notes)
        self.assertIn('image@sha256:abc', notes)

    def test_tag_only_semantic_versioning_on_real_commits(self):
        with tempfile.TemporaryDirectory() as tmp:
            def git(*args):
                return subprocess.run(['git', *args], cwd=tmp, check=True, capture_output=True, text=True).stdout.strip()
            git('init', '-b', 'main')
            git('config', 'user.name', 'Release test')
            git('config', 'user.email', 'test@example.invalid')
            git('remote', 'add', 'origin', 'https://github.com/wrightstrategy/rvc2mqtt.git')
            Path(tmp, 'pyproject.toml').write_text((ROOT / 'pyproject.toml').read_text())
            git('add', 'pyproject.toml')
            git('commit', '-m', 'feat: initial bridge')
            # Synthetic tags exist only in this disposable local test repository.
            git('tag', 'v1.0.0')
            for message, expected in [('docs: describe the mount', 'v1.0.0'),
                                      ('fix: consume declared port', 'v1.0.1'),
                                      ('feat: new configuration', 'v1.1.0'),
                                      ('fix!: require external INI', 'v2.0.0')]:
                git('commit', '--allow-empty', '-m', message)
                before = git('rev-parse', 'HEAD')
                result = subprocess.run([*PSR, '--print-tag'], cwd=tmp, check=True,
                                        capture_output=True, text=True)
                self.assertEqual(result.stdout.strip(), expected)
                self.assertEqual(git('rev-parse', 'HEAD'), before)
                self.assertEqual(git('status', '--porcelain'), '')
                self.assertEqual(git('tag'), 'v1.0.0')
            before = git('rev-parse', 'HEAD')
            subprocess.run([*PSR, '--no-commit', '--no-changelog', '--skip-build',
                            '--no-push', '--no-vcs-release'], cwd=tmp, check=True,
                           capture_output=True, text=True)
            self.assertEqual(git('rev-parse', 'v2.0.0^{commit}'), before)
            self.assertEqual(git('rev-parse', 'HEAD'), before)
            self.assertEqual(git('status', '--porcelain'), '')


if __name__ == '__main__':
    unittest.main()
