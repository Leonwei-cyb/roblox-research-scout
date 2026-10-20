"""Regression tests for the source-quality redirect/canonical defects (offline).

Defect 1: watch/source_quality.md counted items from PAUSED feeds as current
coverage. On 2026-10-19, 157 of the 221 indexed redirects came from seven feeds
no longer configured, so the 8.5% direct-original share hid the 13.7% share of
the active feed set.
Defect 2: Google News RSS items carry <source url="..."> naming the publisher
(Instagram, YouTube, a blog), but parse_feed dropped it, so a redirect could not
even be routed to the right place for primary-source verification.
"""
import importlib.util
import sys
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"


def load(name):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


quality = load("research_quality")
media = load("media_scout")

GN_RSS = b"""<?xml version="1.0"?>
<rss version="2.0"><channel><title>q</title>
<item><title>Owner of Steal an Egg - Instagram</title>
<link>https://news.google.com/rss/articles/CBMiVkFVX3lxTE9SQW42?oc=5</link>
<pubDate>Tue, 14 Oct 2026 10:00:00 GMT</pubDate>
<description>&lt;a href="https://news.google.com/rss/articles/CBMiVkFVX3lxTE9SQW42?oc=5"&gt;Owner&lt;/a&gt;</description>
<source url="https://www.instagram.com">Instagram</source></item>
</channel></rss>"""


class SourceQualityCanonicalTests(unittest.TestCase):
    def rows(self):
        return [
            {"source": "paused-index", "title": "a", "url": "https://news.google.com/rss/articles/1"},
            {"source": "paused-index", "title": "b", "url": "https://news.google.com/rss/articles/2"},
            {"source": "paused-index", "title": "c", "url": "https://news.google.com/rss/articles/3"},
            {"source": "youtube-live", "title": "d", "url": "https://www.youtube.com/watch?v=abc"},
            {"source": "devforum", "title": "e", "url": "https://devforum.roblox.com/t/x/1"},
        ]

    def test_report_separates_active_from_paused_sources(self):
        text = quality.report(self.rows(), active_sources={"youtube-live", "devforum"})
        self.assertIn("Active configured sources", text)
        # Whole store: 1 of 5 direct = 20.0%; active set: 1 of 2 = 50.0%.
        self.assertIn("**20.0%**", text)
        self.assertIn("Active-source direct-original share: **50.0%**", text)
        self.assertIn("Entries from paused/unconfigured sources: **3**", text)
        self.assertIn("paused-index", text)

    def test_active_source_ids_follow_feed_config(self):
        cfg = {"feeds": [{"id": "devforum", "category": "c", "label": "l", "url": "https://devforum.roblox.com/latest.rss"}],
               "news_queries": [{"id": "gn-q", "category": "c", "query": "roblox"}],
               "youtube_channels": [{"channel_id": "UC" + "a" * 22, "label": "x"}]}
        self.assertEqual(quality.active_source_ids(cfg), {"devforum", "gn-q", "youtube-UC" + "a" * 22})

    def test_google_news_publisher_is_kept(self):
        source = {"id": "gn", "label": "Google News indexed: q", "category": "c"}
        records = media.parse_feed(GN_RSS, source)
        self.assertEqual(records[0]["publisher"], "https://www.instagram.com")
        self.assertEqual(quality.classify(records[0]), "indexed redirect (not original)")

    def test_redirects_grouped_by_publisher(self):
        rows = [{"source": "s", "title": "t", "url": "https://news.google.com/rss/articles/1", "publisher": "https://www.instagram.com"},
                {"source": "s", "title": "Something - YouTube", "url": "https://news.google.com/rss/articles/2"}]
        text = quality.report(rows, active_sources={"s"})
        self.assertIn("| www.instagram.com | 1 |", text)
        # Legacy rows without the field fall back to the ' - Publisher' title suffix.
        self.assertIn("| YouTube (title suffix) | 1 |", text)

    def test_existing_contract_unchanged(self):
        self.assertIn("0.0%", quality.report([]))


if __name__ == "__main__":
    unittest.main()
