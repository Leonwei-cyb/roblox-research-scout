"""Regression tests for local authorized-video intake reliability."""
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import local_batch_review
import local_video_lab


class VideoBatchReliabilityTests(unittest.TestCase):
    def test_replaced_clip_same_size_and_timestamp_is_not_skipped(self):
        with tempfile.TemporaryDirectory() as folder:
            clip = Path(folder) / "creator.mp4"
            clip.write_bytes(b"aaaa")
            old_signature = local_batch_review.signature(clip)
            old_mtime = clip.stat().st_mtime_ns
            clip.write_bytes(b"bbbb")
            import os
            os.utime(clip, ns=(old_mtime, old_mtime))
            self.assertNotEqual(old_signature, local_batch_review.signature(clip))
            self.assertEqual([clip], local_batch_review.pending(
                Path(folder), {clip.name: old_signature}))

    def test_distinct_clip_extensions_cannot_overwrite_galleries(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            out = root / "out"
            video_a = root / "cat.mp4"
            video_b = root / "cat.mov"
            for video in (video_a, video_b):
                video.write_bytes(b"fixture")
            def fake_capture(video, destination, frames):
                destination.mkdir(parents=True, exist_ok=True)
                image = destination / "frame_01.jpg"
                image.write_bytes(b"fixture")
                return [(1.0, image)]
            with patch.object(local_video_lab, "capture_frames", side_effect=fake_capture), \
                 patch.object(local_video_lab.shutil, "which", return_value="/usr/bin/ffmpeg"):
                local_video_lab.run(video_a, out, 1, None, None)
                local_video_lab.run(video_b, out, 1, None, None)
            galleries = sorted(out.glob("*/gallery.html"))
            self.assertEqual(2, len(galleries))
            self.assertNotEqual(galleries[0].parent, galleries[1].parent)


if __name__ == "__main__":
    unittest.main()
