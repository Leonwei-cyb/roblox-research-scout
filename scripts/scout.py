#!/usr/bin/env python3
"""No-AI GitHub scouting. Changes are discovery leads, NOT quality endorsements.

Uses GitHub's public REST API with the current Actions GITHUB_TOKEN.
Network access is limited to api.github.com, and no external Python packages are used.
"""

import json
import os
import re
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "watch" / "config.json"
STATE = ROOT / "watch" / "state.json"
REPORT = ROOT / "watch" / "latest.md"
HEALTH = ROOT / "watch" / "github_source_health.md"
API = "https://api.github.com"
MAX_SEEN = 600


def safe(text, max_len=180):
    """Make third-party metadata inert in a compact Markdown report."""
    text = re.sub(r"[\x00-\x1f\x7f]", " ", str(text or ""))
    text = text.replace("[", "\\[").replace("]", "\\]")
    text = text.replace("|", "\\|").replace(chr(96), "'")
    return text[:max_len].strip()


def api_get(path, params=None):
    url = API + path
    if params:
        url += "?" + urlencode(params)
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "roblox-research-no-ai-scout",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    token = os.environ.get("GITHUB_TOKEN", "")
    if token:
        headers["Authorization"] = "Bearer " + token
    req = Request(url, headers=headers)
    try:
        with urlopen(req, timeout=15) as response:
            return json.load(response)
    except HTTPError as err:
        if err.code == 404:
            return None
        raise RuntimeError("GitHub API HTTP " + str(err.code) + " for " + path) from err
    except (URLError, ValueError) as err:
        raise RuntimeError("GitHub API unavailable for " + path) from err


def snapshot_repo(full_name):
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", full_name):
        raise ValueError("Invalid GitHub repository: " + full_name)
    name = quote(full_name, safe="/")
    repo = api_get("/repos/" + name)
    if repo is None:
        raise RuntimeError("Watched repository no longer exists: " + full_name)
    releases = api_get("/repos/" + name + "/releases/latest")
    commits = api_get("/repos/" + name + "/commits", {"per_page": 1}) or []
    last = commits[0] if commits else {}
    return {
        "name": full_name,
        "url": "https://github.com/" + full_name,
        "head": last.get("sha", ""),
        "head_subject": safe(last.get("commit", {}).get("message", "").split("\n")[0]),
        "release_tag": (releases or {}).get("tag_name", ""),
        "release_url": (releases or {}).get("html_url", ""),
    }


def search_repos(query, min_stars, limit):
    result = api_get(
        "/search/repositories",
        {
            "q": query,
            "sort": "updated",
            "order": "desc",
            "per_page": min(25, int(limit)),
        },
    ) or {}
    repos = []
    for item in result.get("items", []):
        if item.get("archived") or item.get("fork"):
            continue
        if item.get("stargazers_count", 0) < min_stars:
            continue
        repo_name = item.get("full_name", "")
        if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo_name):
            continue
        repos.append({
            "name": repo_name,
            "url": "https://github.com/" + repo_name,
            "stars": int(item.get("stargazers_count", 0)),
            "description": safe(item.get("description", "")),
            "pushed_at": item.get("pushed_at", "")[:10],
        })
    return repos


def read_json(path, fallback):
    if not path.exists():
        return fallback
    return json.loads(path.read_text(encoding="utf-8"))


def hosted_config_autofix(root=ROOT):
    """Free deterministic repair on the existing hosted scout run, never on Mac."""
    if os.environ.get("GITHUB_ACTIONS")!="true":
        return []
    from safe_config_autofix import work
    return work(Path(root),write=True)


def run():
    cfg = read_json(CONFIG, {})
    old = read_json(STATE, {"repos": {}, "seen": []})
    first = not STATE.exists()
    seen = set(old.get("seen", []))
    current = {}
    updates = []

    issues = []
    checked = 0
    targets = cfg.get("watch_repos", [])[:20]
    for name in targets:
        try:
            current[name] = snapshot_repo(name)
            checked += 1
        except (RuntimeError, ValueError) as exc:
            issues.append(name + ": " + safe(str(exc),120))
            # Do not erase the last known release/head on a temporary failure.
            if name in old.get("repos", {}):
                current[name] = old["repos"][name]
            continue
        prior = old.get("repos", {}).get(name)
        if not first and prior:
            now = current[name]
            if now["release_tag"] != prior.get("release_tag", ""):
                desc = safe(prior.get("release_tag", "none")) + " → " + safe(now["release_tag"] or "none")
                updates.append("- **Release:** [" + name + "](" + now["url"] + ") " + desc + ".")
            elif now["head"] and now["head"] != prior.get("head", ""):
                updates.append("- **Source updated:** [" + name + "](" + now["url"] + ") — " + now["head_subject"] + ".")

    found = {}
    for query in cfg.get("discovery_queries", [])[:4]:
        try:
            candidates = search_repos(query, int(cfg.get("min_stars", 10)), int(cfg.get("results_per_query", 12)))
        except (RuntimeError, ValueError) as exc:
            issues.append("Discovery query: " + safe(str(exc),120))
            continue
        for result in candidates:
            found[result["name"]] = result
    if checked == 0:
        raise RuntimeError("No watched GitHub repository could be checked; preserving previous snapshot.")
    health_lines = [
        "# GitHub source coverage", "",
        "Watchlist configured: " + str(len(cfg.get("watch_repos", []))),
        "Watchlist attempted: " + str(len(targets)),
        "Repositories successfully checked: " + str(checked),
        "Discovery query errors included below; successful API calls are not an endorsement.",
        "",
    ]
    health_lines += ["- " + safe(issue,210) for issue in issues] if issues else ["No GitHub source errors."]
    health_text = "\n".join(health_lines) + "\n"
    if not HEALTH.exists() or HEALTH.read_text(encoding="utf-8") != health_text:
        HEALTH.write_text(health_text, encoding="utf-8")

    new_leads = [v for k, v in found.items() if k not in seen and k not in current]
    new_leads.sort(key=lambda x: (-x["stars"], x["name"]))
    updates.extend(
        "- **Unreviewed lead:** [" + p["name"] + "](" + p["url"] + ") ("
        + str(p["stars"]) + " stars). " + p["description"]
        for p in new_leads[:15]
    )

    next_state = {
        "repos": current,
        "seen": sorted((seen | set(found) | set(current)))[-MAX_SEEN:],
    }
    # Do not overwrite a good baseline with an incomplete scan. All API calls happen above.
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(next_state, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")

    if first:
        lines = [
            "# Roblox research scout — initial baseline",
            "",
            "Automatically gathered GitHub metadata, **not** a game-quality review.",
            "",
            "## Monitored projects",
            "",
        ]
        for p in current.values():
            lines.append("- [" + p["name"] + "](" + p["url"] + ") — latest release: " + safe(p["release_tag"] or "none") + ".")
        lines.extend(["", "## Discovered candidate repositories", ""])
        for p in sorted(found.values(), key=lambda r: (-r["stars"], r["name"]))[:15]:
            lines.append("- [" + p["name"] + "](" + p["url"] + ") (" + str(p["stars"]) + " stars). " + p["description"])
        lines.extend(["", "These are **leads only**. No gameplay videos were watched, and no assets/plugins were installed."])
    elif updates:
        lines = [
            "# Roblox research scout — changes since last run",
            "",
            "Automated GitHub metadata observations, **not** verified recommendations.",
            "",
            *updates,
            "",
            "For any candidate: inspect its actual source, permissions/license, gameplay fit, and a real task before adopting.",
        ]
    else:
        print("No new release, source activity or candidate lead. Existing report unchanged.")
        return

    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(("Baseline created" if first else "Changes found") + ": " + str(len(found)) + " candidate entries, " + str(len(updates)) + " updates")


if __name__ == "__main__":
    try:
        # Already-scheduled hourly scout calls this entrypoint. No extra job.
        repairs=hosted_config_autofix()
        changed=sum(sum(counts.values()) for _,counts in repairs)
        if changed:
            print("Safe public source duplicates repaired:",changed)
        run()
    except (RuntimeError, ValueError, OSError, KeyError, TypeError) as exc:
        print("Scout failed: " + str(exc), file=sys.stderr)
        sys.exit(1)
