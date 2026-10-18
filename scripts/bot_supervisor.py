#!/usr/bin/env python3
"""No-AI bot health report using only PUBLIC GitHub Actions run metadata."""
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "watch" / "bot_health.md"
REPOS = [
    "Leonwei-cyb/roblox-research-scout",
]
API = "https://api.github.com/repos/{}/actions/runs?per_page=12"

def runs_for(repo):
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "RobloxBotHealth/1"}
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = "Bearer " + token
    request = Request(API.format(repo), headers=headers)
    try:
        with urlopen(request, timeout=9) as response:
            return json.load(response).get("workflow_runs", [])
    except HTTPError as exc:
        raise RuntimeError("GitHub HTTP " + str(exc.code)) from exc
    except URLError as exc:
        raise RuntimeError("GitHub API connection failed") from exc

def summarize(repo, runs):
    # Only completed runs are rated. A run that is still executing isn't a failure.
    completed = [r for r in runs if r.get("status") == "completed" and r.get("conclusion")]
    last = completed[0] if completed else None
    failures = sum(r.get("conclusion") not in {"success", "skipped", "neutral"} for r in completed[:10])
    state = ("NO COMPLETED RUN" if last is None else
             ("ATTENTION" if last.get("conclusion") != "success" else "OK"))
    return state, failures, last

def render(all_runs):
    lines = [
        "# Public GitHub bot health", "",
        "Deterministic Actions metadata; NOT a quality verdict or proof the content sources worked.",
        "This report excludes private repositories and contains no account secrets.", "",
        "| Repository | Last completed | Recent failed checks | Run |",
        "|---|---|---:|---|",
    ]
    for repo, runs in all_runs:
        state, failed, last = summarize(repo, runs)
        url = last.get("html_url", "") if last else ""
        if not url.startswith("https://github.com/"):
            url = "https://github.com/" + repo + "/actions"
        lines.append("| " + repo + " | " + state + " | " + str(failed) +
                     " / " + str(min(10, len([r for r in runs if r.get("status") == "completed"]))) +
                     " | [View](" + url + ") |")
    lines += ["", "### Important limits", "",
        "- This is a once-per-research-workflow health check, NOT an hourly independent daemon.",
        "- The current running workflow cannot grade its own future completion.",
        "- Passing Actions jobs may still contain blocked TikTok, X or Reddit source feeds.",
        "- Private gameplay bots require an event-driven private-repo supervisor; never send their contents to public CI.",
        "- For content coverage, also read [source_health.md](source_health.md) and [coverage_audit.md](coverage_audit.md).", ""]
    return "\n".join(lines)

def main():
    checks = []
    for repo in REPOS:
        try:
            checks.append((repo, runs_for(repo)))
        except RuntimeError as exc:
            print("Supervisor API unavailable:", str(exc))
            checks.append((repo, []))
    report = render(checks)
    if not OUT.exists() or OUT.read_text(encoding="utf-8") != report:
        OUT.write_text(report, encoding="utf-8")
        print("Updated bot health")
    else:
        print("Bot health unchanged")

if __name__ == "__main__":
    main()
