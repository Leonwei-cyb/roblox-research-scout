"""No Mac UI, network, or screenshots in these tests."""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import peekaboo_handoff as h

INDEX = {"posts": [
    {"key": "instagram:AA", "url": "https://www.instagram.com/reel/AA",
     "kind": "instagram", "evidence": "UNVIEWED_METADATA"},
    {"key": "youtube:ABC", "url": "https://youtube.com/watch?v=ABCDEFGHIJK",
     "kind": "youtube", "evidence": "UNVIEWED_METADATA"},
    {"key": "reddit:123", "url": "https://reddit.com/r/roblox/comments/123/post",
     "kind": "reddit", "evidence": "UNVIEWED_METADATA"},
]}


class ResearchPeekabooHandoffTests(unittest.TestCase):
    def test_prepare_does_not_launch_any_app(self):
        with patch.object(h.subprocess, "run") as run:
            r = h.prepare("instagram:AA", INDEX)
        run.assert_not_called()
        self.assertFalse(r["video_watched"])
        self.assertFalse(r["original_post_opened"])
        self.assertEqual(r["status"], "AWAITING_ORIGINAL_REVIEW")

    def test_unlisted_and_non_social_sources_are_refused(self):
        for key in ("missing", "reddit:123"):
            with self.assertRaises(ValueError):
                h.prepare(key, INDEX)

    def test_missing_local_probe_does_not_launch(self):
        with patch.object(h.subprocess, "run") as run:
            with self.assertRaisesRegex(ValueError, "adapter missing"):
                h.capture("instagram:AA", "Google Chrome", 55, INDEX,
                          probe=Path("/an/unavailable/local/probe.py"))
        run.assert_not_called()

    def test_reject_non_browser_and_invalid_id(self):
        with patch.object(Path, "is_file", return_value=True):
            with self.assertRaises(ValueError):
                h.capture("instagram:AA", "Terminal", 55, INDEX)
            with self.assertRaises(ValueError):
                h.capture("instagram:AA", "Google Chrome", 0, INDEX)

    def test_no_capture_without_positive_receipt(self):
        with patch.object(Path, "is_file", return_value=True), \
             patch.object(h.subprocess, "run", return_value=type("R", (), {
                 "returncode": 0, "stdout": '{"status":"BLOCKED"}'})()):
            with self.assertRaisesRegex(ValueError, "verified"):
                h.capture("instagram:AA", "Safari", 7, INDEX)

    def test_success_does_not_mean_a_post_was_inspected(self):
        with patch.object(Path, "is_file", return_value=True), \
             patch.object(h.subprocess, "run", return_value=type("R", (), {
                 "returncode": 0, "stdout": '{"status":"OBSERVED_READ_ONLY","local_only":true}'})()) as run:
            r = h.capture("instagram:AA", "Safari", 7, INDEX)
        self.assertEqual(r["status"], "CAPTURE_ONLY_UNVERIFIED_CONTENT")
        self.assertFalse(r["original_post_opened"])
        self.assertFalse(r["video_watched"])
        self.assertFalse(r["social_feed_access_unlocked"])
        args = run.call_args.args[0]
        self.assertEqual(args[-5:], ["--app", "Safari", "--window-id", "7", "--allow-browser"])
        self.assertNotIn("--allow-frontmost", args)
        self.assertNotIn("--keep-private", args)

    def test_native_failure_does_not_leak_cli_stderr(self):
        with patch.object(Path, "is_file", return_value=True), \
             patch.object(h.subprocess, "run", return_value=type("R", (), {
                 "returncode": 2, "stdout": "", "stderr": "Private browser window"})()):
            with self.assertRaisesRegex(ValueError, "refused or failed") as e:
                h.capture("instagram:AA", "Safari", 7, INDEX)
        self.assertNotIn("Private", str(e.exception))


if __name__ == "__main__":
    unittest.main()
