"""No-network tests: direct video links beat indexed social search noise."""
import importlib.util
import unittest
from pathlib import Path

path = Path(__file__).resolve().parents[1] / "scripts" / "video_shortlist.py"
spec = importlib.util.spec_from_file_location("video_shortlist", path)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def item(title, url, category="youtube", date="2026-10-17"):
    return {"title": title, "url": url, "category": category, "published": date, "excerpt": ""}


class VideoShortlistTests(unittest.TestCase):
    def test_direct_sources(self):
        self.assertEqual(m.kind(item("x", "https://www.youtube.com/watch?v=123")), "YouTube video")
        self.assertEqual(m.kind(item("x", "https://www.tiktok.com/@user/video/12345")), "TikTok original video")
        self.assertEqual(m.kind(item("x", "https://www.instagram.com/reel/ABCabc_42/")), "Instagram original Reel/post")
        self.assertEqual(m.kind(item("x", "https://x.com/creator/status/12345")), "X original post")
        self.assertIsNone(m.kind(item("x", "https://news.google.com/rss/articles/ABCDE")))

    def test_prevents_unrelated_news_and_promotional_posts(self):
        rows = [
            item("join our discord #robloxdev", "https://www.youtube.com/watch?v=spam"),
            item("Free Roblox Crack download", "https://www.youtube.com/watch?v=bad"),
            item("Rapid Creation with Agentic Studio Roblox", "https://www.youtube.com/watch?v=good"),
            item("Roblox UI design tips", "https://news.google.com/rss/articles/UNVERIFIED", "Instagram indexed leads"),
            item("A real Roblox devlog", "https://www.tiktok.com/@coder/video/1234", "tiktok"),
        ]
        picks = m.shortlist(rows)
        self.assertEqual(len(picks), 2)
        self.assertEqual(picks[0][0]["url"], "https://www.youtube.com/watch?v=good")
        report = m.report(rows)
        self.assertIn("verified original video/post URL", report)
        self.assertNotIn("watch?v=spam", report)
        self.assertNotIn("UNVERIFIED", report)

    def test_dedup_and_community_label(self):
        row = item("Animated cat controller Roblox", "https://www.reddit.com/r/robloxgamedev/comments/abc123/title/")
        discussion = item("Where are the Roblox devs?", "https://www.reddit.com/r/robloxgamedev/comments/def123/title/")
        picks = m.shortlist([row, row, discussion])
        self.assertEqual(len(picks), 1)
        self.assertIn("video not confirmed", picks[0][1])

    def test_direct_video_ranks_above_community_post(self):
        rows = [
            item("Roblox game prototype", "https://www.reddit.com/r/robloxgamedev/comments/abc123/demo/"),
            item("Rapid Creation with Agentic Studio", "https://www.youtube.com/watch?v=1234"),
        ]
        self.assertEqual(m.shortlist(rows)[0][1], "YouTube video")


if __name__ == "__main__":
    unittest.main()
