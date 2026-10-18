import importlib.util
import tempfile
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location("dispatcher", Path(__file__).resolve().parents[1] / "scripts/research_dispatcher.py")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

def row(title, url, source="youtube-X"):
    return {"title": title, "url": url, "source": source, "excerpt": "", "published": "2026-10-18"}

class BotTests(unittest.TestCase):
    def test_real_media_not_search_redirect(self):
        self.assertTrue(m.media_url("https://www.youtube.com/watch?v=ABC123"))
        self.assertTrue(m.media_url("https://www.instagram.com/reel/ABC123/"))
        self.assertTrue(m.media_url("https://www.tiktok.com/@test/video/12345678"))
        self.assertFalse(m.media_url("https://news.google.com/rss/articles/ABCD"))
        self.assertFalse(m.media_url("https://www.instagram.com/name/"))

    def test_filters_ads_and_prefers_media(self):
        rows=[row("Roblox UI animation demo", "https://www.youtube.com/watch?v=123"),
              row("Roblox UI animation demo", "https://news.google.com/rss/articles/123"),
              row("free robux join discord", "https://www.youtube.com/watch?v=spam"),
              row("Roblox prank giveaway", "https://www.youtube.com/watch?v=bait")]
        ui=m.choose(rows)["UI / menus / effects"]
        self.assertEqual(ui[0][1]["url"], "https://www.youtube.com/watch?v=123")
        self.assertFalse(any("spam" in x[1]["url"] for x in ui))

    def test_coverage_and_timing(self):
        rows=[row("Roblox gameplay", "https://www.youtube.com/watch?v=123"), row("Roblox UI", "https://news.google.com/rss/articles/abc")]
        report=m.coverage_audit(rows, "- reddit: HTTP 429")
        self.assertIn("| Original media URLs | 1 |", report)
        self.assertIn("| Indexed redirects, original unknown | 1 |", report)
        self.assertIn("HTTP 429", report)
        self.assertIn("NOT Roblox CCU", m.topic_signals(rows))

    def test_idempotent(self):
        with tempfile.TemporaryDirectory() as td:
            target=Path(td)/"test.md"
            self.assertTrue(m.save(target, "ok"))
            self.assertFalse(m.save(target, "ok"))
            self.assertTrue(m.save(target, "changed"))
if __name__=="__main__":
    unittest.main()
