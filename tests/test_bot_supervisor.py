import importlib.util
import unittest
from unittest.mock import patch
from pathlib import Path

p = Path(__file__).resolve().parents[1] / "scripts/bot_supervisor.py"
s = importlib.util.spec_from_file_location("bot_supervisor", p)
m = importlib.util.module_from_spec(s)
s.loader.exec_module(m)

class SupervisorTests(unittest.TestCase):
    def test_committed_health_report_checks_research_only(self):
        mocked = [{"status": "completed", "conclusion": "failure"}]
        with patch.object(m, "research_runs_for", return_value=mocked) as fetch:
            self.assertEqual(m.runs_for("Leonwei-cyb/roblox-research-scout"), mocked)
            fetch.assert_called_once_with("Leonwei-cyb/roblox-research-scout")

    def test_mixed_runs(self):
        runs = [
            {"status":"in_progress", "conclusion":None},
            {"status":"completed", "conclusion":"success","html_url":"https://github.com/a/b/actions/runs/1"},
            {"status":"completed", "conclusion":"failure","html_url":"https://github.com/a/b/actions/runs/2"},
        ]
        self.assertEqual(m.summarize("a/b", runs)[0], "OK")
        self.assertEqual(m.summarize("a/b", runs)[1], 1)
    def test_failure_and_empty(self):
        self.assertEqual(m.summarize("a/b", [dict(status="completed",conclusion="failure")])[0], "ATTENTION")
        self.assertEqual(m.summarize("a/b", [])[0], "NO COMPLETED RUN")
    def test_report(self):
        text = m.render([("a/b",[dict(status="completed",conclusion="success",
            html_url="https://github.com/a/b/actions/runs/1")])])
        self.assertIn("a/b", text)
        self.assertIn("source_health.md", text)

if __name__ == "__main__":
    unittest.main()
