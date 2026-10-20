#!/usr/bin/env python3
"""Open-source discovery for Leon blockers. No AI calls, no installs, no code execution.

What it does each run (all bounded, see watch/discovery.json "limits"):
1. GitHub repository search for each configured topic query (REST, conditional
   requests with ETags, one page each).
2. One batched GraphQL lookup per <= graphql_batch_size repos for the facts the
   verdict needs: default-branch head SHA and date, latest release, license,
   security policy, archived/fork flags, top-level tests/CI folders and the
   most recently updated open issues.
3. Dedup by canonical repo (GitHub's numeric id, so renames do not duplicate)
   and version (latest release tag, or "head" for repos without releases).
4. Score fit against the current Leon blockers, maintenance, license and
   security posture, and record adopt / reject / needs-test with evidence.
   "adopt" (or a reviewed "reject") only ever comes from a tested review record
   in findings/reviews/; automation alone can only reject or ask for a test.
5. Write findings/candidates.jsonl, findings/SUMMARY.md and status/discovery.json.

It never posts to other repositories, never follows links outside api.github.com,
never retries around a rate limit, and never claims continuous coverage.
"""
from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

sys.path.insert(0, str(Path(__file__).resolve().parent))
import discovery_packs as packs  # noqa: E402  (sibling module, stdlib only)

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "watch" / "discovery.json"
STATE = ROOT / "watch" / "discovery_state.json"
CANDIDATES = ROOT / "findings" / "candidates.jsonl"
SUMMARY = ROOT / "findings" / "SUMMARY.md"
REVIEWS = ROOT / "findings" / "reviews"
STATUS = ROOT / "status" / "discovery.json"
PACKS = ROOT / "findings" / "packs"
API = "https://api.github.com"
REPO_RE = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})/[A-Za-z0-9_.-]{1,100}$")
REQUEST_RE = re.compile(r"(?:https://github\.com/)?([A-Za-z0-9][A-Za-z0-9-]{0,38}/[A-Za-z0-9_.-]{1,100})")
PERMISSIVE = {"MIT", "APACHE-2.0", "BSD-2-CLAUSE", "BSD-3-CLAUSE", "ISC", "MPL-2.0",
              "UNLICENSE", "0BSD", "ZLIB", "CC0-1.0", "BSL-1.0"}
VERDICTS = ("adopt", "needs-test", "reject")
OWNERS = ("Wheel", "Work/dashboard", "hub")
SCHEMA = 1


class RateLimited(RuntimeError):
    """GitHub said stop. We stop; we never rotate tokens or retry around it."""

    def __init__(self, message, reset_at=""):
        super().__init__(message)
        self.reset_at = reset_at


def utcnow():
    return datetime.now(timezone.utc).replace(microsecond=0)


def iso(dt):
    return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_iso(text):
    if not text:
        return None
    try:
        dt = datetime.fromisoformat(str(text).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    return dt if dt.tzinfo else None


def safe(text, max_len=160):
    """Third-party text is data: strip control characters and bound the length."""
    text = re.sub(r"[\x00-\x1f\x7f]", " ", str(text or ""))
    return re.sub(r"\s+", " ", text)[:max_len].strip()


def md(text, max_len=160):
    """Make third-party text inert inside the Markdown summary."""
    text = safe(text, max_len).replace("\\", "\\\\")
    for ch in "[]|*_#":
        text = text.replace(ch, "\\" + ch)
    return text.replace("`", "'").replace("<", " ").replace(">", " ")


def valid_repo(name):
    return isinstance(name, str) and bool(REPO_RE.match(name)) and ".." not in name


def parse_requests(text, limit=5):
    """Repos named in a manual or repository_dispatch request. Never more than `limit`."""
    out = []
    for match in REQUEST_RE.finditer(str(text or "")):
        name = match.group(1).rstrip(".")
        if name.endswith(".git"):
            name = name[:-4]
        if valid_repo(name) and name.lower() not in {n.lower() for n in out}:
            out.append(name)
        if len(out) >= limit:
            break
    return out


def read_json(path, fallback):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return fallback


def write_if_changed(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists() or path.read_text(encoding="utf-8") != text:
        path.write_text(text, encoding="utf-8")
        return True
    return False


# --------------------------------------------------------------------------- HTTP

class GitHub:
    """Tiny GitHub client: ETag cache for REST GETs, budget checks, no retries."""

    def __init__(self, token, etags, limits, now):
        self.token = token
        self.etags = etags          # url -> {"etag": str, "data": compact payload}
        self.used_urls = set()
        self.limits = limits
        self.now = now
        self.rate = {}              # resource -> {"remaining": int, "reset_at": iso}
        self.calls = {"rest": 0, "rest_not_modified": 0, "graphql": 0}
        self.log = []               # every request made: kind, what, outcome (no headers, no token)

    def _headers(self, extra=None):
        headers = {"Accept": "application/vnd.github+json",
                   "User-Agent": "leon-oss-discovery-no-ai",
                   "X-GitHub-Api-Version": "2022-11-28"}
        if self.token:
            headers["Authorization"] = "Bearer " + self.token
        headers.update(extra or {})
        return headers

    def _note_rate(self, headers):
        resource = headers.get("X-RateLimit-Resource") or "core"
        remaining = headers.get("X-RateLimit-Remaining")
        reset = headers.get("X-RateLimit-Reset")
        if remaining is not None:
            try:
                entry = {"remaining": int(remaining)}
                if reset:
                    entry["reset_at"] = iso(datetime.fromtimestamp(int(reset), timezone.utc))
                self.rate[resource] = entry
            except ValueError:
                pass

    def budget_ok(self, resource, minimum):
        info = self.rate.get(resource)
        return info is None or info.get("remaining", minimum) >= minimum

    def _raise_for(self, err, what):
        headers = err.headers or {}
        self._note_rate(headers)
        if err.code == 429 or (err.code == 403 and (headers.get("X-RateLimit-Remaining") == "0"
                                                     or headers.get("Retry-After"))):
            reset = ""
            if headers.get("X-RateLimit-Reset"):
                try:
                    reset = iso(datetime.fromtimestamp(int(headers["X-RateLimit-Reset"]), timezone.utc))
                except ValueError:
                    reset = ""
            elif headers.get("Retry-After"):
                try:
                    reset = iso(self.now + timedelta(seconds=int(headers["Retry-After"])))
                except ValueError:
                    reset = ""
            raise RateLimited("GitHub rate limit for " + what, reset)
        raise RuntimeError("GitHub HTTP " + str(err.code) + " for " + what)

    def get(self, path, params, compact):
        """GET with If-None-Match. `compact` turns the JSON body into what we cache."""
        url = API + path + ("?" + urlencode(params) if params else "")
        self.used_urls.add(url)
        cached = self.etags.get(url)
        extra = {"If-None-Match": cached["etag"]} if cached and cached.get("etag") else {}
        self.calls["rest"] += 1
        entry = {"kind": "rest", "what": "GET " + path + ("?" + urlencode(params) if params else ""), "outcome": "error"}
        self.log.append(entry)
        try:
            with urlopen(Request(url, headers=self._headers(extra)), timeout=15) as resp:
                self._note_rate(resp.headers)
                data = compact(json.load(resp))
                etag = resp.headers.get("ETag", "")
                if etag:
                    self.etags[url] = {"etag": etag, "data": data}
                entry["outcome"] = "200"
                return data, "ok"
        except HTTPError as err:
            entry["outcome"] = str(err.code)
            if err.code == 304 and cached:
                self._note_rate(err.headers or {})
                self.calls["rest_not_modified"] += 1
                return cached["data"], "not_modified"
            self._raise_for(err, path)
        except (URLError, TimeoutError, ValueError) as err:
            raise RuntimeError("GitHub API unavailable for " + path) from err

    def graphql(self, query, variables, what="graphql"):
        if not self.token:
            raise RuntimeError("GraphQL needs a token (GITHUB_TOKEN); enrichment skipped")
        body = json.dumps({"query": query, "variables": variables}).encode("utf-8")
        self.calls["graphql"] += 1
        self.log.append({"kind": "graphql", "what": what, "outcome": "sent"})
        req = Request(API + "/graphql", data=body, method="POST",
                      headers=self._headers({"Content-Type": "application/json"}))
        try:
            with urlopen(req, timeout=20) as resp:
                self._note_rate(resp.headers)
                payload = json.load(resp)
        except HTTPError as err:
            self._raise_for(err, "graphql")
        except (URLError, TimeoutError, ValueError) as err:
            raise RuntimeError("GitHub GraphQL unavailable") from err
        rate = (payload.get("data") or {}).get("rateLimit") or {}
        if "remaining" in rate:
            self.rate["graphql"] = {"remaining": int(rate["remaining"]), "reset_at": str(rate.get("resetAt", ""))}
        errors = payload.get("errors") or []
        if any(str(e.get("type", "")).upper() == "RATE_LIMITED" for e in errors):
            raise RateLimited("GitHub GraphQL rate limit", str(rate.get("resetAt", "")))
        return payload.get("data") or {}, errors

    def prune(self, keep_max=400):
        """Drop ETags for URLs we no longer request, so the cache stays bounded."""
        stale = [u for u in self.etags if u not in self.used_urls]
        for url in stale:
            self.etags.pop(url, None)
        while len(self.etags) > keep_max:
            self.etags.pop(next(iter(self.etags)))


def compact_search(body):
    items = []
    for item in (body or {}).get("items", []):
        name = item.get("full_name", "")
        if not valid_repo(name):
            continue
        items.append({
            "id": item.get("id"), "repo": name,
            "stars": int(item.get("stargazers_count") or 0),
            "fork": bool(item.get("fork")), "archived": bool(item.get("archived")),
            "description": safe(item.get("description"), 200),
            "topics": [safe(t, 40) for t in (item.get("topics") or [])][:12],
            "pushed_at": str(item.get("pushed_at") or ""),
        })
    return {"items": items, "total": int((body or {}).get("total_count") or 0)}


GRAPHQL_FIELDS = """
  databaseId nameWithOwner url description isArchived isFork isMirror isSecurityPolicyEnabled
  securityPolicyUrl stargazerCount pushedAt
  licenseInfo { spdxId name }
  repositoryTopics(first: 12) { nodes { topic { name } } }
  latestRelease { tagName url publishedAt }
  releases { totalCount }
  defaultBranchRef { name target { ... on Commit { oid committedDate } } }
  issues(states: OPEN) { totalCount }
  recentIssues: issues(first: 5, states: OPEN, orderBy: {field: UPDATED_AT, direction: DESC}) {
    nodes { number title url updatedAt }
  }
  object(expression: "HEAD:") { ... on Tree { entries { name type } } }
  readme: object(expression: "HEAD:README.md") { ... on Blob { text } }
"""


def build_graphql(names):
    decls, parts, variables = [], [], {}
    for i, name in enumerate(names):
        owner, repo = name.split("/", 1)
        variables["o" + str(i)], variables["n" + str(i)] = owner, repo
        decls.append("$o%d: String!, $n%d: String!" % (i, i))
        parts.append("r%d: repository(owner: $o%d, name: $n%d) {%s}" % (i, i, i, GRAPHQL_FIELDS))
    query = "query(" + ", ".join(decls) + ") {\n rateLimit { cost remaining resetAt }\n" + "\n".join(parts) + "\n}"
    return query, variables


README_CHARS = 1500
TEST_DIRS = {"test", "tests", "__tests__", "spec", "specs", "testing", "e2e"}


def facts_from_graphql(node):
    """Flatten a GraphQL repository node into the facts the verdict uses."""
    if not node:
        return None
    entries = ((node.get("object") or {}).get("entries")) or []
    names = {str(e.get("name", "")).lower() for e in entries}
    head = ((node.get("defaultBranchRef") or {}).get("target")) or {}
    release = node.get("latestRelease") or {}
    lic = node.get("licenseInfo") or {}
    return {
        "id": node.get("databaseId"),
        "repo": node.get("nameWithOwner", ""),
        "url": node.get("url", ""),
        "description": safe(node.get("description"), 200),
        "topics": [safe(((t or {}).get("topic") or {}).get("name"), 40)
                   for t in ((node.get("repositoryTopics") or {}).get("nodes") or [])][:12],
        "archived": bool(node.get("isArchived")),
        "fork": bool(node.get("isFork")),
        "mirror": bool(node.get("isMirror")),
        "security_policy": bool(node.get("isSecurityPolicyEnabled")),
        "security_policy_url": str(node.get("securityPolicyUrl") or ""),
        "stars": int(node.get("stargazerCount") or 0),
        "license": str(lic.get("spdxId") or "NONE"),
        "branch": str((node.get("defaultBranchRef") or {}).get("name") or ""),
        "sha": str(head.get("oid") or ""),
        "last_commit": str(head.get("committedDate") or ""),
        "release": str(release.get("tagName") or ""),
        "release_url": str(release.get("url") or ""),
        "release_published": str(release.get("publishedAt") or ""),
        "releases": int((node.get("releases") or {}).get("totalCount") or 0),
        "open_issues": int((node.get("issues") or {}).get("totalCount") or 0),
        "recent_issues": [
            {"number": int(i.get("number") or 0), "title": safe(i.get("title"), 120),
             "url": str(i.get("url") or ""), "updated_at": str(i.get("updatedAt") or "")}
            for i in ((node.get("recentIssues") or {}).get("nodes") or [])
        ],
        "has_tests": bool(names & TEST_DIRS),
        "has_ci": ".github" in names or ".circleci" in names or ".gitlab-ci.yml" in names,
        # Used for scoring only; never stored or rendered.
        "readme_excerpt": safe((node.get("readme") or {}).get("text"), README_CHARS),
    }


# --------------------------------------------------------------------------- scoring

def blocker_fit(text, blockers):
    """Per-blocker fit 0..1 from distinct pattern hits.

    A blocker only counts when at least one of its "core" patterns matches, so
    generic words ("claude", "agents", "github") alone never route a repo.
    """
    out = {}
    lower = text.lower()
    for b in blockers:
        core = b.get("core") or []
        if core and not any(re.search(pat, lower) for pat in core):
            continue
        hits = sum(1 for pat in b.get("patterns", []) if re.search(pat, lower))
        if hits:
            out[b["id"]] = round(min(1.0, hits / 3.0), 2)
    return out


def maintenance_points(last_commit, now):
    when = parse_iso(last_commit)
    if when is None:
        return 0, None
    days = max(0, (now - when).days)
    for limit, points in ((30, 20), (90, 14), (180, 8), (365, 3)):
        if days <= limit:
            return points, days
    return 0, days


def license_points(spdx):
    code = str(spdx or "").upper()
    if code in PERMISSIVE:
        return 15, "permissive"
    if code.startswith(("GPL", "LGPL", "AGPL", "EUPL")):
        return 6, "copyleft"
    if code == "NOASSERTION":
        # A license file exists but GitHub could not classify it (dual or custom).
        return 0, "unclassified (read the LICENSE file)"
    return 0, "none"


def score(facts, blockers, now):
    text = " ".join([facts.get("repo", "").replace("/", " ").replace("-", " "),
                     facts.get("description", ""), " ".join(facts.get("topics", [])),
                     facts.get("readme_excerpt", "")])
    fits = blocker_fit(text, blockers)
    fit = round(50 * max(fits.values())) if fits else 0
    maintenance, days = maintenance_points(facts.get("last_commit"), now)
    lic, lic_kind = license_points(facts.get("license"))
    security = (5 if facts.get("security_policy") else 0) + (5 if facts.get("has_tests") else 0) \
        + (5 if facts.get("has_ci") else 0)
    return {"fit": fit, "maintenance": maintenance, "license": lic, "security": security,
            "total": fit + maintenance + lic + security}, fits, days, lic_kind


def load_reviews(folder):
    """Tested review records. Only these can say adopt."""
    reviews = {}
    if not folder.is_dir():
        return reviews
    for path in sorted(folder.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        repo, verdict = data.get("repo"), data.get("verdict")
        if valid_repo(repo) and verdict in VERDICTS and re.fullmatch(r"[0-9a-f]{40}", str(data.get("sha", ""))):
            data["_path"] = "findings/reviews/" + path.name
            reviews[repo.lower()] = data
    return reviews


def decide(facts, scores, fits, days, cfg, review):
    rules = cfg.get("verdict_rules", {})
    limits = cfg.get("limits", {})
    if review:
        # Exact SHA only: a release tag that has not moved says nothing about new commits on HEAD.
        if review.get("sha") == facts.get("sha"):
            return review["verdict"], "tested review " + review["_path"] + " (" + str(review.get("date", "")) + ")"
        if review["verdict"] == "reject":
            return "reject", "rejected by tested review at " + review["sha"][:7] + "; new version not re-reviewed"
        return "needs-test", "adopted at " + review["sha"][:7] + " but the repo moved to a new version; re-test before relying on it"
    if facts.get("archived"):
        return "reject", "archived upstream"
    if facts.get("fork") or facts.get("mirror"):
        return "reject", "fork or mirror; evaluate the upstream instead"
    if str(facts.get("license", "NONE")).upper() in {"NONE", ""}:
        return "reject", "no license: all rights reserved, ideas only, no code reuse"
    if days is None or days > int(limits.get("stale_days", 365)):
        return "reject", "no commit in over " + str(limits.get("stale_days", 365)) + " days"
    if not fits:
        return "reject", "no fit with a current Leon blocker"
    if scores["total"] < int(rules.get("needs_test_min_score", 45)):
        return "reject", "score " + str(scores["total"]) + " below needs-test threshold"
    if scores["license"] == 0:
        return "needs-test", "license file present but unclassified by GitHub; read it before any reuse"
    return "needs-test", "metadata looks viable; needs a pinned, isolated test before any reuse"


def evidence_links(facts):
    url = facts.get("url") or "https://github.com/" + facts.get("repo", "")
    links = [url]
    if facts.get("sha"):
        links.append(url + "/tree/" + facts["sha"])
        if facts.get("license") not in {"NONE", "NOASSERTION", ""}:
            links.append(url + "/blob/" + facts["sha"] + "/LICENSE")
    if facts.get("release_url"):
        links.append(facts["release_url"])
    if facts.get("security_policy_url") and facts.get("security_policy"):
        links.append(facts["security_policy_url"])
    return links


def task_line(facts, blocker_label, sha):
    return ("Pin " + facts["repo"] + "@" + sha[:7] + ", read its " + facts.get("license", "?")
            + " license and source, run its tests or a minimal proof in an isolated scratch dir (no installs on the Mac), "
            "and record adopt/reject for: " + blocker_label + ".")


def build_record(facts, cfg, now, review, prior, topic, carried=None):
    blockers = cfg.get("blockers", [])
    scores, fits, days, lic_kind = score(facts, blockers, now)
    verdict, reason = decide(facts, scores, fits, days, cfg, review)
    # A carried-forward candidate may hold a manual, read-only verdict. It can only say
    # needs-test or reject (adopt needs a tested review), and hard facts still win.
    if (carried and not review and carried.get("verdict") in {"needs-test", "reject"}
            and not facts.get("archived") and str(facts.get("license", "NONE")).upper() not in {"NONE", ""}
            and not (facts.get("fork") or facts.get("mirror"))):
        verdict, reason = carried["verdict"], safe(carried.get("reason", "manual assessment"), 400)
    by_id = {b["id"]: b for b in blockers}
    ranked = sorted(fits.items(), key=lambda kv: (-kv[1], kv[0]))
    best = by_id.get(ranked[0][0]) if ranked else None
    audited = cfg.get("audited_elsewhere", {}).get(facts["repo"])
    owner = best["owner"] if best and best.get("owner") in OWNERS else "hub"
    if carried and carried.get("owner") in OWNERS:
        owner = carried["owner"]
    routed = (verdict == "needs-test" and not audited and (best is not None or bool(carried))
              and (scores["total"] >= int(cfg.get("verdict_rules", {}).get("route_min_score", 60))
                   or bool(carried)))
    record = {
        "schema": SCHEMA,
        "repo": facts["repo"],
        "repo_id": facts.get("id"),
        "url": facts.get("url") or "https://github.com/" + facts["repo"],
        "version": facts.get("release") or "head",
        "sha": facts.get("sha", ""),
        "license": facts.get("license", "NONE"),
        "license_kind": lic_kind,
        "topic": topic,
        "scores": scores,
        "blockers": [{"id": k, "fit": v} for k, v in ranked],
        "verdict": verdict,
        "verdict_reason": reason,
        "suggested_owner": owner if (routed or verdict == "adopt" or (carried and carried.get("owner") in OWNERS)) else None,
        "task": task_line(facts, best["label"] if best else "carried-forward HQ candidate", facts.get("sha", "")) if routed else None,
        "provenance": ({"carried_forward": carried.get("name"), "note": carried.get("note", ""),
                        "assessment": carried.get("assessment")} if carried else None),
        "audited_elsewhere": audited or None,
        "signals": {
            "stars": facts.get("stars", 0), "open_issues": facts.get("open_issues", 0),
            "last_commit": facts.get("last_commit", ""), "days_since_commit": days,
            "releases": facts.get("releases", 0), "archived": facts.get("archived", False),
            "security_policy": facts.get("security_policy", False),
            "has_tests": facts.get("has_tests", False), "has_ci": facts.get("has_ci", False),
        },
        "recent_issues": facts.get("recent_issues", [])[:3],
        "evidence": evidence_links(facts) + ([("https://github.com/Leonwei-cyb/roblox-research-scout/blob/main/"
                                                + review["_path"])] if review else []),
        "first_seen": (prior or {}).get("first_seen") or iso(now),
        "last_checked": iso(now),
    }
    return record


# --------------------------------------------------------------------------- store

def load_candidates(path):
    rows = []
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                try:
                    rows.append(json.loads(line))
                except ValueError:
                    continue
    return rows


def canonical_key(record):
    """(repo identity, version). GitHub's numeric id survives renames and transfers."""
    ident = record.get("repo_id") or str(record.get("repo", "")).lower()
    return str(ident), str(record.get("version") or "head")


def merge_candidates(existing, fresh, limits):
    store = {}
    for row in existing:
        store[canonical_key(row)] = row
    renamed = {}
    for row in fresh:
        key = canonical_key(row)
        # Drop a legacy name-keyed duplicate once the numeric id is known.
        legacy = (str(row.get("repo", "")).lower(), key[1])
        if legacy in store and legacy != key:
            prior = store.pop(legacy)
            row["first_seen"] = min(row["first_seen"], prior.get("first_seen", row["first_seen"]))
        prior = store.get(key)
        if prior:
            row["first_seen"] = min(row["first_seen"], prior.get("first_seen", row["first_seen"]))
        store[key] = row
        renamed[key[0]] = row["repo"]
    # Keep the newest name for every version of a renamed repo.
    for key, row in store.items():
        if key[0] in renamed:
            row["repo"] = renamed[key[0]]
    per_repo = {}
    for key, row in sorted(store.items(), key=lambda kv: kv[1].get("last_checked", ""), reverse=True):
        per_repo.setdefault(key[0], []).append(key)
    max_versions = int(limits.get("max_versions_per_repo", 3))
    keep = {k for keys in per_repo.values() for k in keys[:max_versions]}
    rows = [row for key, row in store.items() if key in keep]
    rows.sort(key=lambda r: (VERDICTS.index(r.get("verdict", "reject")) if r.get("verdict") in VERDICTS else 9,
                             -int((r.get("scores") or {}).get("total", 0)), str(r.get("repo", "")).lower(),
                             str(r.get("version", ""))))
    return rows[: int(limits.get("max_candidates_stored", 600))]


def latest_per_repo(rows):
    """The most recently checked version of each repo: the one that counts today."""
    best = {}
    for row in rows:
        ident = canonical_key(row)[0]
        if ident not in best or row.get("last_checked", "") > best[ident].get("last_checked", ""):
            best[ident] = row
    return list(best.values())


# --------------------------------------------------------------------------- query packs

def compact_tree(body):
    """Keep only what the inspection reads, so the ETag cache stays small."""
    entries = [{"path": str(e.get("path", "")), "size": int(e.get("size") or 0)}
               for e in (body or {}).get("tree", []) if e.get("type") == "blob"]
    manifests, tests, sources = packs.pick_files(entries)
    readme = [e["path"] for e in entries if re.fullmatch(r"readme(\.[a-z]+)?", e["path"], re.I)][:1]
    return {"readme": readme, "manifests": manifests, "sources": sources, "tests": len(tests),
            "tests_sample": tests[:5], "truncated": bool((body or {}).get("truncated"))}


def build_blob_query(wanted):
    """wanted: [(repo, sha, [paths])]. Paths travel as variables, never inside the query text."""
    decls, parts, variables = [], [], {}
    for i, (repo, sha, paths) in enumerate(wanted):
        owner, name = repo.split("/", 1)
        variables["o%d" % i], variables["n%d" % i] = owner, name
        decls.append("$o%d: String!, $n%d: String!" % (i, i))
        fields = []
        for j, path in enumerate(paths):
            key = "e%d_%d" % (i, j)
            variables[key] = sha + ":" + path
            decls.append("$" + key + ": String!")
            fields.append("f%d: object(expression: $%s) { ... on Blob { text byteSize isBinary } }" % (j, key))
        parts.append("r%d: repository(owner: $o%d, name: $n%d) { %s }" % (i, i, i, " ".join(fields)))
    return "query(" + ", ".join(decls) + ") {\n rateLimit { cost remaining resetAt }\n" + "\n".join(parts) + "\n}", variables


def inspect_sources(gh, records, limits):
    """Tree + README + manifests + key source for each record. Returns {repo_lower: inspection}."""
    out, wanted = {}, []
    for rec in records:
        if not rec.get("sha"):
            continue
        owner, name = rec["repo"].split("/", 1)
        if not gh.budget_ok("core", int(limits.get("min_rest_remaining", 120))):
            out[rec["repo"].lower()] = {"error": "core budget low"}
            continue
        try:
            tree, _ = gh.get("/repos/" + quote(owner) + "/" + quote(name) + "/git/trees/" + rec["sha"],
                             {"recursive": "1"}, compact_tree)
        except RateLimited:
            raise
        except RuntimeError as exc:
            out[rec["repo"].lower()] = {"error": safe(exc, 120)}
            continue
        paths = tree["readme"] + tree["manifests"] + tree["sources"]
        out[rec["repo"].lower()] = {"tests": tree["tests"], "tests_sample": tree["tests_sample"], "files": paths,
                                    "tree_truncated": tree["truncated"], "texts": {}}
        if paths:
            wanted.append((rec["repo"], rec["sha"], paths))
    per = int(limits.get("blob_batch_repos", 6))
    for b in range(0, len(wanted), per):
        chunk = wanted[b:b + per]
        if not gh.budget_ok("graphql", int(limits.get("min_graphql_remaining", 150))):
            for repo, _sha, _paths in chunk:
                out[repo.lower()]["error"] = "graphql budget low"
            continue
        query, variables = build_blob_query(chunk)
        data, _errors = gh.graphql(query, variables, what="graphql: source files of " + str(len(chunk)) + " repos")
        for i, (repo, _sha, paths) in enumerate(chunk):
            node = data.get("r%d" % i) or {}
            for j, path in enumerate(paths):
                blob = node.get("f%d" % j) or {}
                if blob.get("text") and not blob.get("isBinary"):
                    out[repo.lower()]["texts"][path] = str(blob["text"])[: packs.MAX_TEXT]
    return out


def apply_pack(pack, hits, fresh, gh, cfg, limits, reviews, now, event):
    """Inspect, classify, rank and verdict one pack's shortlist; annotate records; return the report."""
    shortlist = packs.shortlist(hits, int(pack.get("inspect_top", 12)))
    by_repo = {r["repo"].lower(): r for r in fresh}
    chosen = [by_repo[h["repo"].lower()] for h in shortlist if h["repo"].lower() in by_repo]
    inspections = inspect_sources(gh, chosen, limits)
    audited = cfg.get("audited_elsewhere", {})
    candidates = []
    for h in shortlist:
        rec = by_repo.get(h["repo"].lower())
        if not rec:
            continue
        ins = inspections.get(rec["repo"].lower(), {"error": "not inspected"})
        mode, browser, api = packs.classify(ins.get("texts", {})) if not ins.get("error") else ("unknown", [], [])
        review = reviews.get(rec["repo"].lower())
        review_ok = review and review.get("sha") == rec["sha"]
        verdict, reason = packs.pack_verdict(rec, mode, review["verdict"] if review_ok else None)
        score = packs.rank_score(h, rec, mode, browser, ins.get("tests", 0))
        owner = pack.get("owner", "Wheel") if pack.get("owner") in OWNERS else "Wheel"
        entry = {
            "repo": rec["repo"], "url": rec["url"], "sha": rec["sha"], "version": rec["version"],
            "license": rec["license"], "days_since_commit": rec["signals"]["days_since_commit"],
            "stars": rec["signals"]["stars"], "found_by": sorted(h["hits"]), "search_rank": h["best_rank"],
            "mode": mode, "browser_evidence": browser, "api_evidence": api,
            "files_inspected": sorted(ins.get("texts", {}).keys()), "tests_found": int(ins.get("tests", 0)),
            "inspection_error": ins.get("error"),
            "pack_verdict": verdict, "pack_reason": reason, "rank_score": score,
            "audited_elsewhere": audited.get(rec["repo"]),
            "suggested_owner": owner if verdict == "needs-test" else None,
            "evidence": [rec["url"] + "/tree/" + rec["sha"]] + [rec["url"] + "/blob/" + rec["sha"] + "/" + quote(f)
                                                                  for f in sorted(ins.get("texts", {}).keys())[:4]],
        }
        candidates.append(entry)
        rec.setdefault("packs", {})[pack["id"]] = {k: entry[k] for k in (
            "mode", "pack_verdict", "pack_reason", "rank_score", "found_by", "browser_evidence", "api_evidence")}
        if verdict == "needs-test" and rec["verdict"] == "reject" and rec["verdict_reason"].startswith(("no fit", "score")):
            rec["verdict"], rec["verdict_reason"] = "needs-test", "query pack " + pack["id"] + ": " + reason
        if verdict == "needs-test" and not entry["audited_elsewhere"] and not rec.get("task"):
            rec["suggested_owner"] = owner
            rec["task"] = ("Pin " + rec["repo"] + "@" + rec["sha"][:7] + ", read its " + rec["license"]
                           + " license and the inspected files, then run one isolated source-level reuse test against "
                           + pack.get("label", pack["id"]) + " (no installs, no live sessions) and record adopt/reject.")
    candidates.sort(key=lambda c: (-c["rank_score"], c["repo"].lower()))
    rank_of = {c["repo"].lower(): i for i, c in enumerate(candidates, 1)}
    known = []
    for name in pack.get("known_relevant", []):
        h = hits.get(name.lower())
        known.append({"repo": name, "found_by": sorted(h["hits"]) if h else [], "rank": rank_of.get(name.lower())})
    by_kind = {}
    for call in gh.log:
        by_kind[call["kind"]] = by_kind.get(call["kind"], 0) + 1
    return {
        "schema": SCHEMA, "pack": pack["id"], "label": pack.get("label", pack["id"]), "run_at": iso(now),
        "trigger": event, "per_page": int(pack.get("per_page", 15)),
        "queries": [{"id": qid, "form": form, "words": words} for qid, form, words in packs.pack_queries(pack)],
        "distinct_repos_found": len(hits), "candidates": candidates, "known_relevant": known,
        "coverage_note": "GitHub search relevance, one page per query; not full GitHub coverage.",
    }


# --------------------------------------------------------------------------- run

def run(now=None, token=None, requests_text=None, event="local", run_url=""):
    fixed_clock = now is not None
    now = now or utcnow()
    cfg = read_json(CONFIG, {})
    limits = cfg.get("limits", {})
    state = read_json(STATE, {})
    gh = GitHub(token if token is not None else os.environ.get("GITHUB_TOKEN", ""),
                dict(state.get("etags", {})), limits, now)
    feeds, events = [], []
    started = iso(now)
    outcome = "ok"
    deferred_until = parse_iso(state.get("deferred_until"))
    rate_stop = None
    if deferred_until and deferred_until > now:
        rate_stop = "rate limit backoff until " + iso(deferred_until)

    # 1. Search, bounded.
    pool = {}   # repo (lower) -> (name, topic, search item)
    queries = [(t["id"], q) for t in cfg.get("topics", []) for q in t.get("queries", [])]
    queries = queries[: int(limits.get("max_search_queries", 14))]
    pushed_since = (now - timedelta(days=int(limits.get("pushed_within_days", 120)))).date().isoformat()
    for n, (topic, query) in enumerate(queries):
        feed_id = "search:" + topic + ":" + str(n)
        if rate_stop or not gh.budget_ok("search", 2):
            feeds.append({"id": feed_id, "kind": "search", "status": "deferred",
                          "detail": rate_stop or "search budget low"})
            continue
        q = query + " stars:>=" + str(int(limits.get("min_stars", 15))) + " pushed:>=" + pushed_since + " archived:false"
        try:
            data, status = gh.get("/search/repositories",
                                  {"q": q, "sort": "updated", "order": "desc",
                                   "per_page": int(limits.get("per_page", 20)), "page": 1}, compact_search)
        except RateLimited as exc:
            rate_stop = str(exc)
            if exc.reset_at:
                state["deferred_until"] = exc.reset_at
            feeds.append({"id": feed_id, "kind": "search", "status": "deferred", "detail": rate_stop})
            continue
        except RuntimeError as exc:
            feeds.append({"id": feed_id, "kind": "search", "status": "error", "detail": safe(exc, 120)})
            continue
        feeds.append({"id": feed_id, "kind": "search", "status": status, "items": len(data["items"])})
        for item in data["items"]:
            if item["fork"] or item["archived"]:
                continue
            pool.setdefault(item["repo"].lower(), (item["repo"], topic, item))

    # 1b. Problem-first query packs (bounded; see discovery_packs.py).
    pack_hits = {}
    for pack in cfg.get("query_packs", []):
        if rate_stop:
            feeds.append({"id": "pack:" + pack["id"], "kind": "search", "status": "deferred", "detail": rate_stop})
            continue
        hits, pfeeds, limited = packs.search(gh, pack, now, compact_search, RateLimited, safe)
        feeds.extend(pfeeds)
        pack_hits[pack["id"]] = hits
        if limited:
            rate_stop = str(limited)
            if getattr(limited, "reset_at", ""):
                state["deferred_until"] = limited.reset_at

    # 2. Decide what to enrich: watched repos and requests first, then new search hits.
    prior_rows = load_candidates(CANDIDATES)
    prior_latest = {str(r.get("repo", "")).lower(): r for r in latest_per_repo(prior_rows)}
    known = set(prior_latest)
    targets, topic_of = [], {}
    requested = parse_requests(requests_text if requests_text is not None else os.environ.get("DISCOVERY_REQUESTS", ""))
    carried_by_repo = {c["repo"].lower(): c for c in cfg.get("carried_forward", [])
                       if isinstance(c, dict) and valid_repo(c.get("repo"))}
    carried_names = [c["repo"] for c in carried_by_repo.values()]
    for name in requested + carried_names + [n for n in cfg.get("watch_repos", []) if valid_repo(n)]:
        if name.lower() not in {t.lower() for t in targets}:
            targets.append(name)
            topic_of[name.lower()] = ("requested" if name in requested else
                                      "carried-forward" if name.lower() in carried_by_repo else "watchlist")
    for pack in cfg.get("query_packs", []):
        for h in packs.shortlist(pack_hits.get(pack["id"], {}), int(pack.get("inspect_top", 12))):
            if h["repo"].lower() not in {t.lower() for t in targets}:
                targets.append(h["repo"])
                topic_of[h["repo"].lower()] = "pack:" + pack["id"]
    fresh_hits = sorted((v for k, v in pool.items() if k not in known and k not in topic_of),
                        key=lambda v: (-v[2]["stars"], v[0].lower()))
    for name, topic, _item in fresh_hits[: int(limits.get("max_new_candidates_per_run", 25))]:
        targets.append(name)
        topic_of[name.lower()] = topic
    # Re-check previously routed / adopted repos so releases and issues are monitored.
    for key, row in sorted(prior_latest.items()):
        if row.get("verdict") in {"adopt", "needs-test"} and key not in topic_of:
            targets.append(row["repo"])
            topic_of[key] = row.get("topic", "monitor")
    batch = int(limits.get("graphql_batch_size", 15))
    max_batches = int(limits.get("max_graphql_batches", 4))
    targets = targets[: batch * max_batches]

    reviews = load_reviews(REVIEWS)
    fresh = []
    seen_ids = set()
    for b in range(0, len(targets), batch):
        names = targets[b:b + batch]
        feed_id = "graphql:batch" + str(b // batch)
        if rate_stop or not gh.budget_ok("graphql", int(limits.get("min_graphql_remaining", 150))):
            feeds.append({"id": feed_id, "kind": "graphql", "status": "deferred",
                          "detail": rate_stop or "graphql budget low", "repos": len(names)})
            continue
        query, variables = build_graphql(names)
        try:
            data, errors = gh.graphql(query, variables)
        except RateLimited as exc:
            rate_stop = str(exc)
            if exc.reset_at:
                state["deferred_until"] = exc.reset_at
            feeds.append({"id": feed_id, "kind": "graphql", "status": "deferred", "detail": rate_stop, "repos": len(names)})
            continue
        except RuntimeError as exc:
            feeds.append({"id": feed_id, "kind": "graphql", "status": "error", "detail": safe(exc, 120), "repos": len(names)})
            continue
        missing = 0
        for i, name in enumerate(names):
            facts = facts_from_graphql(data.get("r" + str(i)))
            if not facts or not facts.get("repo"):
                missing += 1
                continue
            if facts["id"] in seen_ids:
                continue          # same repo reached under an old and a new name
            seen_ids.add(facts["id"])
            prior = prior_latest.get(facts["repo"].lower()) or prior_latest.get(name.lower())
            topic = topic_of.get(name.lower(), "search")
            record = build_record(facts, cfg, now, reviews.get(facts["repo"].lower()), prior, topic,
                                  carried_by_repo.get(facts["repo"].lower()) or carried_by_repo.get(name.lower()))
            if prior:
                if prior.get("version") != record["version"] and record["version"] != "head":
                    events.append({"type": "release", "repo": record["repo"], "from": prior.get("version"),
                                   "to": record["version"], "url": facts.get("release_url", "")})
                since = prior.get("last_checked", "")
                for issue in facts.get("recent_issues", []):
                    if issue["updated_at"] > since:
                        events.append({"type": "issue", "repo": record["repo"], "number": issue["number"],
                                       "title": issue["title"], "url": issue["url"]})
            else:
                events.append({"type": "new_candidate", "repo": record["repo"], "verdict": record["verdict"]})
            fresh.append(record)
        status = "ok" if not errors or missing < len(names) else "error"
        entry = {"id": feed_id, "kind": "graphql", "status": status, "repos": len(names), "resolved": len(names) - missing}
        if missing:
            entry["detail"] = str(missing) + " repo(s) not found or not visible"
        feeds.append(entry)

    pack_reports = []
    for pack in cfg.get("query_packs", []):
        if pack["id"] not in pack_hits:
            continue
        try:
            pack_reports.append(apply_pack(pack, pack_hits[pack["id"]], fresh, gh, cfg, limits, reviews, now, event))
            feeds.append({"id": "pack-inspect:" + pack["id"], "kind": "inspect", "status": "ok"})
        except RateLimited as exc:
            rate_stop = str(exc)
            if exc.reset_at:
                state["deferred_until"] = exc.reset_at
            feeds.append({"id": "pack-inspect:" + pack["id"], "kind": "inspect", "status": "deferred", "detail": rate_stop})
        except RuntimeError as exc:
            feeds.append({"id": "pack-inspect:" + pack["id"], "kind": "inspect", "status": "error", "detail": safe(exc, 120)})

    rows = merge_candidates(prior_rows, fresh, limits)
    if any(f["status"] in {"error", "deferred"} for f in feeds):
        outcome = "partial"
    if feeds and all(f["status"] in {"error", "deferred"} for f in feeds):
        outcome = "failed"
    if not rate_stop and state.get("deferred_until") and (parse_iso(state["deferred_until"]) or now) <= now:
        state.pop("deferred_until", None)

    gh.prune()
    finished = now if fixed_clock else utcnow()
    status = build_status(rows, feeds, events, gh, cfg, started, iso(finished), outcome, event, run_url)
    text = "".join(json.dumps(r, sort_keys=True, ensure_ascii=False) + "\n" for r in rows)
    write_if_changed(CANDIDATES, text)
    write_if_changed(SUMMARY, render_summary(rows, events, status))
    write_if_changed(STATUS, json.dumps(status, indent=2, sort_keys=True) + "\n")
    for report in pack_reports:
        report["searches"] = [f for f in feeds if f["id"].startswith("pack:" + report["pack"] + ":")]
        report["api_calls"] = {"total": len(gh.log), "by_kind": {}, "calls": gh.log,
                               "note": "every GitHub request this run made, pack and non-pack"}
        for call in gh.log:
            report["api_calls"]["by_kind"][call["kind"]] = report["api_calls"]["by_kind"].get(call["kind"], 0) + 1
        write_if_changed(PACKS / (report["pack"] + ".json"), json.dumps(report, indent=2, sort_keys=True) + "\n")
        write_if_changed(PACKS / (report["pack"] + ".md"), packs.render(report, md))
    state.update({"etags": gh.etags, "last_run": iso(finished)})
    write_if_changed(STATE, json.dumps(state, indent=2, sort_keys=True) + "\n")
    print("Discovery " + outcome + ": " + str(len(fresh)) + " repos checked, " + str(len(rows))
          + " stored, " + str(status["counts"]["actionable_backlog"]) + " actionable, "
          + str(gh.calls["rest"]) + " REST (" + str(gh.calls["rest_not_modified"]) + " not modified), "
          + str(gh.calls["graphql"]) + " GraphQL")
    return status


def backlog(rows, limit):
    items = [r for r in latest_per_repo(rows) if r.get("task") and r.get("verdict") == "needs-test"]
    items.sort(key=lambda r: (-int(r["scores"]["total"]), r["repo"].lower()))
    return items[:limit]


def build_status(rows, feeds, events, gh, cfg, started, finished, outcome, event, run_url):
    limits = cfg.get("limits", {})
    current = latest_per_repo(rows)
    counts = {v: sum(1 for r in current if r.get("verdict") == v) for v in VERDICTS}
    queue = backlog(rows, int(limits.get("max_backlog", 12)))
    health = {}
    for f in feeds:
        health[f["status"]] = health.get(f["status"], 0) + 1
    return {
        "schema": SCHEMA,
        "last_run": {"started_at": started, "finished_at": finished, "trigger": event,
                     "outcome": outcome, "run_url": run_url},
        "freshness": {
            "stale_after_hours": int(limits.get("stale_after_hours", 13)),
            "schedule": "every 6 hours (best-effort GitHub cron) plus push, manual, repository_dispatch and labelled-issue triggers",
            "continuous": False,
            "note": "Polling snapshots only. Third-party repos cannot push events to us, so releases/issues are seen at the next run.",
        },
        "feeds": feeds,
        "feed_health": health,
        "api": {"calls": gh.calls, "rate": gh.rate},
        "counts": {
            "repos_tracked": len(current), "records": len(rows),
            "adopt": counts["adopt"], "needs_test": counts["needs-test"], "reject": counts["reject"],
            "actionable_backlog": len(backlog(rows, 10 ** 6)),
            "events_this_run": len(events),
            "new_candidates_this_run": sum(1 for e in events if e["type"] == "new_candidate"),
            "new_releases_this_run": sum(1 for e in events if e["type"] == "release"),
            "updated_issues_this_run": sum(1 for e in events if e["type"] == "issue"),
        },
        "adopted": [{"repo": r["repo"], "version": r["version"], "sha": r["sha"],
                     "evidence": r["evidence"][-1]} for r in current if r.get("verdict") == "adopt"],
        "backlog": [{"repo": r["repo"], "sha": r["sha"], "score": r["scores"]["total"],
                     "suggested_owner": r["suggested_owner"], "task": r["task"]} for r in queue],
    }


def render_summary(rows, events, status):
    c = status["counts"]
    run = status["last_run"]
    lines = ["# Open-source discovery: summary", "",
             "Automated GitHub metadata scoring, not an endorsement. Nothing listed here was installed or run by the bot.",
             "Only a tested review in [findings/reviews](reviews/) can mark something **adopt**.", "",
             "- Last run: " + run["finished_at"] + " (" + run["trigger"] + ", " + run["outcome"] + ")",
             "- Repos tracked: " + str(c["repos_tracked"]) + "; adopt " + str(c["adopt"]) + ", needs-test "
             + str(c["needs_test"]) + ", reject " + str(c["reject"]),
             "- Actionable backlog: " + str(c["actionable_backlog"]),
             "- Feed health: " + ", ".join(k + " " + str(v) for k, v in sorted(status["feed_health"].items())),
             "- Coverage: polling snapshots every few hours, **not** continuous.", ""]
    adopted = [r for r in latest_per_repo(rows) if r.get("verdict") == "adopt"]
    if adopted:
        lines += ["## Adopted (tested)", ""]
        for r in adopted:
            lines.append("- [" + md(r["repo"]) + "](" + r["url"] + ") @ " + r["sha"][:7] + " (" + md(r["license"])
                         + "): " + md(r["verdict_reason"], 140))
        lines.append("")
    queue = status["backlog"]
    lines += ["## Actionable backlog (bounded candidate tasks)", ""]
    if not queue:
        lines.append("Nothing above the routing threshold right now.")
    for item in queue:
        lines.append("- **" + md(item["suggested_owner"]) + "** · score " + str(item["score"]) + " · ["
                     + md(item["repo"]) + "](https://github.com/" + item["repo"] + "/tree/" + item["sha"] + ")")
        lines.append("  - " + md(item["task"], 400))
    lines.append("")
    if events:
        lines += ["## Changes this run", ""]
        for e in events[:30]:
            if e["type"] == "release":
                lines.append("- Release: " + md(e["repo"]) + " " + md(e.get("from")) + " to " + md(e.get("to")))
            elif e["type"] == "issue":
                lines.append("- Issue updated: " + md(e["repo"]) + " #" + str(e["number"]) + " " + md(e["title"], 100))
            else:
                lines.append("- New candidate: " + md(e["repo"]) + " (" + e["verdict"] + ")")
        lines.append("")
    lines += ["Machine-readable: [candidates.jsonl](candidates.jsonl), [status/discovery.json](../status/discovery.json).", ""]
    return "\n".join(lines)


def main():
    event = os.environ.get("GITHUB_EVENT_NAME", "local")
    run_url = ""
    if os.environ.get("GITHUB_RUN_ID") and os.environ.get("GITHUB_REPOSITORY"):
        run_url = (os.environ.get("GITHUB_SERVER_URL", "https://github.com") + "/"
                   + os.environ["GITHUB_REPOSITORY"] + "/actions/runs/" + os.environ["GITHUB_RUN_ID"])
    status = run(event=event, run_url=run_url)
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as out:
            out.write("### Open-source discovery\n\n- Outcome: " + status["last_run"]["outcome"]
                      + "\n- Actionable backlog: " + str(status["counts"]["actionable_backlog"])
                      + "\n- Feed health: " + json.dumps(status["feed_health"], sort_keys=True) + "\n")
    # A partial run still saved what it learned; only a run where every feed failed is red.
    return 1 if status["last_run"]["outcome"] == "failed" else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print("Discovery scout failed: " + str(exc), file=sys.stderr)
        sys.exit(1)
