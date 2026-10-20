#!/usr/bin/env python3
"""Turn high-value query-pack candidates into deduplicated research issues in THIS repo.

- Only Leonwei-cyb/roblox-research-scout (or $GITHUB_REPOSITORY when it is that
  repo) is ever written to. Other repositories are never touched.
- One issue per canonical repo, ever: a hidden marker
  `<!-- discovery-key: owner/repo -->` is searched in all existing issues
  (open and closed) before anything is created.
- At most `max_issues` per run (default 3). Repos already audited by another
  worker are skipped. Suggested owner is stated in the body; nobody is pinged.
- `--dry-run` prints what it would do and makes no request that writes.
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
PACKS = ROOT / "findings" / "packs"
# GitHub's issue list is eventually consistent: an issue opened seconds ago can be
# missing from the next listing (seen live 2026-10-20: a back-to-back rerun opened
# #17-#19 as duplicates of #14-#16). Every issue this script opens is also written
# here; the workflow commits this file after routing, and its concurrency group
# keeps CI runs apart.
LEDGER = ROOT / "findings" / "issue_ledger.json"
HOME_REPO = "Leonwei-cyb/roblox-research-scout"
API = "https://api.github.com"
MARKER = re.compile(r"<!-- discovery-key: ([a-z0-9][a-z0-9-]*/[a-z0-9_.-]+) -->")


def target_repo():
    repo = os.environ.get("GITHUB_REPOSITORY") or HOME_REPO
    if repo != HOME_REPO:
        raise SystemExit("Refusing to write issues anywhere but " + HOME_REPO)
    return repo


def request(method, path, token, body=None):
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "leon-oss-discovery-no-ai",
               "X-GitHub-Api-Version": "2022-11-28", "Authorization": "Bearer " + token}
    data = json.dumps(body).encode("utf-8") if body is not None else None
    if data:
        headers["Content-Type"] = "application/json"
    try:
        with urlopen(Request(API + path, data=data, method=method, headers=headers), timeout=15) as resp:
            return json.load(resp)
    except HTTPError as err:
        raise RuntimeError("GitHub HTTP " + str(err.code) + " for " + method + " " + path.split("?")[0]) from err
    except (URLError, TimeoutError, ValueError) as err:
        raise RuntimeError("GitHub API unavailable") from err


def existing_keys(repo, token, pages=10):
    keys = {}
    for page in range(1, pages + 1):
        rows = request("GET", "/repos/" + repo + "/issues?state=all&per_page=100&page=" + str(page), token)
        for issue in rows:
            for key in MARKER.findall(issue.get("body") or ""):
                number = issue.get("number")
                if key not in keys or (isinstance(number, int) and number < keys[key]):
                    keys[key] = number       # the oldest issue is the canonical one
        if len(rows) < 100:
            break
    return keys


def selected(reports, min_score=60):
    out = []
    for report in reports:
        for c in report.get("candidates", []):
            if (c.get("pack_verdict") == "needs-test" and not c.get("audited_elsewhere")
                    and int(c.get("rank_score", 0)) >= min_score):
                out.append((report, c))
    out.sort(key=lambda rc: (-int(rc[1]["rank_score"]), rc[1]["repo"].lower()))
    return out


def clean(text, n=300):
    return re.sub(r"[\x00-\x1f\x7f<>`]", " ", str(text or ""))[:n].strip()


def issue_body(report, c):
    lines = [
        "Automated research lead from query pack `" + clean(report["pack"], 80) + "`: " + clean(report["label"], 160) + ".",
        "", "**Not installed, not run.** Metadata and a read of the files below only.", "",
        "- Repo: https://github.com/" + c["repo"] + " at `" + c["sha"] + "` (" + clean(c.get("version"), 40) + ")",
        "- License: " + clean(c["license"], 40) + "; last commit " + str(c.get("days_since_commit")) + " days before the run",
        "- Classification: **" + c["mode"] + "**; pack verdict **" + c["pack_verdict"] + "** (" + clean(c["pack_reason"], 200) + ")",
        "- Found by queries: " + ", ".join(clean(x, 4) for x in c.get("found_by", [])) + "; rank score " + str(c["rank_score"]),
        "- Browser-session evidence: " + ("; ".join(clean(x, 120) for x in c.get("browser_evidence", [])) or "none"),
        "- API-only evidence: " + ("; ".join(clean(x, 120) for x in c.get("api_evidence", [])) or "none"),
        "- Files read: " + (", ".join(clean(x, 120) for x in c.get("files_inspected", [])) or "none")
        + "; test files seen: " + str(c.get("tests_found", 0)),
        "", "**Suggested owner:** " + clean(c.get("suggested_owner") or "Wheel", 30) + " (routing is the hub's call).",
        "", "**Bounded task:** pin the SHA above, read the license and the files listed, run one isolated "
            "source-level reuse test (no installs on the Mac, no live sessions, no paid model calls), then record "
            "adopt or reject in `findings/reviews/`.", "",
        "Evidence: " + " ".join(c.get("evidence", [])[:5]), "",
        "Run: " + clean(report.get("run_at"), 30) + ". Not full GitHub coverage.", "",
        "<!-- discovery-key: " + c["repo"].lower() + " -->",
    ]
    return "\n".join(lines)


def main(argv):
    dry = "--dry-run" in argv
    token = os.environ.get("GITHUB_TOKEN", "")
    repo = target_repo()
    reports = [json.loads(p.read_text(encoding="utf-8")) for p in sorted(PACKS.glob("*.json"))] if PACKS.is_dir() else []
    picks = selected(reports)
    max_issues = int(os.environ.get("DISCOVERY_MAX_ISSUES", "3"))
    if not picks:
        print("No pack candidate above the issue threshold.")
        return 0
    if not token:
        print("No GITHUB_TOKEN; listing only.")
        dry = True
    ledger = json.loads(LEDGER.read_text(encoding="utf-8")) if LEDGER.exists() else {}
    keys = dict(ledger)
    if token:
        for key, number in existing_keys(repo, token).items():
            if key not in keys or (isinstance(number, int) and isinstance(keys[key], int) and number < keys[key]):
                keys[key] = number
    created = 0
    for report, c in picks:
        key = c["repo"].lower()
        if key in keys:
            print("Already tracked: " + c["repo"] + " in #" + str(keys[key]))
            continue
        if created >= max_issues:
            print("Issue budget reached; " + c["repo"] + " waits for the next run.")
            continue
        title = "[Discovery] " + c["repo"] + ": " + c["mode"] + " candidate (" + c["pack_verdict"] + ")"
        if dry:
            print("Would open: " + title)
        else:
            issue = request("POST", "/repos/" + repo + "/issues", token,
                            {"title": title, "body": issue_body(report, c)})
            print("Opened #" + str(issue.get("number")) + ": " + title)
            ledger[key] = issue.get("number")
            LEDGER.parent.mkdir(parents=True, exist_ok=True)
            LEDGER.write_text(json.dumps(ledger, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        keys[key] = "new"
        created += 1
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except RuntimeError as exc:
        print("Discovery issues failed: " + str(exc), file=sys.stderr)
        sys.exit(1)
