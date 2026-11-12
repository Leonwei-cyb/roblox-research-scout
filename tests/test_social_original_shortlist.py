import unittest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from social_original_shortlist import url_kind, creator_handles, shortlist, render

class SocialSourcesTest(unittest.TestCase):
    def setUp(self):
        self.creators = [{"id":"a","label":"Artist","focus":"PC UI",
          "accounts":[{"platform":"x","url":"https://x.com/Artist"},
                      {"platform":"instagram","url":"https://www.instagram.com/artist/"}],
          "youtube_channel_id":"UC123"}]
    def test_exact_post_url_only(self):
        self.assertEqual(url_kind("https://x.com/Artist/status/123"), "x")
        self.assertEqual(url_kind("https://www.instagram.com/reel/ABC123/"), "instagram")
        for url in ["https://x.com/Artist", "https://x.com/i/trending/123",
                    "https://news.google.com/redirect?url=x.com/Artist/status/123",
                    "https://x.com/Artist/status/notnumber", "http://x.com/Artist/status/123",
                    "https://notx.com/Artist/status/123"]:
            self.assertIsNone(url_kind(url))
    def test_exact_handle_not_fan_mention(self):
        rows = [{"url":"https://x.com/Artist/status/123","title":"Studio build"},
                {"url":"https://x.com/Other/status/456","title":"Artist makes amazing build"},
                {"url":"https://www.instagram.com/reel/CODE/","title":"Who made this?"}]
        result = shortlist(self.creators,rows)
        self.assertEqual([x["url"] for x in result[0][1]], ["https://x.com/Artist/status/123"])
    def test_crossposts_only_confirmed_channel(self):
        rows = [{"url":"https://www.youtube.com/watch?v=abcd","source":"youtube-UC123","title":"UI showcase"},
                {"url":"https://www.youtube.com/shorts/xyz","source":"youtube-OTHER","title":"Unrelated"}]
        result = shortlist(self.creators,rows)
        self.assertEqual(len(result[0][1]),0)
        self.assertEqual(len(result[0][2]),1)
        self.assertIn("NOT matched to social post",render(self.creators,rows))
    def test_dedup_and_spam(self):
        rows=[{"url":"https://x.com/Artist/status/123","title":"Build"},
              {"url":"https://x.com/Artist/status/123","title":"Build duplicate"},
              {"url":"https://x.com/Artist/status/456","title":"Free Robux giveaway"}]
        self.assertEqual(len(shortlist(self.creators,rows)[0][1]),1)
    def test_unverified_channel_not_conflated(self):
        c=[{**self.creators[0],"youtube_channel_id":None,
            "candidate_youtube_channel_id":"UC123"}]
        row=[{"url":"https://www.youtube.com/watch?v=abcd","source":"youtube-UC123","title":"Build"}]
        self.assertEqual(shortlist(c,row)[0][2],[])
if __name__ == "__main__":
    unittest.main()
