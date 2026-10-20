"""All research workflows must be manual-only while the Mac is the scheduler.

This catches accidental reintroduction of paid GitHub-hosted automatic runs.
No third-party dependencies or API calls are required.
"""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github" / "workflows"


class LocalOnlyWorkflowsTests(unittest.TestCase):
    def test_all_hosted_workflows_require_manual_trigger(self):
        paths = sorted(WORKFLOWS.glob("*.yml"))
        self.assertGreaterEqual(len(paths), 6)
        for path in paths:
            data = path.read_text(encoding="utf-8")
            self.assertIn("\non:\n  workflow_dispatch:", data, path.name)
            self.assertEqual(len(re.findall(r"^on:$", data, re.MULTILINE)), 1, path.name)
            # Only inspect the top-level trigger section, not jobs/steps.
            section = data.split("\non:\n", 1)[1].split("\npermissions:", 1)[0]
            for trigger in ("schedule", "push", "pull_request", "workflow_run",
                            "repository_dispatch", "issues", "pull_request_target"):
                self.assertNotRegex(section, rf"^  {trigger}:", path.name)
            self.assertNotRegex(section, r"^\s+- cron:", path.name)


if __name__ == "__main__":
    unittest.main()
