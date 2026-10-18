"""Tests for public multi-source research without contacting any website or model."""
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "media_scout.py"
spec = importlib.util.spec_from_file_location("media_scout", MODULE_PATH)
monitor = importlib.util.module_from_spec(spec)
spec.loader.exec_module(monitor)

ATOM = b"""<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <title>Claude Code v2.2.0 release</title>
    <id>urn:claude:2.2.0</id>
    <link rel="alternate" type="text/html" href="https://github.com/anthropics/claude-code/releases/tag/v2.2.0"/>
    <updated>2026-10-17T16:20:00Z</updated>
    <content>Fixed the Roblox Studio connection for Macs.</content>
  </entry>
</feed>"""

RSS = b"""<?xml version="1.0"?>
<rss version="2.0"><channel><title>DevForum</title>
<item><title>Roblox Studio UI testing update</title>
<link>https://devforum.roblox.com/t/123?utm_source=feed</link>
<description><![CDATA[<p>Use native tools instead of clicks.</p>]]></description>
<pubDate>Sun, 18 Oct 2026 12:30:00 GMT</pubDate></item>
</channel></rss>"""


def source(identifier="x"):
    return {"id": identifier, "label": "A feed", "category": "roblox_updates"}


class FeedParsingTests(unittest.TestCase):
    def test_atom_metadata(self):
        rows = monitor.parse_feed(ATOM, source("claude"), limit=3)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["published"], "2026-10-17")
        self.assertIn("Claude Code", rows[0]["title"])
        self.assertIn("Roblox Studio", rows[0]["excerpt"])
        self.assertEqual(rows[0]["category"], "roblox_updates")

    def test_same_title_with_distinct_original_urls_is_not_collapsed(self):
        first = monitor.parse_feed(RSS, source("forum"))
        second = monitor.parse_feed(RSS.replace(b"/t/123?", b"/t/987?"), source("forum"))
        self.assertEqual(first[0]["title"], second[0]["title"])
        self.assertNotEqual(first[0]["id"], second[0]["id"])

    def test_rss_description_and_tracking_parameters(self):
        rows = monitor.parse_feed(RSS, source("forum"))
        self.assertEqual(rows[0]["url"], "https://devforum.roblox.com/t/123")
        self.assertEqual(rows[0]["published"], "2026-10-18")
        self.assertEqual(rows[0]["excerpt"], "Use native tools instead of clicks.")

    def test_apple_game_subset_is_not_all_app_rankings(self):
        payload = json.dumps({"feed": {"results": [
            {"name": "A Banking App", "url": "https://apps.apple.com/app/id111",
             "genres": [{"genreId": "6000", "name": "Business"}], "artistName": "Bank"},
            {"name": "A Game", "url": "https://apps.apple.com/app/id222",
             "genres": [{"genreId": "6014", "name": "Games"}], "artistName": "Creator"}
        ]}}).encode("utf-8")
        rows = monitor.parse_apple_chart(payload, source("apple"))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["title"], "A Game")
        self.assertIn("position 2", rows[0]["excerpt"])
        self.assertIn("not the full games-only chart", rows[0]["excerpt"])

    def test_restrict_hosts(self):
        with self.assertRaises(ValueError):
            monitor.fetch_url("http://example.com/bad")
        with self.assertRaises(ValueError):
            monitor.fetch_url("https://example.com/bad")

    def test_valid_youtube_channel(self):
        feeds = list(monitor.feed_sources({"youtube_channels": [
            {"channel_id": "UCjiPEaapiHbJMoAdi_L8fNA", "label": "Roblox"}
        ]}))
        self.assertIn("channel_id=UCjiPEaapiHbJMoAdi_L8fNA", feeds[0]["url"])
        with self.assertRaises(ValueError):
            list(monitor.feed_sources({"youtube_channels": [{"channel_id": "@Roblox"}]}))

    def test_reject_html_in_markdown(self):
        r = monitor.markdown("<b>Release</b> [v2] | new" + chr(96) + "code")
        self.assertNotIn("<b>", r)
        self.assertIn("\\[v2\\]", r)
        self.assertIn("\\|", r)
        self.assertNotIn(chr(96), r)


class ScanTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.root = Path(self.folder.name)
        (self.root / "watch").mkdir()
        (self.root / "watch" / "feeds.json").write_text(json.dumps({
            "feeds": [
                {"id": "good", "label": "Claude", "category": "claude_updates", "url": "https://raw.githubusercontent.com/test.xml"},
                {"id": "blocked", "label": "Reddit", "category": "community", "url": "https://www.reddit.com/some.rss"}
            ],
            "limits": {"per_source": 10, "max_new_report": 8}
        }))
        self.ctx = [
            patch.object(monitor, "CONFIG", self.root / "watch" / "feeds.json"),
            patch.object(monitor, "STATE", self.root / "watch" / "media_state.json"),
            patch.object(monitor, "BRIEF", self.root / "watch" / "media_brief.md"),
            patch.object(monitor, "HEALTH", self.root / "watch" / "source_health.md"),
            patch.object(monitor, "COOLDOWNS", self.root / "watch" / "media_cooldowns.json")
        ]
        for p in self.ctx:
            p.start()
            self.addCleanup(p.stop)

    def fake_fetch(self, url, timeout=12):
        if "reddit.com" in url:
            raise RuntimeError("HTTP 403")
        return ATOM

    def test_same_url_with_changed_title_retains_legacy_seen_id(self):
        with patch.object(monitor, "fetch_url", return_value=ATOM):
            monitor.run()
        existing = json.loads(monitor.STATE.read_text())
        # Simulate the prior title-hash ID format already deployed.
        legacy_id = "legacy-title-only-digest"
        existing["items"][0]["id"] = legacy_id
        existing["seen"] = [legacy_id]
        monitor.STATE.write_text(json.dumps(existing))
        changed = ATOM.replace(b"Claude Code v2.2.0 release", b"Updated Claude Code changes")
        with patch.object(monitor, "fetch_url", return_value=changed):
            monitor.run()
        result = json.loads(monitor.STATE.read_text())
        self.assertIn(legacy_id, result["seen"])
        self.assertNotIn("Updated Claude Code changes", monitor.BRIEF.read_text())

    def test_baseline_and_no_duplicate_changes(self):
        with patch.object(monitor, "fetch_url", side_effect=self.fake_fetch):
            monitor.run()
            report = monitor.BRIEF.read_text()
            self.assertIn("Claude Code", report)
            health = monitor.HEALTH.read_text()
            self.assertIn("blocked", health)
            self.assertIn("HTTP 403", health)
            monitor.run()
            self.assertEqual(monitor.BRIEF.read_text(), report)
            self.assertEqual(monitor.HEALTH.read_text(), health)

    def test_new_entry_detected(self):
        with patch.object(monitor, "fetch_url", return_value=ATOM):
            monitor.run()
        later = ATOM.replace(b"v2.2.0 release", b"v2.2.1 release").replace(
            b"/tag/v2.2.0", b"/tag/v2.2.1")
        with patch.object(monitor, "fetch_url", return_value=later):
            monitor.run()
        self.assertIn("v2.2.1", monitor.BRIEF.read_text())

    def test_migrated_state_removes_duplicate_saved_urls(self):
        with patch.object(monitor, "fetch_url", return_value=ATOM):
            monitor.run()
            old=json.loads(monitor.STATE.read_text())
            extra=dict(old["items"][0])
            extra["id"]="stale-duplicate-title-id"
            old["items"].append(extra)
            old["seen"].append(extra["id"])
            monitor.STATE.write_text(json.dumps(old))
            monitor.run()
        refreshed=json.loads(monitor.STATE.read_text())
        urls=[r["url"] for r in refreshed["items"]]
        self.assertEqual(len(urls),len(set(urls)))

    def test_rate_limited_feed_is_not_immediately_retried(self):
        def fetch(url, timeout=12):
            if "reddit.com" in url:
                raise RuntimeError("HTTP 429")
            return ATOM
        with patch.object(monitor, "fetch_url", side_effect=fetch) as fake:
            monitor.run()
            self.assertEqual(fake.call_count, 2)
            monitor.run()
            self.assertEqual(fake.call_count, 3)
        self.assertIn("Deferred feeds", monitor.HEALTH.read_text())
        self.assertIn("blocked", monitor.HEALTH.read_text())

    def test_cooldown_policy_expires_and_does_not_bypass_403(self):
        now = monitor.datetime(2026, 10, 18, tzinfo=monitor.timezone.utc)
        until = monitor.retry_after("HTTP 429", now)
        self.assertTrue(monitor.not_yet_due({"until": until}, now))
        self.assertFalse(monitor.not_yet_due({"until": until}, now + monitor.timedelta(hours=13)))
        self.assertIsNone(monitor.retry_after("HTTP 403", now))

    def test_total_failure_preserves_old_report(self):
        with patch.object(monitor, "fetch_url", return_value=ATOM):
            monitor.run()
        report = monitor.BRIEF.read_text()
        with patch.object(monitor, "fetch_url", side_effect=RuntimeError("HTTP 429")):
            with self.assertRaises(RuntimeError):
                monitor.run()
        self.assertEqual(report, monitor.BRIEF.read_text())


if __name__ == "__main__":
    unittest.main()
