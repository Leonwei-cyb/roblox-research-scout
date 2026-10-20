"""Offline tests for scripts/discovery_scout.py: no token, no network, no CI minutes."""
import importlib.util
import io
import json
import tempfile
import unittest
from datetime import datetime, timezone
from email.message import Message
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("discovery_scout", ROOT / "scripts" / "discovery_scout.py")
ds = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ds)

NOW = datetime(2026, 10, 20, 6, 0, tzinfo=timezone.utc)
SHA_A = "a" * 40
SHA_B = "b" * 40

CONFIG = {
    "limits": {"per_page": 20, "max_search_queries": 4, "graphql_batch_size": 15, "max_graphql_batches": 2,
               "max_new_candidates_per_run": 10, "min_rest_remaining": 10, "min_graphql_remaining": 10,
               "stale_days": 365, "max_versions_per_repo": 2, "max_backlog": 5, "stale_after_hours": 13},
    "verdict_rules": {"needs_test_min_score": 45, "route_min_score": 60},
    "topics": [{"id": "relay", "queries": ["webhook relay"]}],
    "watch_repos": [],
    "audited_elsewhere": {"busy/monitor": "already audited"},
    "carried_forward": [],
    "blockers": [
        {"id": "github-mac-messaging", "owner": "hub", "label": "Low-latency GitHub to Mac messaging",
         "core": ["webhooks?", "\\brelay\\b"], "patterns": ["webhooks?", "localhost", "\\bforward\\w*", "\\brelay\\b"]},
        {"id": "live-dashboard", "owner": "Work/dashboard", "label": "Live agent dashboard",
         "core": ["dashboard"], "patterns": ["dashboard", "\\bmonitor\\w*", "real.?time"]},
    ],
}


def node(name, rid, sha=SHA_A, release="", license_id="MIT", archived=False, fork=False,
         committed="2026-10-15T00:00:00Z", description="Forward GitHub webhooks to localhost relay",
         issues=None):
    return {
        "databaseId": rid, "nameWithOwner": name, "url": "https://github.com/" + name,
        "description": description, "isArchived": archived, "isFork": fork, "isMirror": False,
        "isSecurityPolicyEnabled": True, "securityPolicyUrl": "https://github.com/" + name + "/security/policy",
        "stargazerCount": 100, "pushedAt": committed, "licenseInfo": {"spdxId": license_id, "name": license_id},
        "repositoryTopics": {"nodes": [{"topic": {"name": "webhooks"}}]},
        "latestRelease": ({"tagName": release, "url": "https://github.com/" + name + "/releases/tag/" + release,
                           "publishedAt": committed} if release else None),
        "releases": {"totalCount": 1 if release else 0},
        "defaultBranchRef": {"name": "main", "target": {"oid": sha, "committedDate": committed}},
        "issues": {"totalCount": len(issues or [])},
        "recentIssues": {"nodes": issues or []},
        "object": {"entries": [{"name": "test", "type": "tree"}, {"name": ".github", "type": "tree"}]},
        "workflows": {"entries": [{"name": "ci.yml"}]},
        "readme": {"text": "# Relay\nForwards webhooks."},
    }


class FakeGitHub(ds.GitHub):
    """Replaces the network. `world` maps lower-case repo name -> GraphQL node."""
    world = {}
    search_items = []
    calls_log = []
    rate_limit_search = False
    graphql_errors = []       # repo names whose licenseInfo field errors (null + error entry)

    def get(self, path, params, compact):
        FakeGitHub.calls_log.append(("GET", path))
        if FakeGitHub.rate_limit_search:
            raise ds.RateLimited("GitHub rate limit for " + path, "2026-10-20T07:00:00Z")
        return compact({"items": FakeGitHub.search_items, "total_count": len(FakeGitHub.search_items)}), "ok"

    def graphql(self, query, variables):
        FakeGitHub.calls_log.append(("GRAPHQL", len(variables)))
        assert "$o0" in query and "repository(owner: $o0, name: $n0)" in query
        data, errors = {}, []
        i = 0
        while "o%d" % i in variables:
            name = variables["o%d" % i] + "/" + variables["n%d" % i]
            data["r%d" % i] = FakeGitHub.world.get(name.lower())
            if name.lower() in FakeGitHub.graphql_errors and data["r%d" % i]:
                data["r%d" % i] = dict(data["r%d" % i], licenseInfo=None)
                errors.append({"path": ["r%d" % i, "licenseInfo"], "message": "Something went wrong"})
            i += 1
        return data, errors


def search_item(name, rid, stars=50):
    return {"id": rid, "full_name": name, "stargazers_count": stars, "fork": False, "archived": False,
            "description": "relay", "topics": [], "pushed_at": "2026-10-15T00:00:00Z"}


class DiscoveryRunTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        (root / "watch").mkdir()
        self.config_path = root / "watch" / "discovery.json"
        self.cfg = json.loads(json.dumps(CONFIG))
        self.save_config()
        for attr, rel in (("CONFIG", "watch/discovery.json"), ("STATE", "watch/discovery_state.json"),
                          ("CANDIDATES", "findings/candidates.jsonl"), ("SUMMARY", "findings/SUMMARY.md"),
                          ("REVIEWS", "findings/reviews"), ("STATUS", "status/discovery.json")):
            p = patch.object(ds, attr, root / rel)
            p.start()
            self.addCleanup(p.stop)
        p = patch.object(ds, "GitHub", FakeGitHub)
        p.start()
        self.addCleanup(p.stop)
        FakeGitHub.world = {}
        FakeGitHub.search_items = []
        FakeGitHub.calls_log = []
        FakeGitHub.rate_limit_search = False
        FakeGitHub.graphql_errors = []
        self.root = root

    def save_config(self):
        self.config_path.write_text(json.dumps(self.cfg))

    def rows(self):
        return [json.loads(line) for line in ds.CANDIDATES.read_text().splitlines()]

    def run_once(self, now=NOW, requests_text=""):
        return ds.run(now=now, token="test-token", requests_text=requests_text, event="test")

    def test_new_candidate_is_scored_routed_and_written(self):
        FakeGitHub.search_items = [search_item("acme/relay", 1)]
        FakeGitHub.world = {"acme/relay": node("acme/relay", 1)}
        status = self.run_once()
        rows = self.rows()
        self.assertEqual(1, len(rows))
        r = rows[0]
        self.assertEqual("needs-test", r["verdict"])
        self.assertEqual("hub", r["suggested_owner"])
        self.assertIn("Pin acme/relay@aaaaaaa", r["task"])
        self.assertEqual(SHA_A, r["sha"])
        self.assertEqual("MIT", r["license"])
        self.assertIn("https://github.com/acme/relay/tree/" + SHA_A, r["evidence"])
        for key in ("fit", "maintenance", "license", "security", "total"):
            self.assertIn(key, r["scores"])
        self.assertEqual(1, status["counts"]["actionable_backlog"])
        self.assertFalse(status["freshness"]["continuous"])
        self.assertEqual("ok", status["last_run"]["outcome"])
        self.assertTrue(ds.SUMMARY.read_text().startswith("# Open-source discovery"))

    def test_dedup_same_version_and_rename_keeps_one_record(self):
        FakeGitHub.search_items = [search_item("acme/relay", 1)]
        FakeGitHub.world = {"acme/relay": node("acme/relay", 1, release="v1")}
        self.run_once()
        self.run_once()
        self.assertEqual(1, len(self.rows()))
        # Same GitHub id under a new name: still one record, newest name wins.
        FakeGitHub.search_items = [search_item("acme/relay-next", 1)]
        FakeGitHub.world = {"acme/relay-next": node("acme/relay-next", 1, release="v1"),
                            "acme/relay": node("acme/relay-next", 1, release="v1")}
        self.run_once()
        rows = self.rows()
        self.assertEqual(1, len(rows))
        self.assertEqual("acme/relay-next", rows[0]["repo"])

    def test_new_release_adds_version_and_event_and_is_bounded(self):
        FakeGitHub.search_items = [search_item("acme/relay", 1)]
        for n, tag in enumerate(["v1", "v2", "v3"]):
            FakeGitHub.world = {"acme/relay": node("acme/relay", 1, release=tag, sha=str(n) * 40)}
            status = self.run_once(now=NOW.replace(hour=6 + n))
        rows = self.rows()
        self.assertEqual({"v2", "v3"}, {r["version"] for r in rows})   # max_versions_per_repo = 2
        self.assertEqual(1, status["counts"]["new_releases_this_run"])
        self.assertEqual(1, status["counts"]["repos_tracked"])
        self.assertIn("Release: acme/relay v2 to v3", ds.SUMMARY.read_text())

    def test_issue_updates_on_monitored_repo_are_reported(self):
        FakeGitHub.search_items = [search_item("acme/relay", 1)]
        FakeGitHub.world = {"acme/relay": node("acme/relay", 1)}
        self.run_once()
        FakeGitHub.search_items = []
        FakeGitHub.world = {"acme/relay": node("acme/relay", 1, issues=[
            {"number": 7, "title": "Crash on reconnect", "url": "https://github.com/acme/relay/issues/7",
             "updatedAt": "2026-10-20T08:00:00Z"}])}
        status = self.run_once(now=NOW.replace(hour=9))
        self.assertEqual(1, status["counts"]["updated_issues_this_run"])
        self.assertIn("#7 Crash on reconnect", ds.SUMMARY.read_text())

    def test_rate_limit_stops_and_defers_without_retry(self):
        self.cfg["topics"] = [{"id": "relay", "queries": ["a", "b", "c"]}]
        self.save_config()
        FakeGitHub.rate_limit_search = True
        status = self.run_once()
        gets = [c for c in FakeGitHub.calls_log if c[0] == "GET"]
        self.assertEqual(1, len(gets), "must not keep calling after a rate-limit response")
        self.assertEqual("failed", status["last_run"]["outcome"])
        self.assertEqual(3, status["feed_health"]["deferred"])
        state = json.loads(ds.STATE.read_text())
        self.assertEqual("2026-10-20T07:00:00Z", state["deferred_until"])
        # Next run before the reset time makes no request at all.
        FakeGitHub.calls_log = []
        FakeGitHub.rate_limit_search = False
        self.run_once(now=NOW.replace(minute=30))
        self.assertEqual([], [c for c in FakeGitHub.calls_log if c[0] == "GET"])
        # After the reset the backoff clears and searching resumes.
        self.run_once(now=NOW.replace(hour=8))
        self.assertTrue([c for c in FakeGitHub.calls_log if c[0] == "GET"])
        self.assertNotIn("deferred_until", json.loads(ds.STATE.read_text()))

    def test_review_record_is_the_only_way_to_adopt(self):
        FakeGitHub.search_items = [search_item("acme/relay", 1)]
        FakeGitHub.world = {"acme/relay": node("acme/relay", 1)}
        ds.REVIEWS.mkdir(parents=True)
        (ds.REVIEWS / "acme__relay.json").write_text(json.dumps(
            {"repo": "acme/relay", "sha": SHA_A, "verdict": "adopt", "date": "2026-10-20"}))
        status = self.run_once()
        r = self.rows()[0]
        self.assertEqual("adopt", r["verdict"])
        self.assertIn("findings/reviews/acme__relay.json", r["verdict_reason"])
        self.assertEqual(1, status["counts"]["adopt"])
        self.assertEqual("acme/relay", status["adopted"][0]["repo"])
        # The repo moves on: the adoption no longer covers the new code.
        FakeGitHub.world = {"acme/relay": node("acme/relay", 1, sha=SHA_B)}
        self.run_once(now=NOW.replace(hour=9))
        r = [x for x in self.rows() if x["sha"] == SHA_B][0]
        self.assertEqual("needs-test", r["verdict"])
        self.assertIn("re-test", r["verdict_reason"])

    def test_review_needs_exact_sha_even_when_release_tag_is_unchanged(self):
        """Codex P2 on PR #20: matching the release tag applied a review to untested HEAD commits."""
        FakeGitHub.search_items = [search_item("acme/relay", 1)]
        FakeGitHub.world = {"acme/relay": node("acme/relay", 1, release="v1", sha=SHA_B)}
        ds.REVIEWS.mkdir(parents=True)
        (ds.REVIEWS / "acme__relay.json").write_text(json.dumps(
            {"repo": "acme/relay", "sha": SHA_A, "version": "v1", "verdict": "adopt", "date": "2026-10-20"}))
        status = self.run_once()
        r = self.rows()[0]
        self.assertEqual("needs-test", r["verdict"])
        self.assertIn("re-test", r["verdict_reason"])
        self.assertEqual(0, status["counts"]["adopt"])

    def test_audited_elsewhere_is_never_routed_and_carried_owner_overrides(self):
        self.cfg["carried_forward"] = [{"name": "Dog", "repo": "acme/dog", "owner": "Wheel", "note": "from HQ"}]
        self.save_config()
        FakeGitHub.search_items = [search_item("busy/monitor", 2)]
        FakeGitHub.world = {
            "busy/monitor": node("busy/monitor", 2, description="realtime dashboard monitor relay webhooks"),
            "acme/dog": node("acme/dog", 3, description="webhook relay review"),
        }
        self.run_once()
        rows = {r["repo"]: r for r in self.rows()}
        self.assertIsNone(rows["busy/monitor"]["task"])
        self.assertEqual("already audited", rows["busy/monitor"]["audited_elsewhere"])
        self.assertEqual("Wheel", rows["acme/dog"]["suggested_owner"])
        self.assertEqual("Dog", rows["acme/dog"]["provenance"]["carried_forward"])
        self.assertEqual("carried-forward", rows["acme/dog"]["topic"])

    def test_graphql_field_error_defers_instead_of_rejecting(self):
        FakeGitHub.search_items = [search_item("acme/relay", 1)]
        FakeGitHub.world = {"acme/relay": node("acme/relay", 1)}
        self.run_once()
        self.assertEqual("needs-test", self.rows()[0]["verdict"])
        # Next run the license field fails to resolve: the node comes back with
        # licenseInfo null plus a field error. That is missing data, not "no license".
        FakeGitHub.graphql_errors = ["acme/relay"]
        status = self.run_once(now=NOW.replace(hour=7))
        rows = self.rows()
        self.assertEqual(1, len(rows))
        self.assertEqual("needs-test", rows[0]["verdict"])
        self.assertEqual("MIT", rows[0]["license"])
        feed = [f for f in status["feeds"] if f["kind"] == "graphql"][0]
        self.assertEqual("error", feed["status"])          # every repo in the batch was deferred
        self.assertIn("1 deferred after GraphQL field errors", feed["detail"])
        self.assertEqual("partial", status["last_run"]["outcome"])
        # A brand-new repo hit by a field error is not written as a reject either.
        FakeGitHub.search_items = [search_item("acme/newbie", 2)]
        FakeGitHub.world["acme/newbie"] = node("acme/newbie", 2)
        FakeGitHub.graphql_errors = ["acme/newbie"]
        self.run_once(now=NOW.replace(hour=8))
        self.assertNotIn("acme/newbie", {r["repo"] for r in self.rows()})

    def test_monitored_repos_keep_reserved_slots_when_fresh_hits_fill_budget(self):
        self.cfg["limits"].update({"graphql_batch_size": 3, "max_graphql_batches": 1})
        self.save_config()
        FakeGitHub.search_items = [search_item("acme/relay", 1)]
        FakeGitHub.world = {"acme/relay": node("acme/relay", 1)}
        self.run_once()
        self.assertEqual("needs-test", self.rows()[0]["verdict"])
        # Later runs: more popular fresh hits alone would fill all 3 slots every time.
        FakeGitHub.search_items = [search_item("acme/hot%d" % n, 10 + n, stars=900 - n) for n in range(5)]
        FakeGitHub.world.update({"acme/hot%d" % n: node("acme/hot%d" % n, 10 + n) for n in range(5)})
        FakeGitHub.world["acme/relay"] = node("acme/relay", 1, release="v2")
        later = NOW.replace(hour=9)
        self.run_once(now=later)
        relay = [r for r in self.rows() if r["repo"] == "acme/relay"]
        self.assertIn("v2", {r["version"] for r in relay})
        self.assertEqual(ds.iso(later), max(r["last_checked"] for r in relay))

    def test_audited_identity_survives_a_rename(self):
        # Config names the old repo; GitHub now answers under a new name (same id).
        FakeGitHub.search_items = [search_item("busy/monitor-v2", 7)]
        FakeGitHub.world = {"busy/monitor-v2": node("busy/monitor-v2", 7)}
        self.cfg["watch_repos"] = ["busy/monitor"]
        self.save_config()
        FakeGitHub.world["busy/monitor"] = node("busy/monitor-v2", 7)
        self.run_once()
        rows = {r["repo"]: r for r in self.rows()}
        self.assertEqual("already audited", rows["busy/monitor-v2"]["audited_elsewhere"])
        self.assertIsNone(rows["busy/monitor-v2"]["task"])
        # Next run only the new name appears (no watch entry): the prior note, found by id, holds.
        self.cfg["watch_repos"] = []
        self.save_config()
        del FakeGitHub.world["busy/monitor"]
        self.run_once(now=NOW.replace(hour=7))
        rows = {r["repo"]: r for r in self.rows()}
        self.assertEqual("already audited", rows["busy/monitor-v2"]["audited_elsewhere"])
        # The GitHub id form also matches with no name at all.
        self.assertEqual("x", ds.audited_note({"audited_elsewhere": {"id:7": "x"}}, {"id": 7, "repo": "a/b"}))
        # Dropping it from the config clears the sticky note.
        self.assertIsNone(ds.audited_note({"audited_elsewhere": {}}, {"id": 7, "repo": "a/b"},
                                          prior={"audited_elsewhere": "already audited"}))

    def test_carried_manual_verdict_cannot_adopt_or_override_hard_facts(self):
        self.cfg["carried_forward"] = [
            {"name": "Manual", "repo": "acme/manual", "owner": "Wheel", "verdict": "needs-test", "reason": "read-only check"},
            {"name": "Sneaky", "repo": "acme/sneaky", "verdict": "adopt", "reason": "trust me"},
            {"name": "NoLicense", "repo": "acme/nolic", "verdict": "needs-test", "reason": "looks good"}]
        self.save_config()
        FakeGitHub.world = {"acme/manual": node("acme/manual", 5, description="unrelated words"),
                            "acme/sneaky": node("acme/sneaky", 6, description="unrelated words"),
                            "acme/nolic": node("acme/nolic", 7, license_id="NONE")}
        self.run_once()
        rows = {r["repo"]: r for r in self.rows()}
        self.assertEqual("needs-test", rows["acme/manual"]["verdict"])
        self.assertEqual("Wheel", rows["acme/manual"]["suggested_owner"])
        self.assertIn("Pin acme/manual@", rows["acme/manual"]["task"])
        self.assertNotEqual("adopt", rows["acme/sneaky"]["verdict"])
        self.assertEqual("reject", rows["acme/nolic"]["verdict"])

    def test_requested_repos_are_validated_and_bounded(self):
        FakeGitHub.world = {"acme/relay": node("acme/relay", 1)}
        self.run_once(requests_text="please check https://github.com/acme/relay; $(rm -rf /) ../../etc")
        self.assertEqual(["acme/relay"], [r["repo"] for r in self.rows()])
        self.assertEqual("requested", self.rows()[0]["topic"])


class VerdictTests(unittest.TestCase):
    def facts(self, **kw):
        f = ds.facts_from_graphql(node("acme/relay", 1, **kw))
        return f

    def verdict(self, **kw):
        f = self.facts(**kw)
        scores, fits, days, _ = ds.score(f, CONFIG["blockers"], NOW)
        return ds.decide(f, scores, fits, days, CONFIG, None)

    def test_rules(self):
        self.assertEqual("reject", self.verdict(archived=True)[0])
        self.assertEqual("reject", self.verdict(fork=True)[0])
        self.assertEqual("reject", self.verdict(license_id="NONE")[0])
        self.assertEqual("reject", self.verdict(committed="2024-01-01T00:00:00Z")[0])
        self.assertEqual("needs-test", self.verdict()[0])
        noassert = self.verdict(license_id="NOASSERTION")
        self.assertEqual("needs-test", noassert[0])
        self.assertIn("unclassified", noassert[1])

    def test_generic_words_alone_never_fit_a_blocker(self):
        text = "claude agents github tool for monitoring forward thinking"
        self.assertEqual({}, ds.blocker_fit(text, [CONFIG["blockers"][0]]))
        self.assertEqual(1.0, ds.blocker_fit("webhook relay forward to localhost", CONFIG["blockers"])["github-mac-messaging"])

    def test_readme_text_is_used_for_scoring_but_never_stored(self):
        f = self.facts(description="")
        self.assertIn("readme_excerpt", f)
        rec = ds.build_record(f, CONFIG, NOW, None, None, "search")
        self.assertNotIn("readme_excerpt", json.dumps(rec))
        self.assertTrue(rec["blockers"])

    def test_ci_needs_real_workflow_files(self):
        """Codex P2 (PR #20): a .github folder with only issue templates counted as CI."""
        n = node("acme/relay", 1)
        n["object"] = {"entries": [{"name": ".github", "type": "tree"}]}
        n["workflows"] = None
        self.assertFalse(ds.facts_from_graphql(n)["has_ci"])
        n["workflows"] = {"entries": [{"name": "ci.yml"}]}
        self.assertTrue(ds.facts_from_graphql(n)["has_ci"])
        n["workflows"] = None
        n["object"] = {"entries": [{"name": ".gitlab-ci.yml", "type": "blob"}]}
        self.assertTrue(ds.facts_from_graphql(n)["has_ci"])

    def test_parse_requests(self):
        self.assertEqual(["a/b", "c/d.e"], ds.parse_requests("a/b https://github.com/c/d.e.git a/b"))
        self.assertEqual(5, len(ds.parse_requests(" ".join("o/r%d" % i for i in range(9)))))
        self.assertFalse(ds.valid_repo("../etc"))

    def test_markdown_is_inert(self):
        out = ds.md("[click](http://x) | `x` <script> # h *b*")
        self.assertNotIn("](", out.replace("\\]", ""))
        self.assertNotIn("`", out)
        self.assertNotIn("<", out)


class HttpClientTests(unittest.TestCase):
    """The real GitHub client: ETag reuse and rate-limit detection."""

    class Resp(io.BytesIO):
        def __init__(self, body, headers):
            super().__init__(json.dumps(body).encode())
            self.headers = headers

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    def headers(self, **kw):
        m = Message()
        for k, v in kw.items():
            m[k.replace("_", "-")] = v
        return m

    def test_etag_conditional_request_reuses_cache_on_304(self):
        gh = ds.GitHub("t", {}, {}, NOW)
        sent = []

        def fake_urlopen(req, timeout):
            sent.append(dict(req.header_items()))
            if len(sent) == 1:
                return self.Resp({"items": [search_item("acme/relay", 1)], "total_count": 1},
                                 self.headers(ETag='W/"abc"', X_RateLimit_Remaining="29", X_RateLimit_Resource="search"))
            raise HTTPError(req.full_url, 304, "Not Modified", self.headers(X_RateLimit_Remaining="29"), None)

        with patch.object(ds, "urlopen", fake_urlopen):
            first, s1 = gh.get("/search/repositories", {"q": "x"}, ds.compact_search)
            second, s2 = gh.get("/search/repositories", {"q": "x"}, ds.compact_search)
        self.assertEqual(("ok", "not_modified"), (s1, s2))
        self.assertEqual(first, second)
        self.assertNotIn("If-none-match", sent[0])
        self.assertEqual('W/"abc"', sent[1]["If-none-match"])
        self.assertEqual(1, gh.calls["rest_not_modified"])
        self.assertEqual(29, gh.rate["search"]["remaining"])

    def test_403_with_zero_remaining_is_a_rate_limit_not_a_retry(self):
        gh = ds.GitHub("t", {}, {}, NOW)

        def fake_urlopen(req, timeout):
            raise HTTPError(req.full_url, 403, "Forbidden",
                            self.headers(X_RateLimit_Remaining="0", X_RateLimit_Reset="1792476000"), None)

        with patch.object(ds, "urlopen", fake_urlopen):
            with self.assertRaises(ds.RateLimited) as ctx:
                gh.get("/search/repositories", {"q": "x"}, ds.compact_search)
        self.assertTrue(ctx.exception.reset_at.endswith("Z"))

    def test_graphql_requires_token_and_uses_variables(self):
        with self.assertRaises(RuntimeError):
            ds.GitHub("", {}, {}, NOW).graphql("query{x}", {})
        query, variables = ds.build_graphql(['evil"){x}/repo'.replace('"', ""), "a/b"][1:])
        self.assertEqual({"o0": "a", "n0": "b"}, variables)
        self.assertNotIn('"a"', query)

    def test_token_never_written_to_outputs(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        (root / "watch").mkdir()
        (root / "watch" / "discovery.json").write_text(json.dumps(CONFIG))
        patches = [patch.object(ds, a, root / r) for a, r in (
            ("CONFIG", "watch/discovery.json"), ("STATE", "watch/discovery_state.json"),
            ("CANDIDATES", "findings/candidates.jsonl"), ("SUMMARY", "findings/SUMMARY.md"),
            ("REVIEWS", "findings/reviews"), ("STATUS", "status/discovery.json"))]
        patches.append(patch.object(ds, "GitHub", FakeGitHub))
        for p in patches:
            p.start()
            self.addCleanup(p.stop)
        FakeGitHub.search_items = [search_item("acme/relay", 1)]
        FakeGitHub.world = {"acme/relay": node("acme/relay", 1)}
        FakeGitHub.rate_limit_search = False
        ds.run(now=NOW, token="ghs_SECRETVALUE123", requests_text="", event="test")
        for path in root.rglob("*"):
            if path.is_file():
                self.assertNotIn("ghs_SECRETVALUE123", path.read_text())


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.data = (ROOT / ".github" / "workflows" / "discovery.yml").read_text(encoding="utf-8")

    def test_event_triggers_and_scheduled_backstop(self):
        for needle in ("  schedule:", "  workflow_dispatch:", "  repository_dispatch:", "types: [discovery-scan]",
                       "  issues:", "types: [labeled]"):
            self.assertIn(needle, self.data)
        self.assertIn("- cron: '47 */6 * * *'", self.data)

    def test_least_privilege_and_no_merge(self):
        self.assertIn("permissions:\n  contents: write", self.data)
        discover, sep, route = self.data.partition("\n  route-issues:\n")
        self.assertTrue(sep)
        self.assertNotIn("issues: write", discover)
        self.assertIn("      contents: write\n      issues: write", route)
        self.assertIn("git add findings/issue_ledger.json", route)
        self.assertIn("needs: discover", route)
        for banned in ("pull-requests: write", "gh pr merge", "pulls.merge", "--force", "push -f"):
            self.assertNotIn(banned, self.data)
        self.assertIn("secrets.GITHUB_TOKEN", self.data)
        self.assertNotIn("secrets.", self.data.replace("secrets.GITHUB_TOKEN", ""))

    def test_untrusted_input_goes_through_env_not_shell(self):
        run_lines = [line for line in self.data.splitlines() if "${{" in line and "github.event" in line]
        for line in run_lines:
            self.assertTrue(line.strip().startswith(("DISCOVERY_REQUESTS:", "if:")), line)
        self.assertIn("author_association", self.data)

    def test_commits_only_discovery_outputs(self):
        self.assertIn("git add findings/ status/discovery.json watch/discovery_state.json", self.data)
        adds = [line.strip() for line in self.data.splitlines() if line.strip().startswith("git add")]
        self.assertEqual(["git add findings/ status/discovery.json watch/discovery_state.json",
                          "git add findings/issue_ledger.json 2>/dev/null || true"], adds)
        self.assertNotIn("git add -A", self.data)


if __name__ == "__main__":
    unittest.main()
