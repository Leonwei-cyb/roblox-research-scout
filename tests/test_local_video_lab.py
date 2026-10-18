import importlib.util
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

p=Path(__file__).resolve().parents[1]/"scripts/local_video_lab.py"
spec=importlib.util.spec_from_file_location("local_video_lab",p)
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

class LocalVideoTests(unittest.TestCase):
    def test_frame_schedule(self):
        self.assertEqual(m.timepoints(10,2),[2.5,7.5])
        with self.assertRaises(ValueError):
            m.timepoints(30,99)

    def test_no_cloud(self):
        with self.assertRaises(ValueError):
            m.image_review([],"","qwen3-vl:235b-cloud")
        with self.assertRaises(ValueError):
            m.image_review([],"","https://remote.example/v1")

    def test_caption_and_html(self):
        with tempfile.TemporaryDirectory() as d:
            file=Path(d)/"captions.srt"
            file.write_text("1\n00:00:01,200 --> 00:00:02,200\nCat earned coins\n")
            self.assertIn("Cat earned coins",m.caption_excerpt(file))
            page=m.build_gallery(Path("<bad>.mp4"),[(1.2,Path("frame_01.jpg"))],"<private>")
            self.assertIn("&lt;bad&gt;",page)
            self.assertIn("&lt;private&gt;",page)

    @unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"),"ffmpeg not installed")
    def test_synthetic_clip(self):
        with tempfile.TemporaryDirectory() as d:
            clip=Path(d)/"synthetic.mp4"
            subprocess.run(["ffmpeg","-nostdin","-loglevel","error","-f","lavfi",
                "-i","color=c=blue:s=128x72:d=2","-t","2","-c:v","mpeg4",
                "-y",str(clip)],timeout=15,check=True)
            m.run(clip,Path(d)/"out",2,None,None)
            self.assertTrue((Path(d)/"out/synthetic/gallery.html").is_file())
            self.assertTrue((Path(d)/"out/synthetic/frame_01.jpg").is_file())
