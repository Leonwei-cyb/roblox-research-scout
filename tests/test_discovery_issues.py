"""Offline tests for scripts/discovery_issues.py (dedup, budget, home-repo only)."""
import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("discovery_issues", ROOT / "scripts" / "discovery_issues.py")
di = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(di)


def cand(repo, score=90, verdict="needs-test", audited=None):
    return {"repo": repo, "sha": "a" * 40, "version": "head", "license": "MIT", "days_since_commit": 3,
            "mode": "browser-session", "pack_verdict": verdict, "pack_reason": "evidence", "found_by": ["a"],
            "rank_score": score, "browser_evidence": ["content scripts on chat sites"], "api_evidence": [],
            "files_inspected": ["manifest.json"], "tests_found": 1, "suggested_owner": "Wheel",
            "audited_elsewhere": audited, "evidence": ["https://github.com/" + repo]}


class IssueRoutingTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        packs = Path(tmp.name) / "packs"
        packs.mkdir()
        report = {"pack": "p", "label": "Pack", "run_at": "2026-10-20T06:00:00Z", "candidates": [
            cand("new/one", 95), cand("old/two", 90), cand("busy/three", 99, audited="Wheel audits it"),
            cand("low/four", 20), cand("rej/five", 99, verdict="reject"), cand("new/six", 80), cand("new/seven", 70),
            cand("new/eight", 65)]}
        (packs / "p.json").write_text(json.dumps(report))
        p = patch.object(di, "PACKS", packs)
        p.start()
        self.addCleanup(p.stop)
        self.ledger = Path(tmp.name) / "issue_ledger.json"
        p = patch.object(di, "LEDGER", self.ledger)
        p.start()
        self.addCleanup(p.stop)
        self.listing_lags = False
        self.posts = []
        existing = [{"number": 4, "body": "old lead\n<!-- discovery-key: old/two -->"}]

        def fake_request(method, path, token, body=None):
            if method == "GET":
                if self.listing_lags:
                    return existing[:1] if "page=1" in path else []
                return existing if "page=1" in path else []
            self.posts.append((path, body))
            number = 10 + len(self.posts)
            existing.insert(0, {"number": number, "body": body["body"]})
            return {"number": number}

        p = patch.object(di, "request", fake_request)
        p.start()
        self.addCleanup(p.stop)

    def test_dedup_budget_and_skips(self):
        with patch.dict(os.environ, {"GITHUB_TOKEN": "t", "GITHUB_REPOSITORY": di.HOME_REPO}):
            di.main([])
        titles = [b["title"] for _, b in self.posts]
        self.assertEqual(3, len(titles))                        # budget
        self.assertTrue(titles[0].startswith("[Discovery] new/one"))
        joined = " ".join(titles)
        for skipped in ("old/two", "busy/three", "low/four", "rej/five"):
            self.assertNotIn(skipped, joined)
        self.assertTrue(all(path == "/repos/" + di.HOME_REPO + "/issues" for path, _ in self.posts))
        body = self.posts[0][1]["body"]
        self.assertIn("<!-- discovery-key: new/one -->", body)
        self.assertIn("Suggested owner:** Wheel", body)
        self.assertIn("Not installed, not run", body)

    def test_back_to_back_run_with_lagging_listing_opens_no_duplicate(self):
        """Live defect 2026-10-20: a rerun seconds later opened #17-#19 as duplicates of #14-#16."""
        with patch.dict(os.environ, {"GITHUB_TOKEN": "t", "GITHUB_REPOSITORY": di.HOME_REPO}):
            di.main([])
            first = len(self.posts)
            self.listing_lags = True          # the new issues are not in the listing yet
            di.main([])
        new_titles = [b["title"] for _, b in self.posts[first:]]
        self.assertEqual(3, first)
        for _, b in self.posts[:first]:
            self.assertNotIn(b["title"], new_titles)

    def test_oldest_issue_wins_when_duplicates_exist(self):
        rows = [{"number": 19, "body": "<!-- discovery-key: a/b -->"}, {"number": 14, "body": "<!-- discovery-key: a/b -->"}]
        with patch.object(di, "request", lambda m, p, t, b=None: rows if "page=1" in p else []):
            self.assertEqual({"a/b": 14}, di.existing_keys(di.HOME_REPO, "t"))

    def test_renamed_repo_is_matched_by_github_id(self):
        """Codex P2 (PR #20): a rename changed owner/repo, so a name-only marker missed the old issue."""
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        packs = Path(tmp.name)
        c = cand("new-owner/renamed", 95)
        c["repo_id"] = 4242
        (packs / "p.json").write_text(json.dumps({"pack": "p", "label": "P", "run_at": "x", "candidates": [c]}))
        rows = [{"number": 7, "body": "old\n<!-- discovery-key: id:4242 -->\n<!-- discovery-key: old-owner/name -->"}]
        posts = []
        def fake(method, path, token, body=None):
            if method == "GET":
                return rows if "page=1" in path else []
            posts.append(body)
            return {"number": 99}
        with patch.object(di, "PACKS", packs), patch.object(di, "request", fake), \
                patch.dict(os.environ, {"GITHUB_TOKEN": "t", "GITHUB_REPOSITORY": di.HOME_REPO}):
            di.main([])
        self.assertEqual([], posts)

    def test_new_issue_carries_id_and_name_markers(self):
        c = cand("a/b")
        c["repo_id"] = 5
        body = di.issue_body({"pack": "p", "label": "P", "run_at": "x"}, c)
        self.assertIn("<!-- discovery-key: id:5 -->", body)
        self.assertIn("<!-- discovery-key: a/b -->", body)

    def test_deferred_inspection_is_never_routed(self):
        c = cand("x/y", 99)
        c["inspection_error"] = "core budget low"
        self.assertEqual([], di.selected([{"candidates": [c]}]))

    def test_dry_run_never_posts(self):
        with patch.dict(os.environ, {"GITHUB_TOKEN": "t", "GITHUB_REPOSITORY": di.HOME_REPO}):
            di.main(["--dry-run"])
        self.assertEqual([], self.posts)

    def test_refuses_other_repositories(self):
        with patch.dict(os.environ, {"GITHUB_TOKEN": "t", "GITHUB_REPOSITORY": "Leonwei-cyb/Roblox-Studio-Hub"}):
            with self.assertRaises(SystemExit):
                di.main([])
        self.assertEqual([], self.posts)


if __name__ == "__main__":
    unittest.main()
