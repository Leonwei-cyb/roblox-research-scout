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

    def test_runner_uses_failure_aware_cursor_helper(self):
        source = (ROOT / "scripts" / "discovery_scout.py").read_text(encoding="utf-8")
        self.assertIn("research_lanes.advance_cursors(", source)
        self.assertNotIn('old_offset + lane["completed"]', source)

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

    def test_cat_magic_candidate_has_real_project_fit(self):
        from datetime import datetime, timezone
        facts = {"repo": "example/roblox-tycoon", "description": "Roblox tycoon purchase pad system",
                 "topics": [], "readme_excerpt": "Roblox Luau classroom tycoon upgrades",
                 "license": "MIT", "last_commit": "2026-10-20T00:00:00Z",
                 "security_policy": True, "has_tests": True, "has_ci": True,
                 "sha": "a" * 40, "id": 42, "url": "https://github.com/example/roblox-tycoon"}
        rec = ds.build_record(facts, self.cfg,
                              datetime(2026, 10, 20, tzinfo=timezone.utc),
                              None, None, "cat-magic-gameplay")
        self.assertEqual(rec["project"], "Cat Magic School")
        self.assertEqual(rec["verdict"], "needs-test")
        self.assertEqual(rec["suggested_owner"], "hub")

    def test_tower_query_never_routes_to_cat_magic_by_keyword_collision(self):
        from datetime import datetime, timezone
        facts = {"repo": "example/tower-tycoon", "description": "Roblox tower tycoon purchase pads",
                 "topics": [], "readme_excerpt": "Roblox Luau tycoon upgrades and waves",
                 "license": "MIT", "last_commit": "2026-10-20T00:00:00Z",
                 "security_policy": True, "has_tests": True, "has_ci": True,
                 "sha": "c" * 40, "id": 44, "url": "https://github.com/example/tower-tycoon"}
        rec = ds.build_record(facts, self.cfg,
                              datetime(2026, 10, 20, tzinfo=timezone.utc),
                              None, None, "one-tower-gameplay")
        self.assertEqual(rec["project"], "One Tower Tycoon")
        self.assertNotIn("cat-magic-tycoon", [x["id"] for x in rec["blockers"]])

    def test_unrelated_agent_candidate_is_not_cat_magic(self):
        from datetime import datetime, timezone
        facts = {"repo": "example/agent-dashboard", "description": "Live agent monitoring dashboard",
                 "topics": [], "readme_excerpt": "Agent status dashboard",
                 "license": "MIT", "last_commit": "2026-10-20T00:00:00Z",
                 "security_policy": True, "has_tests": True, "has_ci": True,
                 "sha": "b" * 40, "id": 43, "url": "https://github.com/example/agent-dashboard"}
        rec = ds.build_record(facts, self.cfg,
                              datetime(2026, 10, 20, tzinfo=timezone.utc),
                              None, None, "leon-systems")
        self.assertNotEqual(rec["project"], "Cat Magic School")

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
