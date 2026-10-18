"""Mocked, offline tests: no GitHub token, API calls, or CI minutes needed."""
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location("scout", Path(__file__).resolve().parents[1] / "scripts" / "scout.py")
scout = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(scout)


class ScoutTest(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.root = Path(self.folder.name)
        (self.root / "watch").mkdir()
        (self.root / "watch" / "config.json").write_text(json.dumps({
            "watch_repos": ["owner/project"],
            "discovery_queries": ["roblox mcp"],
            "min_stars": 10,
            "results_per_query": 12,
        }))
        self.patches = [
            patch.object(scout, "CONFIG", self.root / "watch" / "config.json"),
            patch.object(scout, "STATE", self.root / "watch" / "state.json"),
            patch.object(scout, "REPORT", self.root / "watch" / "latest.md"),
        ]
        for patcher in self.patches:
            patcher.start()
            self.addCleanup(patcher.stop)
        self.addCleanup(self.folder.cleanup)
        self.tag = "v1"
        self.sha = "a" * 40
        self.leads = [{"full_name": "foo/new-tool", "stargazers_count": 48, "description": "Roblox tool", "fork": False, "archived": False}]

    def fake_api(self, path, params=None):
        if path == "/repos/owner/project":
            return {"full_name": "owner/project"}
        if path.endswith("/releases/latest"):
            return {"tag_name": self.tag, "html_url": "https://github.com/owner/project/releases/tag/" + self.tag}
        if path.endswith("/commits"):
            return [{"sha": self.sha, "commit": {"message": "Fix UI layout\nother"}}]
        if path == "/search/repositories":
            return {"items": self.leads}
        raise AssertionError(path)

    def test_baseline_and_no_spam(self):
        with patch.object(scout, "api_get", self.fake_api):
            scout.run()
            initial = scout.REPORT.read_text()
            self.assertIn("initial baseline", initial)
            self.assertIn("foo/new-tool", initial)
            scout.run()
            self.assertEqual(initial, scout.REPORT.read_text())

    def test_detect_new_release_and_candidate(self):
        with patch.object(scout, "api_get", self.fake_api):
            scout.run()
            self.tag = "v2"
            self.leads.append({"full_name": "bar/studio-agent", "stargazers_count": 96, "description": "New workflow", "fork": False, "archived": False})
            scout.run()
            report = scout.REPORT.read_text()
            self.assertIn("v1 → v2", report)
            self.assertIn("bar/studio-agent", report)
            scout.run()
            self.assertEqual(report, scout.REPORT.read_text())

    def test_no_arbitrary_repository_names(self):
        with self.assertRaises(ValueError):
            scout.snapshot_repo("https://evil.com/payload")
        self.assertNotIn(chr(96), scout.safe("a" + chr(96) + "b"))
        self.assertIn("\\[", scout.safe("[title]"))


if __name__ == "__main__":
    unittest.main()
