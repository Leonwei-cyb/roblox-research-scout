"""Offline tests: research reports follow the shared active-game authority."""
import json
import os
import re
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import learning_radar
import research_reporter as r

YT = "https://youtube.com/watch?v=ABCDEFGHIJK"
POST = {"key": "youtube:ABCDEFGHIJK", "url": YT, "kind": "youtube",
        "title": "Roblox UI HUD layout", "published": "2026-10-24", "source": "firsthand",
        "evidence": "UNVIEWED_METADATA", "score": 9, "signals": ["UI and menus"]}
CAT_WORDS = re.compile(r"Cat Magic|\bcats?\b|tuition|\bdesks?\b|classroom|FREE pad", re.I)


class ActiveGameRoutingTests(unittest.TestCase):
    def run_main(self, authority_text):
        """Run the real reporter main() against a temp watch dir and authority file."""
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        root = Path(td.name)
        (root / "watch").mkdir()
        (root / "watch" / "learning_index.json").write_text(json.dumps({"posts": [POST]}), encoding="utf-8")
        old = root / "watch" / "cat_magic_research_report.md"
        old.write_text("historical\n", encoding="utf-8")
        auth = root / "active_game.txt"
        if authority_text is not None:
            auth.write_text(authority_text, encoding="utf-8")
        env = {k: v for k, v in os.environ.items() if k != "LEON_ACTIVE_GAME"}
        env["LEON_ACTIVE_GAME_FILE"] = str(auth)
        with patch.dict(os.environ, env, clear=True), \
             patch.object(r, "INDEX", root / "watch" / "learning_index.json"), \
             patch.object(r, "OUTPUT", root / "watch"):
            r.main()
        return root / "watch"

    def test_hex_haven_authority_routes_to_colonists_not_cat_magic(self):
        out = self.run_main("hex-haven\n")
        self.assertEqual((out / "cat_magic_research_report.md").read_text(), "historical\n")
        self.assertFalse((out / "cat_magic_research_report.json").exists())
        current = json.loads((out / "current_game_research_report.json").read_text())
        self.assertEqual(current["active_game"], "Colonists")
        self.assertIn("Cat Magic", current["held_games_not_current"])
        self.assertEqual(current["candidates"][0]["stage"], "UNVIEWED_METADATA")
        self.assertTrue((out / "colonists_research_report.md").exists())
        md = (out / "current_game_research_report.md").read_text()
        self.assertIn("Colonists research intelligence", md)
        for p in current["candidates"]:
            self.assertNotRegex(p["question_for_reviewer"], CAT_WORDS)

    def test_missing_authority_suppresses_all_game_tasks(self):
        out = self.run_main(None)
        current = json.loads((out / "current_game_research_report.json").read_text())
        self.assertIsNone(current["active_game"])
        self.assertEqual(current["status"], "ACTIVE_GAME_UNKNOWN_NO_GAME_TASKS")
        self.assertEqual(current["candidates"], [])
        self.assertTrue(current["authority"].endswith("MISSING"))
        self.assertEqual(current["held_games_not_current"], [])
        self.assertNotIn("On hold", (out / "current_game_research_report.md").read_text())
        self.assertEqual(sorted(p.name for p in out.glob("*_research_report.*")),
                         ["cat_magic_research_report.md",
                          "current_game_research_report.json", "current_game_research_report.md"])

    def test_unrecognized_authority_is_not_guessed(self):
        out = self.run_main("one-tower\n")
        current = json.loads((out / "current_game_research_report.json").read_text())
        self.assertIsNone(current["active_game"])
        self.assertTrue(current["authority"].endswith("UNRECOGNIZED"))

    def test_cat_magic_authority_still_writes_its_report(self):
        out = self.run_main("cat-magic")
        cat = json.loads((out / "cat_magic_research_report.json").read_text())
        self.assertEqual(cat["schema"], "LEON_CAT_MAGIC_RESEARCH_REPORT_V1")
        self.assertIn("Colonists", cat["held_games_not_current"])

    def test_learning_queue_questions_follow_the_game(self):
        result = learning_radar.triage([{"url": YT, "title": "Roblox tycoon UI animation"}])
        colonists = learning_radar.render(result, "colonists")
        unknown = learning_radar.render(result, None)
        self.assertIn("Active game: **Colonists**", colonists)
        self.assertNotRegex(colonists, CAT_WORDS)
        self.assertIn("Active game: **UNKNOWN**", unknown)
        self.assertNotRegex(unknown, CAT_WORDS)
        self.assertIn("unviewed metadata", unknown.lower())


if __name__ == "__main__":
    unittest.main()
