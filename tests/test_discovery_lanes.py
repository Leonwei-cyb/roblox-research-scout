"""Run locally: python3 -m unittest -v test_research_lanes.py (no network)."""
import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from research_lanes import plan_queries, prioritize_hits


def example():
    return {
        "topics": [{"id": "cat", "queries": ["cat-a", "cat-b", "cat-c", "cat-d"]},
                   {"id": "tower", "queries": ["tower-a", "tower-b", "tower-c"]},
                   {"id": "anime", "queries": ["anime-a", "anime-b", "anime-c"]},
                   {"id": "tools", "queries": ["tools-a", "tools-b", "tools-c"]}],
        "research_lanes": [{"id": "cat-magic", "topics": ["cat"], "weight": 6},
                           {"id": "tower", "topics": ["tower"], "weight": 2},
                           {"id": "anime", "topics": ["anime"], "weight": 2},
                           {"id": "tools", "topics": ["tools"], "weight": 1}],
    }


class ResearchLanesTests(unittest.TestCase):
    def test_respects_shared_budget_and_prevents_duplicate_searches(self):
        cfg = example()
        picked, status, _ = plan_queries(cfg, {}, 6)
        self.assertEqual(len(picked), 6)
        self.assertEqual(len({q for _, q, _ in picked}), 6)
        self.assertEqual(sum(s["planned"] for s in status), 6)

    def test_cat_magic_wins_more_slots_initially(self):
        picked, _, _ = plan_queries(example(), {}, 7)
        counts = {lid: sum(x[2] == lid for x in picked) for lid in ("cat-magic", "tower", "anime", "tools")}
        self.assertGreater(counts["cat-magic"], counts["tools"])

    def test_priority_change_requires_configuration_only(self):
        cfg = example()
        before = plan_queries(cfg, {}, 6)[0]
        cfg["research_lanes"][0]["weight"] = 1
        cfg["research_lanes"][2]["weight"] = 12
        after = plan_queries(cfg, {}, 6)[0]
        self.assertGreater(sum(x[2] == "anime" for x in after), sum(x[2] == "anime" for x in before))

    def test_query_rotation_after_successful_run(self):
        cfg = example()
        first, _, cursor = plan_queries(cfg, {}, 4)
        second, _, _ = plan_queries(cfg, {"research_lane_cursor": cursor}, 4)
        self.assertNotEqual(first, second)

    def test_every_lane_gets_a_slot_when_budget_allows(self):
        picked, _, _ = plan_queries(example(), {}, 4)
        self.assertEqual({x[2] for x in picked}, {"cat-magic", "tower", "anime", "tools"})

    def test_small_budget_rotates_between_lanes(self):
        cfg = example()
        seen = set()
        for run in range(4):
            picked, _, _ = plan_queries(cfg, {"research_lane_run": run}, 1)
            seen.update(x[2] for x in picked)
        self.assertEqual(seen, {"cat-magic", "tower", "anime", "tools"})

    def test_disabled_lane_does_not_run(self):
        cfg = example()
        cfg["research_lanes"][1]["enabled"] = False
        picked, summary, _ = plan_queries(cfg, {}, 9)
        self.assertNotIn("tower", [l for _, _, l in picked])
        self.assertFalse(summary[1]["active"])

    def test_shared_query_only_searched_once(self):
        cfg = example()
        cfg["research_lanes"][1]["topics"].append("cat")
        picked, _, _ = plan_queries(cfg, {}, 14)
        self.assertEqual(len({q for _, q, _ in picked}), len(picked))
        self.assertLessEqual(len(picked), 13)

    def test_legacy_configuration_stays_compatible(self):
        cfg = example()
        del cfg["research_lanes"]
        picked, status, cursor = plan_queries(cfg, {}, 2)
        self.assertEqual(picked, [("cat", "cat-a", "general"), ("cat", "cat-b", "general")])
        self.assertEqual(status[0]["planned"], 2)
        self.assertEqual(cursor, {})

    def test_bad_state_and_zero_budget_are_safe(self):
        picked, _, cursor = plan_queries(example(), {"research_lane_cursor": {"cat-magic": "bad"}}, 0)
        self.assertEqual(picked, [])
        self.assertIn("cat-magic", cursor)

    def test_game_hits_survive_very_popular_agent_repositories(self):
        cfg = {"research_lanes": [{"id": "cat", "weight": 12}, {"id": "agent", "weight": 1},
                                  {"id": "art", "weight": 4}]}
        hits = [(f"game/{i}", "cat", {"stars": 10 + i}) for i in range(30)]
        hits += [(f"agent/{i}", "agent", {"stars": 1000 + i}) for i in range(30)]
        hits += [(f"visual/{i}", "art", {"stars": 20 + i}) for i in range(30)]
        picked = prioritize_hits(hits, {"cat": "cat", "agent": "agent", "art": "art"}, cfg, 15)
        by_topic = {topic: sum(row[1] == topic for row in picked)
                    for topic in ("cat", "agent", "art")}
        self.assertEqual(len(picked), 15)
        self.assertGreater(by_topic["cat"], by_topic["agent"])
        self.assertGreater(by_topic["cat"], by_topic["art"])
        self.assertGreaterEqual(by_topic["agent"], 1)

    def test_candidate_enrichment_respects_zero_budget(self):
        self.assertEqual(prioritize_hits([("a/b", "cat", {"stars": 99})],
                                         {"cat": "cat"}, example(), 0), [])

    def test_candidate_enrichment_keeps_legacy_star_order(self):
        hits = [("a/low", "misc", {"stars": 5}), ("a/high", "misc", {"stars": 500})]
        picked = prioritize_hits(hits, {"misc": "general"}, {}, 2)
        self.assertEqual([x[0] for x in picked], ["a/high", "a/low"])

    def test_invalid_and_duplicate_ids_are_ignored(self):
        cfg = example()
        cfg["research_lanes"] += [{"id": "cat-magic", "topics": ["tools"], "weight": 10},
                                  {"id": "../bad", "topics": ["tools"], "weight": 10}]
        _, status, _ = plan_queries(cfg, {}, 4)
        self.assertEqual(len(status), 4)


if __name__ == "__main__":
    unittest.main()
