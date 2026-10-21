"""OFFLINE acceptance fixture for the multi-ChatGPT web-worker query pack.

Owner acceptance test (one-tower-tycoon#1 comment 6283915095): the pack must
find and rank Xalzeroph/Charterion, megamen32/chatgpt-multi and
paritoshv/multi-llm-web-orchestrator among decoys, and must tell real
browser-session orchestration apart from API-only multi-agent frameworks.

The three real repos are represented by short excerpts of their own README,
manifest.json and package.json at the SHAs below (read 2026-10-20). The decoys
are fictional ("decoy-org/*"). The fixture decides which query returns which
repo, so this tests our dedup, inspection, classification and ranking, NOT
GitHub's search engine; the live run in findings/packs/ is the real-world check.
"""
import importlib.util
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("discovery_scout_fixture", ROOT / "scripts" / "discovery_scout.py")
ds = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ds)

NOW = datetime(2026, 10, 20, 6, 0, tzinfo=timezone.utc)
CHARTERION, MULTI, ORCH = "Xalzeroph/Charterion", "megamen32/chatgpt-multi", "paritoshv/multi-llm-web-orchestrator"

REPOS = {
    CHARTERION: dict(id=101, sha="afde4a493fa11311e56b4cf164f56c37940869f4", license="Apache-2.0",
                     committed="2026-09-21T03:03:11Z", stars=4,
                     description="Charterion: Multi-Agent Engineering Control Plane for ChatGPT Web Agents - orchestration, "
                                 "task dispatch, browser control, durable state, worktrees, evidence, review, recovery.",
                     files={
                         "README.md": "# Charterion\n**A local-first engineering control plane that turns multiple ChatGPT Web "
                                      "conversations into a durable, role-based Agent organization.**\n> GAM coordinates "
                                      "ChatGPT Web. It does not replace ChatGPT with an API provider, does not store account "
                                      "credentials.\nCharterion manages multiple ChatGPT Web conversations as persistent "
                                      "engineering workers. Browser tabs are disposable runtime surfaces.",
                         "manifest.json": '{"manifest_version": 3, "name": "Charterion", "permissions": ["tabs", "storage", '
                                          '"sidePanel", "nativeMessaging", "alarms"], "host_permissions": '
                                          '["https://chatgpt.com/*"], "content_scripts": [{"matches": '
                                          '["https://chatgpt.com/*"], "js": ["dist/content.js"]}]}',
                         "package.json": '{"name": "charterion", "license": "Apache-2.0", "scripts": {"test": "vitest run"}, '
                                         '"devDependencies": {"@types/chrome": "^0.2.8", "jsdom": "^30.0.1", "vitest": "^5.0.0"}}',
                         "control/src/browserAuthority.ts": "export class BrowserAuthority { /* chrome.tabs leases */ }",
                     },
                     tests=["control/test/browserAuthority.test.ts"]),
    MULTI: dict(id=102, sha="07f44c9184d2d3d7d987f406c34f3f2f4a9f42d5", license="NONE",
                committed="2026-06-27T23:25:50Z", stars=31,
                description="Multi-pane ChatGPT workspace Chrome extension with side-by-side chats, lazy panes, prompt "
                            "queue, goal agent, and Telegram bridge.",
                files={
                    "README.md": "# ChatGPT Multi Pane\nMulti-pane ChatGPT workspace as a Chrome extension: several ChatGPT "
                                 "chats side by side. Each pane is a live `https://chatgpt.com` iframe. A MAIN-world content "
                                 "script patches fetch for /backend-api/conversation.",
                    "manifest.json": '{"manifest_version": 3, "name": "ChatGPT Multi Pane", "permissions": ["storage", '
                                     '"sidePanel", "activeTab"], "host_permissions": ["https://chatgpt.com/*", '
                                     '"https://chat.openai.com/*"], "content_scripts": [{"matches": ["https://chatgpt.com/*"]}]}',
                    "package.json": '{"name": "chatgpt-multi-pane-extension", "scripts": {"test": "node --test test/*.test.js"}}',
                    "src/content/features/queue.js": "// prompt queue for the composer textarea",
                },
                tests=["test/queue-model.test.js", "test/pane-store.test.js"]),
    ORCH: dict(id=103, sha="a6496805076afb7bd0e4afec1712f17e7de597dd", license="MIT",
               committed="2026-06-16T13:13:16Z", stars=1,
               description="Chrome side-panel extension that orchestrates ChatGPT, Claude, Gemini, and Grok through "
                           "authenticated browser sessions.",
               files={
                   "README.md": "# Multi-LLM Web Orchestrator\nA Chrome side-panel extension that fans out one prompt to "
                                "multiple frontier LLM web apps running in your own authenticated browser sessions. Instead "
                                "of using official APIs, it automates real browser UIs with content scripts.",
                   "manifest.json": '{"manifest_version": 3, "permissions": ["sidePanel", "tabs", "scripting"], '
                                    '"host_permissions": ["https://chatgpt.com/*", "https://claude.ai/*", '
                                    '"https://gemini.google.com/*", "https://grok.com/*"], "content_scripts": []}',
                   "package.json": '{"name": "multi-llm-web-extension", "scripts": {"test": "node --test"}}',
                   "background.js": "chrome.tabs.query({}); chrome.scripting.executeScript({});",
               },
               tests=["tests/content-helpers.test.js"]),
    # ---- decoys (fictional)
    "decoy-org/agent-crew": dict(id=201, sha="1" * 40, license="MIT", committed="2026-10-10T00:00:00Z", stars=9000,
                                 description="Multi-agent orchestration framework: role agents, task dispatch, durable "
                                             "sessions, parallel workers.",
                                 files={"README.md": "# Agent Crew\nParallel multi-agent orchestration. Set OPENAI_API_KEY "
                                                     "and ANTHROPIC_API_KEY before running.",
                                        "package.json": '{"dependencies": {"openai": "^5.0.0", "@langchain/core": "^1.0.0"}}',
                                        "src/agent.ts": "const client = new OpenAI();"},
                                 tests=["test/agent.test.ts"]),
    "decoy-org/chatgpt-cli-swarm": dict(id=202, sha="2" * 40, license="Apache-2.0", committed="2026-10-01T00:00:00Z",
                                        stars=1500,
                                        description="Run many ChatGPT conversations in parallel from the terminal with a "
                                                    "conversation queue.",
                                        files={"README.md": "# chatgpt-cli-swarm\nParallel ChatGPT conversations over the "
                                                            "API (api.openai.com). Export OPENAI_API_KEY.",
                                               "requirements.txt": "openai>=1.40\nrich\n",
                                               "swarm/worker.py": "from openai import OpenAI\n"},
                                        tests=["tests/test_queue.py"]),
    "decoy-org/browser-and-api": dict(id=203, sha="3" * 40, license="MIT", committed="2026-10-05T00:00:00Z", stars=300,
                                      description="Browser agent that drives web apps and also calls model APIs.",
                                      files={"README.md": "# browser-and-api\nUses launchPersistentContext to keep a "
                                                          "logged-in profile on chatgpt.com; summaries via api.openai.com.",
                                             "package.json": '{"dependencies": {"playwright": "^1.50.0", "openai": "^5.0.0"}}'},
                                      tests=[]),
    "decoy-org/session-store": dict(id=204, sha="4" * 40, license="MIT", committed="2026-10-12T00:00:00Z", stars=5000,
                                    description="Durable session manager for web servers (Redis, Postgres).",
                                    files={"README.md": "# session-store\nDurable HTTP session manager with cookies.",
                                           "package.json": '{"dependencies": {"redis": "^5.0.0"}}'},
                                    tests=["test/store.test.js"]),
    "decoy-org/weather-dashboard": dict(id=205, sha="5" * 40, license="MIT", committed="2026-10-12T00:00:00Z", stars=20000,
                                        description="Realtime weather dashboard.",
                                        files={"README.md": "# Weather\nForecasts."}, tests=[]),
}

# query id -> repos GitHub "returned", in order. Decoys deliberately rank FIRST.
SEARCH = {
    "a": ["decoy-org/agent-crew", "decoy-org/chatgpt-cli-swarm", CHARTERION],
    "b": ["decoy-org/browser-and-api", ORCH],
    "c": ["decoy-org/agent-crew", ORCH, "decoy-org/weather-dashboard"],
    "d": ["decoy-org/agent-crew", "xalzeroph/charterion"],          # lower-case duplicate of Charterion
    "e": ["decoy-org/browser-and-api", MULTI, ORCH],
    "f": ["decoy-org/chatgpt-cli-swarm", MULTI],
    "g": ["decoy-org/session-store", "decoy-org/agent-crew", CHARTERION],
    # source (code) search: file matches, no popularity ranking
    "s1": [MULTI, CHARTERION],
    "s2": [MULTI, ORCH],
    "s3": ["decoy-org/browser-and-api"],
}


def canonical(name):
    return next(k for k in REPOS if k.lower() == name.lower())


class FixtureGitHub(ds.GitHub):
    log_calls = []

    def get(self, path, params, compact):
        self.calls["rest"] += 1
        self.log.append({"kind": "rest", "what": "GET " + path, "outcome": "200"})
        if path == "/search/repositories":
            q = params["q"]
            pack = json.loads((ROOT / "watch" / "discovery.json").read_text())["query_packs"][0]
            qid = next(x["id"] for x in pack["queries"] if q.startswith(x["q"] + " ") or q.startswith(x["relaxed"] + " "))
            items = []
            for name in SEARCH[qid]:
                r = REPOS[canonical(name)]
                items.append({"id": r["id"], "full_name": name, "stargazers_count": r["stars"], "fork": False,
                              "archived": False, "description": r["description"], "topics": [],
                              "pushed_at": r["committed"]})
            return compact({"items": items, "total_count": len(items)}), "ok"
        if path == "/search/code":
            pack = json.loads((ROOT / "watch" / "discovery.json").read_text())["query_packs"][0]
            sid = next(x["id"] for x in pack["source_queries"] if x["q"] == params["q"])
            items = [{"path": "manifest.json", "repository": {"id": REPOS[canonical(n)]["id"], "full_name": n,
                                                               "fork": False}} for n in SEARCH[sid]]
            return compact({"items": items, "total_count": len(items)}), "ok"
        if "/git/trees/" in path:
            repo = canonical(path.split("/")[2] + "/" + path.split("/")[3])
            r = REPOS[repo]
            entries = [{"path": p, "type": "blob", "size": len(t)} for p, t in r["files"].items()]
            entries += [{"path": p, "type": "blob", "size": 100} for p in r["tests"]]
            return compact({"tree": entries, "truncated": False}), "ok"
        raise AssertionError(path)

    def graphql(self, query, variables, what="graphql"):
        self.calls["graphql"] += 1
        self.log.append({"kind": "graphql", "what": what, "outcome": "sent"})
        data, i = {}, 0
        while "o%d" % i in variables:
            repo = canonical(variables["o%d" % i] + "/" + variables["n%d" % i])
            r = REPOS[repo]
            if "e%d_0" % i in variables:                       # source-file batch
                node, j = {}, 0
                while "e%d_%d" % (i, j) in variables:
                    sha, fpath = variables["e%d_%d" % (i, j)].split(":", 1)
                    assert sha == r["sha"], "files must be read at the pinned SHA"
                    node["f%d" % j] = {"text": r["files"].get(fpath, ""), "byteSize": 10, "isBinary": False}
                    j += 1
                data["r%d" % i] = node
            else:                                               # facts batch
                data["r%d" % i] = {
                    "databaseId": r["id"], "nameWithOwner": repo, "url": "https://github.com/" + repo,
                    "description": r["description"], "isArchived": False, "isFork": False, "isMirror": False,
                    "isSecurityPolicyEnabled": False, "securityPolicyUrl": "", "stargazerCount": r["stars"],
                    "pushedAt": r["committed"], "licenseInfo": {"spdxId": r["license"]} if r["license"] != "NONE" else None,
                    "repositoryTopics": {"nodes": []}, "latestRelease": None, "releases": {"totalCount": 0},
                    "defaultBranchRef": {"name": "main", "target": {"oid": r["sha"], "committedDate": r["committed"]}},
                    "issues": {"totalCount": 0}, "recentIssues": {"nodes": []},
                    "object": {"entries": [{"name": "README.md", "type": "blob"}]},
                    "readme": {"text": r["files"].get("README.md", "")},
                }
            i += 1
        return data, []


class MultiChatGPTPackFixtureTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        (root / "watch").mkdir()
        cfg = json.loads((ROOT / "watch" / "discovery.json").read_text())
        cfg["topics"], cfg["watch_repos"], cfg["carried_forward"] = [], [], []   # the pack alone
        (root / "watch" / "discovery.json").write_text(json.dumps(cfg))
        for attr, rel in (("CONFIG", "watch/discovery.json"), ("STATE", "watch/discovery_state.json"),
                          ("CANDIDATES", "findings/candidates.jsonl"), ("SUMMARY", "findings/SUMMARY.md"),
                          ("REVIEWS", "findings/reviews"), ("STATUS", "status/discovery.json"),
                          ("PACKS", "findings/packs")):
            p = patch.object(ds, attr, root / rel)
            p.start()
            self.addCleanup(p.stop)
        p = patch.object(ds, "GitHub", FixtureGitHub)
        p.start()
        self.addCleanup(p.stop)
        ds.run(now=NOW, token="fixture", requests_text="", event="fixture")
        self.report = json.loads((root / "findings" / "packs" / "multi-chatgpt-web-workers.json").read_text())
        self.by = {c["repo"]: c for c in self.report["candidates"]}
        self.rows = [json.loads(x) for x in (root / "findings" / "candidates.jsonl").read_text().splitlines()]
        self.root = root

    def test_three_known_projects_found_and_ranked_first(self):
        order = [c["repo"] for c in self.report["candidates"]]
        self.assertEqual({CHARTERION, MULTI, ORCH}, set(order[:3]), order)
        for name in (CHARTERION, MULTI, ORCH):
            self.assertEqual("browser-session", self.by[name]["mode"], self.by[name])
        known = {k["repo"]: k for k in self.report["known_relevant"]}
        self.assertTrue(all(known[n]["found_by"] and known[n]["rank"] <= 3 for n in (CHARTERION, MULTI, ORCH)))

    def test_api_only_frameworks_are_told_apart(self):
        for name in ("decoy-org/agent-crew", "decoy-org/chatgpt-cli-swarm"):
            self.assertEqual("api-only", self.by[name]["mode"])
            self.assertEqual("reject", self.by[name]["pack_verdict"])
            self.assertIn("API-only", self.by[name]["pack_reason"])
        self.assertEqual("mixed", self.by["decoy-org/browser-and-api"]["mode"])
        self.assertEqual("unknown", self.by["decoy-org/session-store"]["mode"])
        self.assertEqual("reject", self.by["decoy-org/session-store"]["pack_verdict"])

    def test_verdicts_respect_license_and_route_to_wheel(self):
        self.assertEqual("needs-test", self.by[ORCH]["pack_verdict"])
        self.assertEqual("Wheel", self.by[ORCH]["suggested_owner"])
        self.assertEqual("reject", self.by[MULTI]["pack_verdict"])           # no license: ideas only
        self.assertIn("no license", self.by[MULTI]["pack_reason"])
        self.assertEqual("needs-test", self.by[CHARTERION]["pack_verdict"])

    def test_canonical_dedup_by_repo_and_sha(self):
        names = [c["repo"].lower() for c in self.report["candidates"]]
        self.assertEqual(len(names), len(set(names)))
        self.assertEqual(["a", "d", "g", "s1"], self.by[CHARTERION]["found_by"])
        self.assertEqual(1, sum(1 for r in self.rows if r["repo"].lower() == CHARTERION.lower()))
        self.assertTrue(self.by[CHARTERION]["evidence"][0].endswith("/tree/" + REPOS[CHARTERION]["sha"]))

    def test_sources_were_inspected_and_api_calls_counted(self):
        self.assertIn("manifest.json", self.by[ORCH]["files_inspected"])
        self.assertIn("README.md", self.by[ORCH]["files_inspected"])
        self.assertGreaterEqual(self.by[MULTI]["tests_found"], 2)
        calls = self.report["api_calls"]
        self.assertEqual(calls["total"], len(calls["calls"]))
        self.assertEqual(14, sum(1 for c in calls["calls"] if c["what"].startswith("GET /search/repositories")))
        self.assertEqual(3, sum(1 for c in calls["calls"] if c["what"].startswith("GET /search/code")))
        self.assertIn("s1", self.by[MULTI]["found_by"])
        md = (self.root / "findings" / "packs" / "multi-chatgpt-web-workers.md").read_text()
        self.assertIn("not full GitHub coverage", md.replace("Not full", "not full"))

    def test_known_repos_are_never_search_input(self):
        cfg = json.loads((ROOT / "watch" / "discovery.json").read_text())
        words = " ".join(q["q"] + " " + q["relaxed"] for q in cfg["query_packs"][0]["queries"]).lower()
        for name in cfg["query_packs"][0]["known_relevant"]:
            for part in name.lower().split("/"):
                self.assertNotIn(part, words)


class InspectionFailureTest(unittest.TestCase):
    """Codex P2 (PR #20): a failed tree read became 'unknown' and then a definitive reject."""

    def test_failed_inspection_is_deferred_not_rejected(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        (root / "watch").mkdir()
        cfg = json.loads((ROOT / "watch" / "discovery.json").read_text())
        cfg["topics"], cfg["watch_repos"], cfg["carried_forward"] = [], [], []
        (root / "watch" / "discovery.json").write_text(json.dumps(cfg))

        class FlakyTrees(FixtureGitHub):
            def get(self, path, params, compact):
                if "/git/trees/" in path and "multi-llm-web-orchestrator" in path:
                    raise RuntimeError("GitHub HTTP 502 for tree")
                return FixtureGitHub.get(self, path, params, compact)

        patches = [patch.object(ds, a, root / r) for a, r in (
            ("CONFIG", "watch/discovery.json"), ("STATE", "watch/discovery_state.json"),
            ("CANDIDATES", "findings/candidates.jsonl"), ("SUMMARY", "findings/SUMMARY.md"),
            ("REVIEWS", "findings/reviews"), ("STATUS", "status/discovery.json"), ("PACKS", "findings/packs"))]
        patches.append(patch.object(ds, "GitHub", FlakyTrees))
        for p in patches:
            p.start()
            self.addCleanup(p.stop)
        ds.run(now=NOW, token="fixture", requests_text="", event="fixture")
        report = json.loads((root / "findings" / "packs" / "multi-chatgpt-web-workers.json").read_text())
        c = {x["repo"]: x for x in report["candidates"]}[ORCH]
        self.assertEqual("needs-test", c["pack_verdict"])
        self.assertIn("deferred", c["pack_reason"])
        self.assertTrue(c["inspection_error"])


class IncompleteInspectionTest(unittest.TestCase):
    """Codex P2 (PR #20): truncated trees / partial GraphQL reads were classified as if complete."""

    def run_with(self, gh_class):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        (root / "watch").mkdir()
        cfg = json.loads((ROOT / "watch" / "discovery.json").read_text())
        cfg["topics"], cfg["watch_repos"], cfg["carried_forward"] = [], [], []
        (root / "watch" / "discovery.json").write_text(json.dumps(cfg))
        patches = [patch.object(ds, a, root / r) for a, r in (
            ("CONFIG", "watch/discovery.json"), ("STATE", "watch/discovery_state.json"),
            ("CANDIDATES", "findings/candidates.jsonl"), ("SUMMARY", "findings/SUMMARY.md"),
            ("REVIEWS", "findings/reviews"), ("STATUS", "status/discovery.json"), ("PACKS", "findings/packs"))]
        patches.append(patch.object(ds, "GitHub", gh_class))
        for p in patches:
            p.start()
            self.addCleanup(p.stop)
        ds.run(now=NOW, token="fixture", requests_text="", event="fixture")
        report = json.loads((root / "findings" / "packs" / "multi-chatgpt-web-workers.json").read_text())
        return {x["repo"]: x for x in report["candidates"]}

    def test_truncated_tree_defers_a_would_be_reject(self):
        class Truncated(FixtureGitHub):
            def get(self, path, params, compact):
                if "/git/trees/" in path and "session-store" in path:
                    data, status = FixtureGitHub.get(self, path, params, lambda b: b)
                    return compact(dict(data, truncated=True)), status
                return FixtureGitHub.get(self, path, params, compact)
        c = self.run_with(Truncated)["decoy-org/session-store"]
        self.assertEqual("needs-test", c["pack_verdict"])
        self.assertIn("truncated", c["pack_reason"])

    def test_partial_graphql_defers_but_license_reject_stands(self):
        class Partial(FixtureGitHub):
            def graphql(self, query, variables, what="graphql"):
                data, errors = FixtureGitHub.graphql(self, query, variables, what)
                if "e0_0" in variables:
                    errors = [{"path": ["r%d" % i, "f0"], "message": "timeout"}
                              for i in range(6) if "o%d" % i in variables]
                return data, errors
        cands = self.run_with(Partial)
        self.assertEqual("needs-test", cands["decoy-org/agent-crew"]["pack_verdict"])
        self.assertIn("partial", cands["decoy-org/agent-crew"]["pack_reason"])
        self.assertEqual("reject", cands[MULTI]["pack_verdict"])          # no license, files irrelevant
        self.assertIn("no license", cands[MULTI]["pack_reason"])


    def test_mirror_is_never_a_routable_pack_candidate(self):
        """Codex P2 (PR #20): the record rejected a mirror but the pack still made it needs-test."""
        class Mirror(FixtureGitHub):
            def graphql(self, query, variables, what="graphql"):
                data, errors = FixtureGitHub.graphql(self, query, variables, what)
                for node in data.values():
                    if node and node.get("nameWithOwner") == CHARTERION:
                        node["isMirror"] = True
                return data, errors
        cands = self.run_with(Mirror)
        self.assertEqual("reject", cands[CHARTERION]["pack_verdict"])
        self.assertIn("mirror", cands[CHARTERION]["pack_reason"])
        self.assertIsNone(cands[CHARTERION]["suggested_owner"])
        self.assertEqual("needs-test", cands[ORCH]["pack_verdict"])       # others unaffected


class NoApiKeyWordingTest(unittest.TestCase):
    """Live false positive (TED-H-com/multi-ai-chat, 2026-10-20): 'There are no model API keys' and
    'do not require model API keys' were read as needing an API key, so a browser-session
    extension was labelled mixed."""

    def test_denials_of_api_keys_are_not_api_evidence(self):
        packs = ds.packs
        for text in ("There are no model API keys and no separate chat backend.",
                     "Both editions use the providers' web sessions and do not require model API keys.",
                     "Works without an API key.", "No API keys needed."):
            mode, _browser, api = packs.classify({"README.md": text, "manifest.json":
                                                  '{"manifest_version": 3, "content_scripts": [], "host_permissions": ["https://chatgpt.com/*"]}'})
            self.assertEqual([], api, text)
            self.assertEqual("browser-session", mode, text)
        _m, _b, api = packs.classify({"README.md": "Set your OpenAI API key in settings."})
        self.assertEqual(["needs a model API key"], api)


if __name__ == "__main__":
    unittest.main()


class StalePackReportTest(unittest.TestCase):
    """Codex P2 (PR #20): a pack skipped by a rate limit left last run's report for the issue router."""

    def test_skipped_pack_replaces_its_report_with_a_deferred_one(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        (root / "watch").mkdir()
        cfg = json.loads((ROOT / "watch" / "discovery.json").read_text())
        cfg["topics"], cfg["watch_repos"], cfg["carried_forward"] = [], [], []
        (root / "watch" / "discovery.json").write_text(json.dumps(cfg))
        patches = [patch.object(ds, a, root / r) for a, r in (
            ("CONFIG", "watch/discovery.json"), ("STATE", "watch/discovery_state.json"),
            ("CANDIDATES", "findings/candidates.jsonl"), ("SUMMARY", "findings/SUMMARY.md"),
            ("REVIEWS", "findings/reviews"), ("STATUS", "status/discovery.json"), ("PACKS", "findings/packs"))]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)
        with patch.object(ds, "GitHub", FixtureGitHub):
            ds.run(now=NOW, token="fixture", requests_text="", event="fixture")
        path = root / "findings" / "packs" / "multi-chatgpt-web-workers.json"
        self.assertTrue(json.loads(path.read_text())["candidates"])

        class Limited(FixtureGitHub):
            def get(self, path, params, compact):
                if path.startswith("/search/"):
                    raise ds.RateLimited("GitHub rate limit for " + path, "2026-10-20T09:00:00Z")
                return FixtureGitHub.get(self, path, params, compact)

        # A topic search hits the limit first, so the pack never runs this time.
        cfg["topics"] = [{"id": "t", "queries": ["anything"]}]
        # New specialist planner only schedules topics assigned to active lanes.
        cfg["research_lanes"] = [{"id": "fixture", "topics": ["t"], "weight": 1}]
        (root / "watch" / "discovery.json").write_text(json.dumps(cfg))
        with patch.object(ds, "GitHub", Limited):
            ds.run(now=NOW.replace(hour=7), token="fixture", requests_text="", event="fixture")
        report = json.loads(path.read_text())
        self.assertEqual("deferred", report["status"])
        self.assertEqual([], report["candidates"])
        self.assertEqual(ds.iso(NOW), report["previous_run_at"])
        self.assertIn("DEFERRED", (root / "findings" / "packs" / "multi-chatgpt-web-workers.md").read_text())
        spec = importlib.util.spec_from_file_location("discovery_issues", ROOT / "scripts" / "discovery_issues.py")
        di = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(di)
        stale = dict(report, candidates=[{"repo": "a/b", "pack_verdict": "needs-test", "rank_score": 99}])
        self.assertEqual([], di.selected([stale]))

        # Pack itself limited mid-way (state backoff cleared): report is marked partial, not ok.
        (root / "watch" / "discovery_state.json").write_text("{}")
        cfg["topics"] = []
        (root / "watch" / "discovery.json").write_text(json.dumps(cfg))
        with patch.object(ds, "GitHub", Limited):
            ds.run(now=NOW.replace(hour=8), token="fixture", requests_text="", event="fixture")
        self.assertEqual("partial", json.loads(path.read_text())["status"])
