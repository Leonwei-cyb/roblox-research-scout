"""Offline tests for the source-linked Cat Magic analyst and reporter."""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import research_reporter as r

YT = "https://youtube.com/watch?v=ABCDEFGHIJK"
DF = "https://devforum.roblox.com/t/a/4946218"


def row(key, url, kind, topic, *, score=9, source="firsthand", title="Roblox tycoon lesson"):
    return {"key": key, "url": url, "kind": kind, "title": title, "published": "2026-10-20",
            "source": source, "evidence": "UNVIEWED_METADATA", "score": score,
            "signals": [topic]}


class ResearchReporterTests(unittest.TestCase):
    def test_original_and_relevance(self):
        d = {"posts": [row("youtube:ABCDEFGHIJK", YT, "youtube", "physical tycoon purchases")]}
        out = r.analyze(d)
        self.assertEqual(out["status"], "TRIAGE_ONLY_NOT_GAMEPLAY_ANALYSIS")
        self.assertEqual(out["inspected_videos"], 0)
        self.assertEqual(out["observed_gameplay_findings"], 0)
        self.assertEqual(len(out["candidates"]), 1)
        self.assertEqual(out["candidates"][0]["question_for_reviewer"], r.LANES[1][2])
        self.assertFalse(out["new_code_changes_authorized"])

    def test_blocks_index_redirect_and_spoofed_evidence(self):
        entries = [
            row("index-only:news", "https://news.google.com/rss/articles/xyz", "index-only", "UI and menus"),
            row("youtube:ABCDEFGHIJK", YT, "youtube", "UI and menus", title="Studio footage"),
        ]
        entries[-1]["evidence"] = "VERIFIED"
        out = r.analyze({"posts": entries})
        self.assertEqual(out["candidates"], [])
        self.assertIn("UI and menus", out["unfilled_topics"])

    def test_refuses_embedded_credentials_and_arbitrary_hosts(self):
        for url in [
            "https://evil.example/watch?v=ABCDEFGHIJK",
            "https://token@youtube.com/watch?v=ABCDEFGHIJK",
            "https://youtube.com/watch?v=ABCDEFGHIJK) [click](https://evil.example",
            "http://youtube.com/watch?v=ABCDEFGHIJK",
        ]:
            self.assertFalse(r.valid_source(row("youtube:ABCDEFGHIJK", url, "youtube", "UI and menus")))

    def test_source_identity_required(self):
        self.assertFalse(r.valid_source(row("youtube:DIFFERENT", YT, "youtube", "UI and menus")))

    def test_deterministic_rank_and_dedup(self):
        one = row("youtube:ABCDEFGHIJK", YT, "youtube", "first-session and mobile", score=17, title="Mobile tycoon onboarding")
        one["signals"].append("physical tycoon purchases")
        two = row("devforum:4946218:1", DF, "devforum", "physical tycoon purchases", score=10)
        a = r.analyze({"posts": [two, one]})
        b = r.analyze({"posts": [one, two]})
        self.assertEqual(a, b)
        self.assertEqual(len(a["candidates"]), 2)
        self.assertEqual(a["candidates"][0]["key"], "youtube:ABCDEFGHIJK")
        self.assertEqual(a["candidates"][1]["key"], "devforum:4946218:1")

    def test_spam_rejected_and_hard_limit(self):
        a = row("youtube:ABCDEFGHIJK", YT, "youtube", "physical tycoon purchases",
                title="FREE ROBUX giveaway")
        self.assertEqual(r.analyze({"posts": [a]})["candidates"], [])
        with self.assertRaises(ValueError):
            r.analyze({"posts": [a] * 10001})
        with self.assertRaises(ValueError):
            r.analyze({"posts": []}, limit=99)
        with self.assertRaises(ValueError):
            r.analyze({"posts": "invalid"})

    def test_report_is_not_false_watched_claim(self):
        d = r.analyze({"posts": [row("youtube:ABCDEFGHIJK", YT, "youtube",
                                     "physical tycoon purchases")]})
        md = r.render(d)
        self.assertIn("No video watched", md)
        self.assertIn("UNVIEWED_METADATA", md)
        self.assertIn("Inspected videos: **0**", md)

    def test_markdown_sanitized(self):
        p = row("devforum:4946218:1", DF, "devforum", "UI and menus",
                title="Roblox UI Hi [skip](https://evil.example) <tag>")
        out = r.render(r.analyze({"posts": [p]}))
        self.assertNotIn("[skip](https://evil.example)", out)
        self.assertIn(r"\[skip\]", out)
        self.assertIn(r"\<tag\>", out)

    def test_excerpt_only_keywords_do_not_masquerade_as_game_research(self):
        leads = [
            row("youtube:ABCDEFGHIJK", YT, "youtube", "first-session and mobile",
                title="Server Animation Memory leaks continuously"),
            row("devforum:4946218:1", DF, "devforum", "tuition and economy",
                title="Makeup Now Available for In-Experience Creation"),
        ]
        self.assertEqual(r.analyze({"posts": leads})["candidates"], [])

    def test_excerpt_stuffing_cannot_out_rank_stronger_title(self):
        clear = row("youtube:ABCDEFGHIJK", YT, "youtube", "UI and menus",
                    score=8, title="Roblox UI HUD")
        stuffed = row("youtube:ZZZZZZZZZZZ",
                      "https://www.youtube.com/watch?v=ZZZZZZZZZZZ",
                      "youtube", "UI and menus", score=100,
                      title="Roblox UI")
        chosen = r.analyze({"posts": [stuffed, clear]})["candidates"]
        self.assertEqual(len(chosen), 1)
        self.assertEqual(chosen[0]["key"], "youtube:ABCDEFGHIJK")

    def test_real_saved_feed_index_stays_bounded_and_title_grounded(self):
        import re
        import learning_radar
        source = Path(__file__).resolve().parents[1] / "watch" / "media_state.json"
        raw = json.loads(source.read_text(encoding="utf-8"))
        index = learning_radar.triage(raw["items"])
        report = r.analyze(index)
        self.assertLessEqual(len(report["candidates"]), 6)
        self.assertEqual(report["observed_gameplay_findings"], 0)
        self.assertEqual(len({x["key"] for x in report["candidates"]}),
                         len(report["candidates"]))
        for item in report["candidates"]:
            self.assertRegex(item["title"], re.compile(
                learning_radar.FOCUS[item["topic"]][0], re.I))
            self.assertEqual(item["stage"], "UNVIEWED_METADATA")

    def test_idempotent_write(self):
        with tempfile.TemporaryDirectory() as t:
            dest = Path(t) / "report.md"
            self.assertTrue(r.save(dest, "one"))
            self.assertFalse(r.save(dest, "one"))
            self.assertTrue(r.save(dest, "two"))

    def test_main_writes_both_reports_offline(self):
        data = {"posts": [row("youtube:ABCDEFGHIJK", YT, "youtube", "physical tycoon purchases")]}
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "watch").mkdir()
            (root / "watch" / "learning_index.json").write_text(json.dumps(data), encoding="utf-8")
            with patch.object(r, "INDEX", root / "watch" / "learning_index.json"), \
                 patch.object(r, "OUTPUT", root / "watch"):
                r.main()
            out = json.loads((root / "watch" / "cat_magic_research_report.json").read_text())
            self.assertEqual(out["candidates"][0]["key"], "youtube:ABCDEFGHIJK")
            self.assertIn("UNVIEWED_METADATA",
                          (root / "watch" / "cat_magic_research_report.md").read_text())


if __name__ == "__main__":
    unittest.main()
