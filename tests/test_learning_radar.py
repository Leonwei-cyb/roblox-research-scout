"""Offline tests: source provenance, one-post dedup and no fake viewing claims."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from learning_radar import identity, triage, render, FOCUS


class LearningRadarTests(unittest.TestCase):
    def test_youtube_alias_is_one_video(self):
        a = identity("https://youtu.be/KB5iAzy86Fo")
        b = identity("https://www.youtube.com/watch?v=KB5iAzy86Fo&utm_source=x")
        c = identity("https://youtube.com/shorts/KB5iAzy86Fo")
        self.assertEqual(a, b)
        self.assertEqual(b, c)

    def test_social_posts_are_not_creator_profiles(self):
        self.assertEqual(identity("https://x.com/Artist/status/123")[0], "x:123")
        self.assertEqual(identity("https://twitter.com/Other/status/123")[0], "x:123")
        self.assertEqual(identity("https://instagram.com/reel/ABC_123")[0], "instagram:ABC_123")
        self.assertEqual(identity("https://tiktok.com/@creator/video/123")[0], "tiktok:123")
        self.assertNotEqual(identity("https://instagram.com/creator")[0],
                            identity("https://instagram.com/other")[0])

    def test_forbid_insecure_and_embedded_credentials(self):
        self.assertEqual(identity("http://x.com/Artist/status/123"), (None, None))
        self.assertEqual(identity("https://a:b@x.com/Artist/status/123"), (None, None))
        self.assertEqual(identity("https://"), (None, None))

    def test_devforum_separate_posts_preserved(self):
        self.assertNotEqual(identity("https://devforum.roblox.com/t/a/4930000/2")[0],
                            identity("https://devforum.roblox.com/t/a/4930000/3")[0])

    def test_all_captured_and_deduplicated(self):
        items = [
            {"url": "https://youtu.be/KB5iAzy86Fo", "title": "Tycoon purchase pad"},
            {"url": "https://www.youtube.com/watch?v=KB5iAzy86Fo", "title": "Tycoon purchase pad"},
            {"url": "https://devforum.roblox.com/t/a/4930000/1",
             "title": "Why players leave my game", "excerpt": "mobile onboarding"},
            {"url": "https://news.google.com/rss/articles/abc", "title": "Game UI news"},
            {"url": "http://unsafe.example", "title": "Untested"},
        ]
        result = triage(items)
        self.assertEqual(result["records_read"], 5)
        self.assertEqual(result["unique_posts"], 3)
        self.assertEqual(result["reviewed_posts"], 0)
        self.assertTrue(all(p["evidence"] == "UNVIEWED_METADATA" for p in result["posts"]))
        self.assertEqual(sum(p["kind"] == "youtube" for p in result["posts"]), 1)

    def test_index_only_never_promoted(self):
        result = triage([{"url": "https://news.google.com/rss/articles/abc",
                          "title": "Roblox tycoon UI tutorial"}])
        self.assertEqual(result["posts"][0]["score"], 0)
        self.assertNotIn("](https://news.google.com", render(result))

    def test_proposed_test_does_not_claim_video_watched(self):
        result = triage([{"url": "https://www.youtube.com/watch?v=KB5iAzy86Fo",
                          "title": "Roblox tycoon animation"}])
        body = render(result)
        self.assertIn("unviewed metadata", body.lower())
        self.assertIn("No videos watched", body)
        self.assertIn("0.5-1 second", body)

    def test_signal_focus_is_broad_but_game_first(self):
        self.assertIn("first-session and mobile", FOCUS)
        self.assertIn("physical tycoon purchases", FOCUS)
        self.assertIn("cat animation and audio", FOCUS)

    def test_render_deterministic_independent_of_ingestion_order(self):
        items = [{"url": "https://devforum.roblox.com/t/a/1", "title": "mobile tutorial"},
                 {"url": "https://devforum.roblox.com/t/b/2", "title": "cat animation"}]
        self.assertEqual(render(triage(items)), render(triage(list(reversed(items)))))


if __name__ == "__main__":
    unittest.main()
