import importlib.util
import unittest
from pathlib import Path
p = Path(__file__).resolve().parents[1] / "scripts/research_quality.py"
s = importlib.util.spec_from_file_location("research_quality", p)
m = importlib.util.module_from_spec(s)
s.loader.exec_module(m)

class QualityTests(unittest.TestCase):
    def test_does_not_infer_video_from_index(self):
        self.assertEqual(m.classify({"title":"Roblox UI clip","url":"https://news.google.com/rss/articles/abc"}),
                         "indexed redirect (not original)")
        self.assertEqual(m.classify({"title":"Roblox UI clip","url":"https://www.youtube.com/watch?v=xyz"}),
                         "original video/post URL (unwatched)")
        self.assertNotIn("original", m.classify({"title":"Roblox UI","url":"https://www.instagram.com/creator/"}))
    def test_guard_and_empty(self):
        self.assertIn("risky",m.classify({"title":"Download cracked Studio free","url":"https://youtu.be/xy"}))
        self.assertIn("0.0%",m.report([]))
        self.assertIn("unwatched",m.report([{"title":"UI","url":"https://youtu.be/xyz"}]))

if __name__ == "__main__":
    unittest.main()
