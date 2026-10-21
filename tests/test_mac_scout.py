"""Offline reliability tests: fake collectors and disposable Git repositories only."""
import fcntl
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import mac_scout as scout
from scheduler_owner import owns_job


class ReliabilityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.repo = self.root / 'repo'
        self.repo.mkdir()
        self.home = self.root / 'state'
        self.home.mkdir()
        self.stop = self.home / 'STOP'
        self.state = self.home / 'state.json'
        self.patches = [patch.object(scout, 'REPO', str(self.repo)),
                        patch.object(scout, 'HOME', str(self.home)),
                        patch.object(scout, 'STOP', str(self.stop)),
                        patch.object(scout, 'STATE', str(self.state)),
                        patch.object(scout, 'LOGS', str(self.root / 'logs'))]
        for p in self.patches:
            p.start()
            self.addCleanup(p.stop)

    def config(self, research='mac', discovery='mac'):
        path = self.repo / 'config/scheduler.json'
        path.parent.mkdir(exist_ok=True)
        path.write_text(json.dumps(dict(research=research, discovery=discovery)))
        return path

    def git(self, *args, cwd=None):
        return subprocess.run(['git', '-C', str(cwd or self.repo), *args],
                              check=True, capture_output=True, text=True).stdout.strip()

    def init_git(self):
        self.remote = self.root / 'remote.git'
        subprocess.run(['git', 'init', '--bare', str(self.remote)], check=True, capture_output=True)
        self.git('init', '-b', 'main')
        self.git('config', 'user.name', 'Offline test')
        self.git('config', 'user.email', 'test@example.invalid')
        (self.repo / 'watch').mkdir()
        (self.repo / 'watch/report.txt').write_text('original\n')
        self.git('add', '.')
        self.git('commit', '-m', 'initial')
        self.git('remote', 'add', 'origin', str(self.remote))
        self.git('push', '-u', 'origin', 'main')

    def test_sync_recovers_dirty_reports_after_remote_advances(self):
        self.init_git()
        other = self.root / 'other'
        subprocess.run(['git', 'clone', '-b', 'main', str(self.remote), str(other)], check=True, capture_output=True)
        self.git('config', 'user.name', 'Offline test', cwd=other)
        self.git('config', 'user.email', 'test@example.invalid', cwd=other)
        (other / 'watch/report.txt').write_text('remote edit\n')
        self.git('add', '.', cwd=other)
        self.git('commit', '-m', 'remote report', cwd=other)
        self.git('push', cwd=other)
        (self.repo / 'watch/report.txt').write_text('interrupted local report\n')
        (self.repo / 'watch/untracked.txt').write_text('partial output')
        scout.sync_repo()
        self.assertEqual('remote edit\n', (self.repo / 'watch/report.txt').read_text())
        self.assertEqual('', self.git('status', '--porcelain'))
        self.assertEqual(self.git('rev-parse', 'refs/heads/main', cwd=self.remote), self.git('rev-parse', 'HEAD'))

    def test_sync_recovers_interrupted_rebase(self):
        self.init_git()
        other = self.root / 'other'
        subprocess.run(['git', 'clone', '-b', 'main', str(self.remote), str(other)], check=True, capture_output=True)
        self.git('config', 'user.name', 'Offline test', cwd=other)
        self.git('config', 'user.email', 'test@example.invalid', cwd=other)
        (other / 'watch/report.txt').write_text('remote edit\n')
        self.git('add', '.', cwd=other)
        self.git('commit', '-m', 'remote report', cwd=other)
        self.git('push', cwd=other)
        (self.repo / 'watch/report.txt').write_text('local commit\n')
        self.git('add', '.')
        self.git('commit', '-m', 'unpublished report')
        self.git('fetch', 'origin', 'main')
        result = subprocess.run(['git', '-C', str(self.repo), 'rebase', 'origin/main'], capture_output=True)
        self.assertNotEqual(0, result.returncode)
        scout.sync_repo()
        self.assertFalse((self.repo / '.git/rebase-merge').exists())
        self.assertFalse((self.repo / '.git/rebase-apply').exists())
        self.assertEqual('', self.git('status', '--porcelain'))
        self.assertEqual(self.git('rev-parse', 'refs/heads/main', cwd=self.remote), self.git('rev-parse', 'HEAD'))

    def test_publication_unchanged_and_success(self):
        self.init_git()
        self.assertEqual('unchanged', scout.publish(['watch/'], 'report')['status'])
        (self.repo / 'watch/report.txt').write_text('updated\n')
        result = scout.publish(['watch/'], 'report')
        self.assertEqual('published', result['status'])
        self.assertEqual(self.git('rev-parse', 'refs/heads/main', cwd=self.remote), result['sha'])

    def test_push_rejection_is_failure(self):
        self.init_git()
        hook = self.remote / 'hooks/pre-receive'
        hook.write_text('#!/bin/sh\nexit 1\n')
        hook.chmod(0o755)
        before = self.git('rev-parse', 'HEAD')
        (self.repo / 'watch/report.txt').write_text('updated\n')
        with patch.object(scout.time, 'sleep'):
            result = scout.publish(['watch/'], 'report')
        self.assertEqual({'status': 'failed', 'reason': 'push retries exhausted', 'sha': None}, result)
        self.assertEqual(before, self.git('rev-parse', 'refs/heads/main', cwd=self.remote))

    def test_rebase_conflict_is_failure_and_aborts(self):
        self.init_git()
        other = self.root / 'other'
        subprocess.run(['git', 'clone', '-b', 'main', str(self.remote), str(other)], check=True, capture_output=True)
        self.git('config', 'user.name', 'Offline test', cwd=other)
        self.git('config', 'user.email', 'test@example.invalid', cwd=other)
        (other / 'watch/report.txt').write_text('remote edit\n')
        self.git('add', '.', cwd=other)
        self.git('commit', '-m', 'concurrent report', cwd=other)
        self.git('push', cwd=other)
        (self.repo / 'watch/report.txt').write_text('local edit\n')
        result = scout.publish(['watch/'], 'report')
        self.assertEqual('failed', result['status'])
        self.assertEqual('rebase conflict', result['reason'])
        self.assertFalse((self.repo / '.git/rebase-merge').exists())

    def cycle(self, state, publication, codes=None):
        self.config(discovery='paused')
        with patch.object(scout, 'sync_repo'), patch.object(scout, 'token', return_value='fake'), \
             patch.object(scout, 'last_report_age', return_value=None), \
             patch.object(scout.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0)), \
             patch.object(scout, 'step', side_effect=lambda n, *_: (codes or {}).get(n, 0)), \
             patch.object(scout, 'publish', return_value=publication):
            return scout.cycle(state)

    def test_failed_publish_keeps_job_due(self):
        state = {'last_research': 1}
        ok, receipt = self.cycle(state, {'status': 'failed', 'sha': None, 'reason': 'push retries exhausted'})
        self.assertFalse(ok)
        self.assertEqual(1, state['last_research'])
        self.assertEqual('failed', receipt['publication']['research']['status'])

    def test_unchanged_success_advances_timestamp(self):
        state = {}
        ok, _ = self.cycle(state, {'status': 'unchanged', 'sha': None})
        self.assertTrue(ok)
        self.assertIn('last_research', state)

    def test_collector_failure_does_not_advance_timestamp(self):
        state = {}
        ok, _ = self.cycle(state, {'status': 'published', 'sha': 'fake'}, {'research_quality': 1})
        self.assertFalse(ok)
        self.assertNotIn('last_research', state)

    def test_force_cannot_override_other_scheduler(self):
        self.config('github', 'github')
        with patch.object(scout, 'sync_repo'), patch.object(scout, 'token') as token:
            ok, receipt = scout.cycle({}, force_research=True)
        self.assertTrue(ok)
        self.assertEqual('nothing due', receipt['skipped'])
        token.assert_not_called()

    def test_local_lock_rejects_second_worker(self):
        with (self.home / 'lock').open('w') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            with patch.object(scout, 'cycle') as cycle:
                self.assertEqual(0, scout.run())
                cycle.assert_not_called()

    def test_stop_at_start_never_syncs(self):
        self.stop.touch()
        with patch.object(scout, 'sync_repo') as sync:
            self.assertEqual(0, scout.run())
            sync.assert_not_called()

    def test_fake_collector_stop_prevents_next_collector_and_publish(self):
        scripts = self.repo / 'scripts'
        scripts.mkdir()
        (scripts / 'first.py').write_text('from pathlib import Path\nPath(' + repr(str(self.stop)) + ').touch()\n')
        (scripts / 'second.py').write_text('raise RuntimeError("must not execute")\n')
        self.assertEqual(0, scout.step('first', dict(os.environ), scout.now() + 10))
        with self.assertRaises(scout.Stopped):
            scout.step('second', dict(os.environ), scout.now() + 10)
        with patch.object(scout, 'git') as git:
            with self.assertRaises(scout.Stopped):
                scout.publish(['watch/'], 'must not publish')
            git.assert_not_called()

    def test_stop_during_fetch_prevents_push(self):
        calls = []
        def fake_git(*args, **kwargs):
            calls.append(args[0])
            if args[0] == 'fetch':
                self.stop.touch()
            return 'watch/report.txt' if args[0] == 'diff' else ''
        with patch.object(scout, 'git', side_effect=fake_git), \
             patch.object(scout.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0)) as run:
            with self.assertRaises(scout.Stopped):
                scout.publish(['watch/'], 'report')
            self.assertFalse(any('push' in call.args[0] for call in run.call_args_list))

    def test_expired_deadline_never_starts_child(self):
        with patch.object(scout.subprocess, 'run') as run:
            with self.assertRaises(TimeoutError):
                scout.step('fake', {}, scout.now() - 1)
            run.assert_not_called()

    def test_failed_cycle_records_backoff(self):
        with patch.object(scout, 'cycle', return_value=(False, {'publication': {'research': {'status': 'failed'}}})):
            self.assertEqual(1, scout.run())
        state = json.loads(self.state.read_text())
        self.assertEqual(1, state['failures'])
        self.assertGreater(state['backoff_until'], scout.now())
        self.assertNotIn('last_research', state)

    def test_stop_does_not_create_failure_backoff(self):
        with patch.object(scout, 'cycle', side_effect=scout.Stopped('STOP')):
            self.assertEqual(0, scout.run())
        self.assertNotIn('backoff_until', json.loads(self.state.read_text()))

    def test_ownership_is_exclusive_and_invalid_config_fails_closed(self):
        for owner in ('github', 'mac', 'paused'):
            path = self.config(owner, owner)
            self.assertEqual(owner == 'mac', owns_job(path, 'mac', 'research'))
            self.assertEqual(owner == 'github', owns_job(path, 'github', 'research'))
        for content in ('{}', 'null', '{"research":"mac","discovery":"typo"}', 'broken'):
            path.write_text(content)
            with self.assertRaises((ValueError, TypeError)):
                owns_job(path, 'mac', 'research')
        path.unlink()
        with self.assertRaises(FileNotFoundError):
            owns_job(path, 'mac', 'research')

    def test_discovery_failure_retries_despite_fresh_report(self):
        self.config('paused', 'mac')
        state = {'retry_discovery': True, 'last_discovery': scout.now()}
        with patch.object(scout, 'sync_repo'), patch.object(scout, 'token', return_value='fake'), \
             patch.object(scout, 'last_report_age', return_value=10), \
             patch.object(scout.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0)), \
             patch.object(scout, 'step', return_value=0) as step, \
             patch.object(scout, 'publish', return_value={'status': 'failed', 'sha': None, 'reason': 'push retries exhausted'}):
            ok, receipt = scout.cycle(state)
        self.assertFalse(ok)
        step.assert_called_once()
        self.assertTrue(state['retry_discovery'])
        self.assertEqual('failed', receipt['publication']['discovery']['status'])

    def test_success_clears_pending_retry(self):
        state = {'retry_research': True}
        ok, _ = self.cycle(state, {'status': 'published', 'sha': 'fake'})
        self.assertTrue(ok)
        self.assertNotIn('retry_research', state)

    def test_publication_rejects_pre_staged_code(self):
        self.init_git()
        (self.repo / 'code.py').write_text('print("not a report")')
        self.git('add', 'code.py')
        (self.repo / 'watch/report.txt').write_text('report update\n')
        before = self.git('rev-parse', 'refs/heads/main', cwd=self.remote)
        with self.assertRaisesRegex(RuntimeError, 'outside report paths'):
            scout.publish(['watch/'], 'report')
        self.assertEqual(before, self.git('rev-parse', 'refs/heads/main', cwd=self.remote))

    def test_publication_rejects_rename_from_code_into_reports(self):
        self.init_git()
        (self.repo / 'code.py').write_text('source')
        self.git('add', 'code.py')
        self.git('commit', '-m', 'source')
        self.git('push')
        self.git('mv', 'code.py', 'watch/code.txt')
        with self.assertRaisesRegex(RuntimeError, 'outside report paths'):
            scout.publish(['watch/'], 'report')

    def test_publication_rejects_leading_space_path(self):
        self.init_git()
        (self.repo / ' watch').mkdir()
        (self.repo / ' watch/rogue').write_text('not a report')
        self.git('add', ' watch/rogue')
        with self.assertRaisesRegex(RuntimeError, 'outside report paths'):
            scout.publish(['watch/'], 'report')

    def test_failed_research_publication_does_not_continue_to_discovery(self):
        self.config()
        state = {}
        with patch.object(scout, 'sync_repo'), patch.object(scout, 'token', return_value='fake'), \
             patch.object(scout, 'last_report_age', return_value=None), \
             patch.object(scout.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0)), \
             patch.object(scout, 'step', return_value=0) as step, \
             patch.object(scout, 'publish', return_value={'status': 'failed', 'sha': None, 'reason': 'rebase conflict'}) as publish:
            ok, _ = scout.cycle(state)
        self.assertFalse(ok)
        self.assertNotIn('discovery_scout', [call.args[0] for call in step.call_args_list])
        publish.assert_called_once()
        self.assertTrue(state['retry_research'])
        self.assertTrue(state['retry_discovery'])

    def test_exception_records_pending_retry_before_publication(self):
        self.config('paused', 'mac')
        with patch.object(scout, 'sync_repo'), patch.object(scout, 'token', return_value='fake'), \
             patch.object(scout, 'last_report_age', return_value=None), \
             patch.object(scout.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0)), \
             patch.object(scout, 'step', return_value=0), \
             patch.object(scout, 'publish', side_effect=TimeoutError('publication timed out')):
            self.assertEqual(1, scout.run())
        state = json.loads(self.state.read_text())
        self.assertTrue(state['retry_discovery'])
        self.assertNotIn('last_discovery', state)
        self.assertEqual(1, state['failures'])

    def test_collector_tokens_are_redacted_from_logs(self):
        result = subprocess.CompletedProcess([], 0, 'fake-child-token', '')
        with patch.object(scout.subprocess, 'run', return_value=result):
            scout.step('fake', {'GITHUB_TOKEN': 'fake-child-token'}, scout.now() + 10)
        logs = ''.join(path.read_text() for path in (self.root / 'logs').glob('*.log'))
        self.assertNotIn('fake-child-token', logs)
        self.assertIn('[REDACTED]', logs)

    def test_git_error_redacts_token_before_truncation(self):
        secret = 'ghp_' + 'x' * 40
        result = subprocess.CompletedProcess([], 1, '', 'bad ' * 70 + secret)
        with patch.dict(os.environ, {'GH_TOKEN': secret}), \
             patch.object(scout.subprocess, 'run', return_value=result):
            with self.assertRaises(RuntimeError) as error:
                scout.git('fetch')
        self.assertNotIn(secret[:12], str(error.exception))
        self.assertIn('[REDACTED]', str(error.exception))

    def test_rebase_timeout_aborts_and_is_bounded(self):
        def child(args, **kwargs):
            self.assertIsNotNone(kwargs.get('timeout'))
            if 'rebase' in args and '--abort' not in args:
                raise subprocess.TimeoutExpired(args, kwargs['timeout'])
            return subprocess.CompletedProcess(args, 0)
        with patch.object(scout, 'git', return_value='watch/report.txt'), \
             patch.object(scout.subprocess, 'run', side_effect=child) as run:
            with self.assertRaises(subprocess.TimeoutExpired):
                scout.publish(['watch/'], 'report')
        self.assertTrue(any('--abort' in call.args[0] for call in run.call_args_list))

    def test_stop_after_fetch_prevents_rebase(self):
        def fake_git(*args, **kwargs):
            if args[0] == 'fetch':
                self.stop.touch()
            return 'watch/report.txt' if args[0] == 'diff' else ''
        with patch.object(scout, 'git', side_effect=fake_git), \
             patch.object(scout.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0)) as run:
            with self.assertRaises(scout.Stopped):
                scout.publish(['watch/'], 'report')
        run.assert_not_called()

    def test_expired_deadline_prevents_publication(self):
        with patch.object(scout, 'git') as git:
            with self.assertRaises(TimeoutError):
                scout.publish(['watch/'], 'report', deadline=scout.now() - 1)
        git.assert_not_called()

    def test_hosted_publication_failures_exit_nonzero(self):
        root = Path(__file__).resolve().parents[1]
        for workflow in ('research', 'discovery'):
            for failure in ('push', 'conflict', 'staged_code'):
                with self.subTest(workflow=workflow, failure=failure):
                    # Each scenario has its own temporary bare remote and clone.
                    with tempfile.TemporaryDirectory() as tmp:
                        remote = Path(tmp) / 'remote.git'
                        repo = Path(tmp) / 'repo'
                        subprocess.run(['git', 'init', '--bare', str(remote)], check=True, capture_output=True)
                        subprocess.run(['git', 'init', '-b', 'main', str(repo)], check=True, capture_output=True)
                        self.git('config', 'user.name', 'Offline test', cwd=repo)
                        self.git('config', 'user.email', 'test@example.invalid', cwd=repo)
                        for directory in ('watch', 'findings', 'status'):
                            (repo / directory).mkdir()
                        for file in ('watch/report.txt', 'watch/discovery_state.json', 'status/discovery.json', 'findings/report.txt'):
                            (repo / file).write_text('original\n')
                        self.git('add', '.', cwd=repo)
                        self.git('commit', '-m', 'initial', cwd=repo)
                        self.git('remote', 'add', 'origin', str(remote), cwd=repo)
                        self.git('push', '-u', 'origin', 'main', cwd=repo)
                        target = 'watch/report.txt' if workflow == 'research' else 'findings/report.txt'
                        if failure == 'push':
                            hook = remote / 'hooks/pre-receive'
                            hook.write_text('#!/bin/sh\nexit 1\n')
                            hook.chmod(0o755)
                        elif failure == 'conflict':
                            other = Path(tmp) / 'other'
                            subprocess.run(['git', 'clone', '-b', 'main', str(remote), str(other)], check=True, capture_output=True)
                            self.git('config', 'user.name', 'Offline test', cwd=other)
                            self.git('config', 'user.email', 'test@example.invalid', cwd=other)
                            (other / target).write_text('remote change\n')
                            self.git('add', '.', cwd=other)
                            self.git('commit', '-m', 'remote change', cwd=other)
                            self.git('push', cwd=other)
                        if failure == 'staged_code':
                            (repo / 'code.py').write_text('not a report')
                            self.git('add', 'code.py', cwd=repo)
                        (repo / target).write_text('local change\n')
                        body = (root / '.github/workflows' / (workflow + '.yml')).read_text()
                        marker = '      - name: Commit reports only on changes' if workflow == 'research' else '      - name: Commit discovery outputs only'
                        shell = body.split(marker, 1)[1].split('        run: |\n', 1)[1].split('\n  route-issues:', 1)[0]
                        shell = '\n'.join(line[10:] for line in shell.splitlines())
                        output = Path(tmp) / 'output'
                        env = dict(os.environ, GITHUB_OUTPUT=str(output))
                        result = subprocess.run(['bash', '-e', '-c', 'sleep() { :; };\n' + shell], cwd=repo, env=env, capture_output=True, text=True)
                        self.assertNotEqual(0, result.returncode, result.stdout + result.stderr)
                        self.assertNotIn('published=true', output.read_text() if output.exists() else '')


class WorkflowOwnershipTests(unittest.TestCase):
    def test_existing_collector_steps_all_require_owner(self):
        root = Path(__file__).resolve().parents[1]
        for workflow, job in [('research', 'research'), ('discovery', 'discovery')]:
            body = (root / '.github/workflows' / (workflow + '.yml')).read_text()
            collector_job = body.split('\n  route-issues:')[0]
            steps = collector_job.split('      - name: ')[1:]
            self.assertIn('Check scheduler ownership', steps[0])
            self.assertIn('--owner github --job ' + job, steps[0])
            for step in steps[1:]:
                self.assertIn("steps.ownership.outputs.enabled == 'true'", step)
            if workflow == 'discovery':
                self.assertIn("needs.discover.outputs.published == 'true'", body)
                self.assertIn("if: success() && steps.ownership.outputs.enabled == 'true'", body)

    def test_cli_emits_no_enable_output_for_invalid_config(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            config = Path(tmp) / 'config.json'
            config.write_text('{}')
            result = subprocess.run([sys.executable, str(root / 'scripts/scheduler_owner.py'),
                                     '--owner', 'github', '--job', 'research', '--config', str(config)],
                                    capture_output=True, text=True)
            self.assertNotEqual(0, result.returncode)
            self.assertNotIn('enabled=true', result.stdout)


if __name__ == '__main__':
    unittest.main()
