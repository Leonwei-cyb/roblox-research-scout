"""Deterministic tests for the independent public research health monitor."""
import importlib.util
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

module_path = Path(__file__).resolve().parents[1] / "scripts" / "bot_supervisor.py"
spec = importlib.util.spec_from_file_location("public_research_health_supervisor", module_path)
supervisor = importlib.util.module_from_spec(spec)
spec.loader.exec_module(supervisor)

NOW = datetime(2026, 10, 18, 20, 0, tzinfo=timezone.utc)


def run(hours_ago, conclusion="success", status="completed",
        branch="main", event="schedule", number=1):
    timestamp = (NOW - timedelta(hours=hours_ago)).isoformat().replace("+00:00", "Z")
    return {
        "id": number, "status": status, "conclusion": conclusion,
        "created_at": timestamp, "updated_at": timestamp,
        "head_branch": branch, "event": event,
        "html_url": "https://github.com/Leonwei-cyb/roblox-research-scout/actions/runs/" + str(number)
    }


class HealthMonitorTests(unittest.TestCase):
    def test_latest_success_and_recent_failure_count(self):
        rows = [run(1, number=3), run(7, conclusion="failure", number=2),
                run(13, number=1)]
        state, latest, failed = supervisor.research_status(rows, now=NOW)
        self.assertEqual("OK", state)
        self.assertEqual(3, latest["id"])
        self.assertEqual(1, failed)

    def test_latest_failure_requests_attention(self):
        state, _, fails = supervisor.research_status(
            [run(1, conclusion="failure")], now=NOW)
        self.assertEqual("ATTENTION", state)
        self.assertEqual(1, fails)

    def test_ten_hour_stale_threshold_respects_six_hour_schedule(self):
        self.assertEqual("OK", supervisor.research_status([run(8)], now=NOW)[0])
        self.assertEqual("STALE", supervisor.research_status([run(11)], now=NOW)[0])

    def test_other_branches_do_not_mask_failed_main(self):
        rows = [run(0.3, branch="feature", event="pull_request", number=5),
                run(2, conclusion="failure", number=4)]
        state, latest, _ = supervisor.research_status(rows, now=NOW)
        self.assertEqual("ATTENTION", state)
        self.assertEqual(4, latest["id"])

    def test_running_job_is_not_a_failure(self):
        rows = [run(0.1, conclusion=None, status="in_progress", number=2),
                run(6, number=1)]
        self.assertEqual("OK", supervisor.research_status(rows, now=NOW)[0])

    def test_no_completed_runs_are_not_reported_healthy(self):
        self.assertEqual("NO COMPLETED RESEARCH RUN",
                         supervisor.research_status([], now=NOW)[0])
        self.assertEqual("NO COMPLETED RESEARCH RUN",
                         supervisor.research_status([
                            run(0.1, conclusion=None, status="in_progress")
                         ], now=NOW)[0])

    def test_missing_run_timestamp_is_unknown_not_healthy(self):
        row = run(1)
        row.pop("updated_at")
        row.pop("created_at")
        self.assertEqual("UNKNOWN RUN AGE",
                         supervisor.research_status([row], now=NOW)[0])

    def test_status_summary_is_workflow_specific(self):
        state, report = supervisor.live_report([run(1)], now=NOW)
        self.assertEqual("OK", state)
        self.assertIn("research.yml only", report)
        self.assertIn("does **not** mean individual X", report)
        self.assertIn("runs/1", report)

    def test_monitor_writes_summary_not_repository_report(self):
        # Freeze the monitor clock as well as its fabricated workflow timestamps.
        # Otherwise this test fails merely because real time advances.
        original_live_report = supervisor.live_report
        with tempfile.TemporaryDirectory() as temp:
            step_summary = Path(temp) / "job-summary.md"
            tracked_report = Path(temp) / "tracked.md"
            with patch.dict(supervisor.os.environ, {"GITHUB_STEP_SUMMARY": str(step_summary)}), \
                 patch.object(supervisor, "OUT", tracked_report), \
                 patch.object(supervisor, "research_runs_for", return_value=[run(1)]), \
                 patch.object(supervisor, "live_report", side_effect=lambda rows: original_live_report(rows, now=NOW)):
                result = supervisor.monitor()
            self.assertEqual("OK", result)
            self.assertTrue(step_summary.is_file())
            self.assertFalse(tracked_report.exists())

    def test_api_outage_is_not_reported_as_bot_failure(self):
        with tempfile.TemporaryDirectory() as temp:
            step_summary = Path(temp) / "job-summary.md"
            with patch.dict(supervisor.os.environ, {"GITHUB_STEP_SUMMARY": str(step_summary)}), \
                 patch.object(supervisor, "research_runs_for", side_effect=RuntimeError("GitHub HTTP 503")):
                result = supervisor.monitor()
            self.assertEqual("API UNAVAILABLE", result)
            self.assertIn("not proof", step_summary.read_text())


if __name__ == "__main__":
    unittest.main()
