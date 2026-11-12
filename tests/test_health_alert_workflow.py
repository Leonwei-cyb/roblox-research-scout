"""Static regression checks for the trusted public research failure notifier.

The PR test job cannot manufacture a real failed GitHub workflow_run event.
These tests verify the critical event/permission/dedup structure before merge.
"""
import unittest
from pathlib import Path

WORKFLOW = Path(__file__).resolve().parents[1] / ".github/workflows/health-monitor.yml"


class HealthAlertWorkflowTests(unittest.TestCase):
    def test_mac_only_scheduler_and_manual_actions_fallback(self):
        data = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("on:\n  workflow_dispatch:", data)
        trigger_block = data.split("\non:\n", 1)[1].split("\npermissions:", 1)[0]
        for event in ("  workflow_run:", "  schedule:", "  push:",
                      "  pull_request:", "  repository_dispatch:"):
            self.assertNotIn(event, trigger_block)

    def test_notifier_is_its_own_job_not_root_yaml(self):
        data = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("\n  notify-failure:\n", data)
        self.assertNotIn("\nnotify-failure:\n", data)
        self.assertIn("github.event.workflow_run.conclusion == 'failure'", data)
        self.assertIn("run.head_branch !== 'main'", data)

    def test_notifier_deduplicates_and_never_merges_or_writes_game_source(self):
        data = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("github.rest.issues.listForRepo", data)
        self.assertIn("existing.some", data)
        self.assertIn("github.rest.issues.create", data)
        self.assertNotIn("github.rest.pulls.merge", data)
        self.assertNotIn("git push", data)

    def test_issues_write_limited_to_failure_job(self):
        data = WORKFLOW.read_text(encoding="utf-8")
        first, separator, second = data.partition("  notify-failure:")
        self.assertTrue(separator)
        self.assertNotIn("issues: write", first)
        self.assertIn("      issues: write", second)
        self.assertIn("  contents: read", first)
        self.assertIn("  actions: read", first)


if __name__ == "__main__":
    unittest.main()
