"""Offline integration checks for game-specific discovery configuration and ranking."""
import ast
import json
import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import discovery_scout as ds  # noqa: E402
from research_lanes import plan_queries  # noqa: E402


class SpecialistIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.cfg = json.loads((ROOT / "watch" / "discovery.json").read_text(encoding="utf-8"))

    def test_existing_discovery_source_still_parses(self):
        ast.parse((ROOT / "scripts" / "discovery_scout.py").read_text(encoding="utf-8"))

    def test_all_topics_belong_to_a_specialist(self):
        available = {t["id"] for t in self.cfg["topics"]}
        assigned = {t for lane in self.cfg["research_lanes"] for t in lane["topics"]}
        self.assertEqual(available, assigned)
        self.assertEqual(len({lane["id"] for lane in self.cfg["research_lanes"]}),
                         len(self.cfg["research_lanes"]))
        self.assertIn("Cat Magic School", self.cfg["active_projects"])

    def test_one_shared_budget_covers_every_active_specialist(self):
        budget = self.cfg["limits"]["max_search_queries"]
        queries, status, _ = plan_queries(self.cfg, {}, budget)
        self.assertLessEqual(len(queries), budget)
        self.assertEqual(len({q for _, q, _ in queries}), len(queries))
        self.assertEqual({s["id"] for s in status if s["active"]},
                         {lid for _, _, lid in queries})
        count = {s["id"]: s["planned"] for s in status}
        self.assertGreater(count["cat-magic"], count["ai-tools"])

    def test_active_game_backlog_precedes_unrelated_high_score(self):
        rows = [{"repo": "safe/tools", "repo_id": 1, "version": "head",
                 "task": "inspect", "verdict": "needs-test", "scores": {"total": 100}},
                {"repo": "safe/tycoon", "repo_id": 2, "version": "head",
                 "task": "inspect", "verdict": "needs-test", "scores": {"total": 72},
                 "project": "Cat Magic School"}]
        self.assertEqual(ds.backlog(rows, 2, ["Cat Magic School"])[0]["repo"], "safe/tycoon")
        self.assertEqual(ds.backlog(rows, 2)[0]["repo"], "safe/tools")


if __name__ == "__main__":
    unittest.main()
