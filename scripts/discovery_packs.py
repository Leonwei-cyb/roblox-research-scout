#!/usr/bin/env python3
"""Problem-first query packs for discovery_scout.py.

A pack is a list of problem statements ("persistent ChatGPT browser-session
workers") rather than product names. For each pack this module:
1. runs each statement as a bounded GitHub repository search (strict wording,
   plus a relaxed form that only drops words from the same statement);
2. reads, for the best-ranked hits only, the file tree at the pinned head SHA,
   the README, manifests (package.json, manifest.json, pyproject.toml,
   requirements.txt), test files and a few key source files;
3. classifies each one as real browser-session orchestration, API-only
   multi-agent, mixed, or unknown, with the evidence lines that decided it;
4. ranks them and gives a pack verdict (needs-test / reject; adopt only via a
   tested review), then writes findings/packs/<pack>.json and .md with every
   API call that was made.

Nothing is cloned, installed or executed. Known-relevant repos listed in the
config are used ONLY to report whether the search rediscovered them; they are
never added to the search or to the inspected set.
"""
from __future__ import annotations

import json
import re
from datetime import timedelta
from pathlib import PurePosixPath

MANIFEST_NAMES = {"package.json", "manifest.json", "pyproject.toml", "requirements.txt", "setup.py", "cargo.toml", "go.mod"}
SKIP_DIRS = ("node_modules/", "vendor/", "dist/", "build/", ".git/", "third_party/")
KEY_SOURCE = re.compile(r"(browser|session|tab|content|background|service.?worker|worker|queue|dispatch|adapter|"
                        r"conversation|pane|agent|orchestr)", re.I)
SOURCE_EXT = {".js", ".mjs", ".cjs", ".ts", ".tsx", ".py", ".go", ".rs"}
TEST_PATH = re.compile(r"(^|/)(tests?|__tests__|spec|specs|e2e)(/|$)|\.(test|spec)\.[a-z]+$|(^|/)test_[^/]+\.py$", re.I)
MAX_BLOB_BYTES = 150_000
MAX_TEXT = 20_000

CHAT_SITES = re.compile(r"chatgpt\.com|chat\.openai\.com|claude\.ai|gemini\.google\.com|grok\.com|x\.com/i/grok", re.I)
BROWSER_DEPS = re.compile(r'"(playwright(-core)?|puppeteer(-core)?|selenium-webdriver|chrome-remote-interface|'
                          r'@playwright/test|webextension-polyfill)"|^\s*(playwright|selenium|undetected[-_]chromedriver|'
                          r'pyppeteer|nodriver|browser-use)\b', re.I | re.M)
API_DEPS = re.compile(r'"(openai|@anthropic-ai/sdk|@google/generative-ai|langchain|@langchain/[a-z-]+|crewai|'
                      r'autogen|litellm|ai|@ai-sdk/[a-z-]+)"\s*:|^\s*(openai|anthropic|langchain[a-z_-]*|crewai|'
                      r'pyautogen|autogen[a-z_-]*|litellm|google-generativeai)\b', re.I | re.M)
BROWSER_TEXT = [
    ("content scripts on chat sites", re.compile(r'"content_scripts"', re.I)),
    ("extension host permissions", re.compile(r'"host_permissions"|"permissions"\s*:\s*\[[^\]]*"(tabs|scripting|sidePanel)"', re.I)),
    ("persistent browser profile", re.compile(r"launchPersistentContext|userDataDir|user[-_]data[-_]dir|storageState|persistent (browser )?(context|profile)", re.I)),
    ("chrome tabs/scripting API", re.compile(r"chrome\.(tabs|scripting|sidePanel|debugger)\b", re.I)),
    ("drives the chat page DOM", re.compile(r"(querySelector|getByRole|locator)\([^)]*(prompt|textarea|send|composer|conversation)", re.I)),
    ("authenticated web session wording", re.compile(r"(authenticated|logged.in|existing|your own) (browser )?sessions?|browser.session|without (an )?api key|no api key", re.I)),
]
API_TEXT = [
    ("calls a model API endpoint", re.compile(r"api\.openai\.com|api\.anthropic\.com|generativelanguage\.googleapis\.com", re.I)),
    ("needs a model API key", re.compile(r"OPENAI_API_KEY|ANTHROPIC_API_KEY|GEMINI_API_KEY|GOOGLE_API_KEY|api[_ ]key", re.I)),
    ("model SDK client", re.compile(r"new OpenAI\(|OpenAI\(\s*api_key|ChatOpenAI\(|Anthropic\(\s*\)|from openai import|import anthropic", re.I)),
]
NO_KEY = re.compile(r"\b(no|without|never (needs?|uses?)|(do|does|did)n'?t (require|need)|(do|does) not (require|need)|"
                    r"not (require|need)(ed)?|no need for)\b(\s+[\w-]+){0,3}?\s+api[_ ]keys?", re.I)
MODE_POINTS = {"browser-session": 40, "mixed": 30, "unknown": 5, "api-only": 0}


def pack_queries(pack):
    """Strict = the problem statement verbatim; relaxed = a subset of its own words."""
    out = []
    for q in pack.get("queries", []):
        out.append((q["id"], "strict", q["q"]))
        if q.get("relaxed"):
            words = set(q["q"].lower().split())
            if not set(q["relaxed"].lower().split()) <= words:
                raise ValueError("relaxed query must only drop words from its statement: " + q["id"])
            out.append((q["id"], "relaxed", q["relaxed"]))
    return out


def search(gh, pack, now, compact, rate_limited, safe):
    """Run the pack's searches. Returns (hits, feeds, rate_stop)."""
    hits, feeds = {}, []
    since = (now - timedelta(days=int(pack.get("pushed_within_days", 365)))).date().isoformat()
    scope = pack.get("search_in", "in:name,description,topics,readme")
    for n, (qid, form, words) in enumerate(pack_queries(pack)[: int(pack.get("max_queries", 14))]):
        feed_id = "pack:" + pack["id"] + ":" + qid + ":" + form
        if not gh.budget_ok("search", 2):
            feeds.append({"id": feed_id, "kind": "search", "status": "deferred", "detail": "search budget low"})
            continue
        q = words + " " + scope + " pushed:>=" + since + " archived:false"
        if int(pack.get("min_stars", 0)) > 0:
            q += " stars:>=" + str(int(pack["min_stars"]))
        try:
            data, status = gh.get("/search/repositories",
                                  {"q": q, "per_page": int(pack.get("per_page", 15)), "page": 1}, compact)
        except rate_limited as exc:
            feeds.append({"id": feed_id, "kind": "search", "status": "deferred", "detail": str(exc)})
            return hits, feeds, exc
        except RuntimeError as exc:
            feeds.append({"id": feed_id, "kind": "search", "status": "error", "detail": safe(exc, 120)})
            continue
        feeds.append({"id": feed_id, "kind": "search", "status": status, "items": len(data["items"]),
                      "query": q})
        for rank, item in enumerate(data["items"]):
            if item["fork"] or item["archived"]:
                continue
            entry = hits.setdefault(item["repo"].lower(), {"repo": item["repo"], "item": item, "hits": [],
                                                          "best_rank": rank})
            if qid not in entry["hits"]:
                entry["hits"].append(qid)
            entry["best_rank"] = min(entry["best_rank"], rank)
    # Source search: files that only a browser-session worker would contain. Repository
    # search ranks by popularity, so a 1-star extension that matches the words sits
    # behind thousands of bigger repos; a code match on the manifest does not.
    for sq in pack.get("source_queries", [])[: int(pack.get("max_source_queries", 3))]:
        feed_id = "pack:" + pack["id"] + ":" + sq["id"] + ":source"
        if not gh.budget_ok("code_search", 2):
            feeds.append({"id": feed_id, "kind": "code_search", "status": "deferred", "detail": "code search budget low"})
            continue
        try:
            data, status = gh.get("/search/code", {"q": sq["q"], "per_page": int(pack.get("source_per_page", 50)),
                                                   "page": 1}, compact_code)
        except rate_limited as exc:
            feeds.append({"id": feed_id, "kind": "code_search", "status": "deferred", "detail": str(exc)})
            return hits, feeds, exc
        except RuntimeError as exc:
            feeds.append({"id": feed_id, "kind": "code_search", "status": "error", "detail": safe(exc, 120)})
            continue
        feeds.append({"id": feed_id, "kind": "code_search", "status": status, "items": len(data["items"]),
                      "query": sq["q"]})
        for rank, item in enumerate(data["items"]):
            if item["fork"]:
                continue
            entry = hits.setdefault(item["repo"].lower(), {"repo": item["repo"], "item": item, "hits": [],
                                                          "best_rank": rank})
            if sq["id"] not in entry["hits"]:
                entry["hits"].append(sq["id"])
            entry.setdefault("source_paths", [])
            if item.get("path") and item["path"] not in entry["source_paths"]:
                entry["source_paths"].append(item["path"])
    return hits, feeds, None


def compact_code(body):
    """Code-search results reduced to one row per file: repo identity and path only."""
    items = []
    for row in (body or {}).get("items", []):
        repo = (row or {}).get("repository") or {}
        name = str(repo.get("full_name", ""))
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9-]{0,38}/[A-Za-z0-9_.-]{1,100}", name):
            continue
        items.append({"id": repo.get("id"), "repo": name, "stars": 0, "fork": bool(repo.get("fork")),
                      "archived": False, "description": "", "topics": [], "pushed_at": "",
                      "path": str(row.get("path", ""))[:200]})
    return {"items": items, "total": int((body or {}).get("total_count") or 0)}


def source_hits(hit):
    return sum(1 for q in hit["hits"] if q.startswith("s"))


def shortlist(hits, limit):
    """Source matches count double: a manifest that targets chat sites beats a keyword match."""
    ordered = sorted(hits.values(), key=lambda h: (-(len(h["hits"]) + source_hits(h)), h["best_rank"],
                                                   -h["item"]["stars"], h["repo"].lower()))
    return ordered[:limit]


def pick_files(paths):
    """Manifests, tests and up to 6 key source files from a recursive tree listing."""
    manifests, tests, sources = [], [], []
    for entry in paths:
        path, size = entry["path"], entry.get("size", 0)
        if any(path.startswith(d) or "/" + d in path for d in SKIP_DIRS):
            continue
        depth = path.count("/")
        name = PurePosixPath(path).name.lower()
        if TEST_PATH.search(path):
            tests.append(path)
            continue
        if name in MANIFEST_NAMES and depth <= 2 and size <= MAX_BLOB_BYTES:
            manifests.append(path)
        elif PurePosixPath(path).suffix.lower() in SOURCE_EXT and KEY_SOURCE.search(name) and size <= MAX_BLOB_BYTES:
            sources.append((depth, path))
    sources.sort()
    return sorted(manifests, key=lambda p: (p.count("/"), p))[:6], tests, [p for _, p in sources[:6]]


def classify(texts):
    """texts: {path: content}. Returns the mode and the evidence lines that decided it."""
    browser, api = [], []
    joined_manifests = "\n".join(t for p, t in texts.items() if PurePosixPath(p).name.lower() in MANIFEST_NAMES)
    everything = "\n".join(texts.values())
    if BROWSER_DEPS.search(joined_manifests):
        browser.append("browser automation dependency: " + BROWSER_DEPS.search(joined_manifests).group(0).strip().strip('"'))
    for path, text in texts.items():
        if PurePosixPath(path).name.lower() == "manifest.json" and '"manifest_version"' in text:
            if CHAT_SITES.search(text):
                browser.append("browser extension manifest targets chat sites (" + path + ")")
            else:
                browser.append("browser extension manifest (" + path + ")")
    if CHAT_SITES.search(everything):
        browser.append("references chat web apps: " + ", ".join(sorted({m.group(0).lower() for m in CHAT_SITES.finditer(everything)})[:4]))
    for label, pat in BROWSER_TEXT:
        if pat.search(everything):
            browser.append(label)
    # "works without an API key" is a browser-session claim, not an API dependency.
    everything = NO_KEY.sub(" ", everything)
    dep = API_DEPS.search(joined_manifests)
    if dep:
        api.append("model SDK dependency: " + dep.group(0).split(":")[0].strip().strip('"'))
    for label, pat in API_TEXT:
        if pat.search(everything):
            api.append(label)
    browser = list(dict.fromkeys(browser))
    api = list(dict.fromkeys(api))
    if len(browser) >= 2 and not api:
        mode = "browser-session"
    elif len(browser) >= 2:
        mode = "mixed"
    elif api:
        mode = "api-only"
    else:
        mode = "unknown"
    return mode, browser, api


def pack_verdict(record, mode, review_verdict=None):
    if review_verdict:
        return review_verdict, "tested review"
    if record["signals"].get("archived"):
        return "reject", "archived upstream"
    if str(record.get("license", "NONE")).upper() in {"NONE", ""}:
        return "reject", "no license: read for ideas only, no code reuse"
    days = record["signals"].get("days_since_commit")
    if days is None or days > 365:
        return "reject", "no commit in over a year"
    if mode == "api-only":
        return "reject", "API-only multi-agent framework, not browser-session orchestration"
    if mode == "unknown":
        return "reject", "no evidence of browser-session orchestration in README, manifests or key source"
    return "needs-test", ("browser-session orchestration evidence found; needs a pinned source-level reuse test"
                          if mode == "browser-session" else
                          "drives browser sessions but also calls model APIs; check which path Leon would reuse")


def rank_score(hit, record, mode, browser_reasons, tests):
    score = 10 * (len(hit["hits"]) + source_hits(hit)) + MODE_POINTS[mode]
    if any("chat" in r for r in browser_reasons):
        score += 10
    if tests:
        score += 5
    if record.get("license_kind") == "permissive":
        score += 5
    days = record["signals"].get("days_since_commit")
    if days is not None and days <= 90:
        score += 5
    return score


def render(report, md):
    lines = ["# Query pack: " + md(report["label"], 120), "",
             "Problem-first GitHub search, one bounded run. Not full GitHub coverage: GitHub search returns at most "
             + str(report["per_page"]) + " results per query here, ranked by GitHub's own relevance.", "",
             "- Run: " + report["run_at"] + " (" + report["trigger"] + ")",
             "- API calls: " + str(report["api_calls"]["total"]) + " total (" + ", ".join(
                 k + " " + str(v) for k, v in sorted(report["api_calls"]["by_kind"].items())) + ")",
             "- Distinct repos found: " + str(report["distinct_repos_found"]) + "; inspected: " + str(len(report["candidates"])),
             ""]
    if report.get("known_relevant"):
        lines += ["## Rediscovery check (known repos were NOT used as search input)", ""]
        for k in report["known_relevant"]:
            lines.append("- " + md(k["repo"]) + ": " + ("found by queries " + ", ".join(k["found_by"]) +
                                                       (", rank " + str(k["rank"]) if k.get("rank") else ", not inspected")
                                                       if k["found_by"] else "**not found** by this run"))
        lines.append("")
    lines += ["## Ranked candidates", "", "| # | Repo @ SHA | Mode | Pack verdict | Score | Why |", "|---:|---|---|---|---:|---|"]
    for i, c in enumerate(report["candidates"], 1):
        why = "; ".join((c["browser_evidence"] or c["api_evidence"] or ["no signals"])[:3])
        lines.append("| " + str(i) + " | [" + md(c["repo"]) + "](" + c["url"] + "/tree/" + c["sha"] + ") @ " + c["sha"][:7]
                     + " | " + c["mode"] + " | " + c["pack_verdict"] + " | " + str(c["rank_score"]) + " | "
                     + md(c["pack_reason"] + ". " + why, 220) + " |")
    lines += ["", "## Searches", ""]
    for f in report["searches"]:
        lines.append("- " + md(f["id"]) + ": " + f["status"] + (" (" + str(f.get("items")) + " results)" if "items" in f else "")
                     + (" " + md(f.get("detail", "")) if f.get("detail") else ""))
    lines += ["", "Verdicts are pack-specific. Only a tested review in findings/reviews can make anything adopt.", ""]
    return "\n".join(lines)
