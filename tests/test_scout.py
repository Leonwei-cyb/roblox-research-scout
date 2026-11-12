"""Mocked, offline tests: no GitHub token, API calls, or CI minutes needed."""
import importlib.util
import os
import sys
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))

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
            patch.object(scout, "HEALTH", self.root / "watch" / "github_source_health.md"),
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

    def test_full_watchlist_and_failure_isolation(self):
        config=json.loads(scout.CONFIG.read_text())
        config["watch_repos"]=["owner/project"]+[f"owner/project-{i}" for i in range(16)]
        scout.CONFIG.write_text(json.dumps(config))
        def flaky_api(path,params=None):
            if "/repos/owner/project-2" in path and path == "/repos/owner/project-2":
                raise RuntimeError("HTTP 429")
            return self.fake_api(path,params) if path.startswith("/search/") or path.startswith("/repos/owner/project") and not any(
                path.startswith("/repos/owner/project-") for _ in [0]
            ) else ({"full_name":"repo"} if path.count("/") == 3 else
                   {"tag_name":"v1"} if "releases/latest" in path else
                   [{"sha":self.sha,"commit":{"message":"OK"}}])
        with patch.object(scout,"api_get",side_effect=flaky_api):
            scout.run()
        health=scout.HEALTH.read_text()
        self.assertIn("Watchlist configured: 17",health)
        self.assertIn("Watchlist attempted: 17",health)
        self.assertIn("Repositories successfully checked: 16",health)

    def test_hosted_autofix_is_bounded_and_does_not_touch_mac(self):
        feeds=self.root/"watch/feeds.json"
        feeds.write_text(json.dumps({"feeds":[{"id":"a","url":"https://a"},{"id":"a","url":"https://a"}]}))
        original_cfg=json.loads(scout.CONFIG.read_text())
        original_cfg["watch_repos"]=["owner/project","owner/project"]
        scout.CONFIG.write_text(json.dumps(original_cfg))
        with patch.dict(os.environ,{"GITHUB_ACTIONS":"false"}):
            self.assertEqual(scout.hosted_config_autofix(self.root),[])
        self.assertEqual(len(json.loads(scout.CONFIG.read_text())["watch_repos"]),2)
        with patch.dict(os.environ,{"GITHUB_ACTIONS":"true"}):
            updated=scout.hosted_config_autofix(self.root)
        self.assertEqual(updated,[("watch/config.json",{"watch_repos":1}),("watch/feeds.json",{"feeds":1})])
        self.assertEqual(len(json.loads(scout.CONFIG.read_text())["watch_repos"]),1)
        self.assertEqual(len(json.loads(feeds.read_text())["feeds"]),1)

    def test_no_arbitrary_repository_names(self):
        with self.assertRaises(ValueError):
            scout.snapshot_repo("https://evil.com/payload")
        self.assertNotIn(chr(96), scout.safe("a" + chr(96) + "b"))
        self.assertIn("\\[", scout.safe("[title]"))


if __name__ == "__main__":
    unittest.main()
