"""Offline tests: no network calls or creator images are downloaded."""
import json
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import official_visual_scout as scout

PAGE = "https://www.biggames.io/post/pet-simulator-99-update-61"
HOST = "https://bigblog-storage.s3.us-east-1.amazonaws.com/"


class OriginalVisualScoutTests(unittest.TestCase):
    def test_only_creator_hosted_image_links_are_accepted(self):
        self.assertTrue(scout.permitted_asset(HOST + "ps99_hotbar_123.png", PAGE))
        self.assertFalse(scout.permitted_asset("http://example.com/img.png", PAGE))
        self.assertFalse(scout.permitted_asset("https://evil.example/img.png", PAGE))
        self.assertFalse(scout.permitted_asset("https://bigblog-storage.s3.us-east-1.amazonaws.com.evil/img.png", PAGE))
        self.assertFalse(scout.permitted_asset("https://www.biggames.io/post/other", PAGE))
        self.assertFalse(scout.permitted_asset("https://user:pw@bigblog-storage.s3.us-east-1.amazonaws.com/a.gif", PAGE))

    def test_extract_img_anchor_and_lazy_srcset_without_duplicates(self):
        body = ('<img alt="Farm upgrades" src="' + HOST + 'ps99_upgrades.png">'
                '<a href="' + HOST + 'ps99_hotbar.gif">Hotbar</a>'
                '<img data-src="' + HOST + 'ps99_map.webp">'
                '<source srcset="' + HOST + 'ps99_upgrades.png 1x, ' + HOST + 'ps99_upgrades2.png 2x">'
                '<img src="https://untrusted.example.org/fake.png">')
        parser = scout.OriginalImages(PAGE)
        parser.feed(body)
        self.assertEqual(3, len(parser.images))
        self.assertEqual("Farm upgrades", parser.images[0]["label"])

    def test_keyword_filter_prioritizes_useful_ui_images(self):
        images = [{"name": name, "label": name, "url": HOST + name}
                  for name in ("ps99_hotbar.png", "ps99_gargantuan_egg.png", "ps99_upgrade_menu.png")]
        chosen = scout.select(images, ["hotbar", "upgrade"], limit=10)
        self.assertEqual(2, len(chosen))
        self.assertFalse(any("egg" in r["name"] for r in chosen))

    def test_report_always_labels_media_as_uninspected(self):
        item = {"url": HOST + "hotbar.png", "name": "hotbar.png", "label": "Hotbar"}
        page = {"publisher": "BIG Games", "url": PAGE}
        report = scout.render([(page, [item])], [])
        self.assertIn("pixels NOT inspected", report)
        self.assertIn("NOT video watched", report)

    def test_daily_cooldown_prevents_polling_every_ten_minutes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = root / "config.json"
            config.write_text(json.dumps({"pages": [{
                "id": "ps99", "publisher": "BIG Games", "url": PAGE,
                "keywords": ["upgrade"]}]}))
            state = root / "state.json"
            report = root / "result.md"
            body = '<img alt="Upgrades" src="' + HOST + 'ps99_upgrades.png">'
            with patch.object(scout, "CONFIG", config), patch.object(scout, "STATE", state), \
                 patch.object(scout, "REPORT", report), \
                 patch.object(scout, "fetch_page", return_value=body) as fetch:
                now = datetime(2026, 10, 18, 12, 0, tzinfo=timezone.utc)
                scout.run(now)
                scout.run(now)
                self.assertEqual(1, fetch.call_count)
            self.assertTrue(report.exists())
            self.assertIn("ps99_upgrades.png", report.read_text())


if __name__ == "__main__":
    unittest.main()
