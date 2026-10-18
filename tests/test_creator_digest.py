"""Tests for creator-source identity safety and video attribution. No network/AI."""
import importlib.util
import unittest
from pathlib import Path

path = Path(__file__).resolve().parents[1] / "scripts" / "creator_digest.py"
spec = importlib.util.spec_from_file_location("creator_digest", path)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class CreatorDigestTests(unittest.TestCase):
    def setUp(self):
        self.brock = {
            "id": "brockodile",
            "label": "Brockodile — Steal An Egg",
            "focus": "game design",
            "source_of_identity": "https://linktr.ee/Brockodile",
            "aliases": ["Brockodile", "Brockkodile", "Steal An Egg"],
            "candidate_youtube_channel_id": "UC1g8RAPLVidtYUzZFFiX2GA",
            "accounts": [
                {"platform": "instagram", "url": "https://www.instagram.com/brockkodile/",
                 "provenance": "developer Linktree", "direct_posts_access": "not verified"}
            ]
        }

    def test_direct_candidate_video_not_confused_with_linktree(self):
        row = {"source": "youtube-UC1g8RAPLVidtYUzZFFiX2GA",
               "title": "Building a Roblox tycoon", "url": "https://www.youtube.com/watch?v=123"}
        self.assertIn("identity check", m.matches(row, self.brock))
        self.assertIn("creator identity check", m.render([self.brock], [row]))

    def test_indexed_brock_name_not_claimed_authored(self):
        row = {"source": "brock-ig", "title": "Brockodile Roblox devlog",
               "url": "https://news.google.com/rss/articles/encoded"}
        self.assertIn("NOT verified", m.matches(row, self.brock))
        self.assertIn("authorship NOT verified", m.render([self.brock], [row]))

    def test_generic_steal_an_egg_spam_does_not_match_developer(self):
        row = {"source": "tiktok-index",
               "title": "Steal An Egg birthday supplies discount",
               "url": "https://news.google.com/rss/articles/other"}
        self.assertIsNone(m.matches(row, self.brock))
        self.assertIn("None verified", m.render([self.brock], [row]))

    def test_other_developer_does_not_match(self):
        row = {"source": "other", "title": "Tizzy RBLX gameplay",
               "url": "https://www.youtube.com/watch?v=456"}
        self.assertIsNone(m.matches(row, self.brock))


if __name__ == "__main__":
    unittest.main()
