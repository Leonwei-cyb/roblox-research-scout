#!/usr/bin/env python3
"""No-AI health reports for PUBLIC GitHub Actions metadata only.

Default mode writes the historical research-scout snapshot at each research run.
--monitor checks only research.yml without changing any tracked repository file.
No credentials, private repositories, video playback or game files are accessed.
"""
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "watch" / "bot_health.md"
REPOS = ["Leonwei-cyb/roblox-research-scout"]
API = "https://api.github.com/repos/{}/actions/runs?per_page=12"
RESEARCH_API = "https://api.github.com/repos/{}/actions/workflows/research.yml/runs?per_page=12"
MAX_RESEARCH_AGE = timedelta(hours=10)


def _get_runs(url):
    headers = {"Accept": "application/vnd.github+json",
               "User-Agent": "RobloxBotHealth/1",
               "X-GitHub-Api-Version": "2022-11-28"}
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = "Bearer " + token
    request = Request(url, headers=headers)
    try:
        with urlopen(request, timeout=9) as response:
            return json.load(response).get("workflow_runs", [])
    except HTTPError as exc:
        raise RuntimeError("GitHub HTTP " + str(exc.code)) from exc
    except (URLError, TimeoutError) as exc:
        raise RuntimeError("GitHub API connection failed") from exc


def runs_for(repo):
    """Historical public-repo overview for the four daily research reports."""
    return _get_runs(API.format(repo))


def research_runs_for(repo):
    """Only research.yml; excludes this monitor's own successful workflow runs."""
    if repo not in REPOS:
        raise ValueError("Only approved public research repos may be monitored")
    return _get_runs(RESEARCH_API.format(repo))


def summarize(repo, runs):
    # Legacy report contract: do not count an in-progress run as a failure.
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
        # Stable workflow link avoids a pointless commit on every successful check.
        url = "https://github.com/" + repo + "/actions/workflows/research.yml"
        lines.append("| " + repo + " | " + state + " | " + str(failed) +
                     " / " + str(min(10, len([r for r in runs if r.get("status") == "completed"]))) +
                     " | [View](" + url + ") |")
    lines += ["", "### Important limits", "",
        "- This is a once-per-research-workflow repository overview, not the separate hourly monitor.",
        "- The current running workflow cannot grade its own future completion.",
        "- Passing Actions jobs may still contain blocked TikTok, X or Reddit source feeds.",
        "- Private gameplay bots are excluded; never send their contents to public CI.",
        "- For content coverage, also read [source_health.md](source_health.md) and [coverage_audit.md](coverage_audit.md).", ""]
    return "\n".join(lines)


def _when(text):
    if not text:
        return None
    try:
        dt = datetime.fromisoformat(str(text).replace("Z", "+00:00"))
        return dt if dt.tzinfo else None
    except (TypeError, ValueError):
        return None


def research_status(runs, now=None):
    """Classify a four-times-daily research workflow, not arbitrary PR/monitor jobs."""
    now = now or datetime.now(timezone.utc)
    relevant = [
        r for r in runs
        if r.get("head_branch") in {None, "main"}
        and r.get("event") in {None, "schedule", "push", "workflow_dispatch"}
    ]
    completed = sorted(
        [r for r in relevant if r.get("status") == "completed" and r.get("conclusion")],
        key=lambda r: r.get("created_at") or "", reverse=True
    )
    latest = completed[0] if completed else None
    if latest is None:
        return "NO COMPLETED RESEARCH RUN", latest, 0
    failures = sum(r["conclusion"] not in {"success", "skipped", "neutral"} for r in completed[:10])
    if latest["conclusion"] != "success":
        return "ATTENTION", latest, failures
    ended = _when(latest.get("updated_at")) or _when(latest.get("created_at"))
    if ended is None:
        return "UNKNOWN RUN AGE", latest, failures
    if now - ended > MAX_RESEARCH_AGE:
        return "STALE", latest, failures
    return "OK", latest, failures


def live_report(runs, now=None):
    """Generate ephemeral Actions job summary; never commit on each poll."""
    now = now or datetime.now(timezone.utc)
    state, latest, failures = research_status(runs, now=now)
    url = latest.get("html_url") if latest else ""
    if not (isinstance(url, str) and
            url.startswith("https://github.com/Leonwei-cyb/roblox-research-scout/actions/runs/")):
        url = "https://github.com/Leonwei-cyb/roblox-research-scout/actions"
    completed_at = (latest.get("updated_at") or latest.get("created_at")) if latest else "none"
    return state, "\n".join([
        "## Public Roblox Research Bot — hourly health check",
        "",
        "**State: " + state + "**",
        "",
        "- Latest completed research workflow: " + str(completed_at),
        "- Recent failed completed research runs: " + str(failures),
        "- [Inspect research workflow run](" + url + ")",
        "",
        "This checks **research.yml only**; the monitor cannot mark itself healthy.",
        "The research collection runs four times daily, so a successful completion",
        "under 10 hours old is considered timely. GitHub scheduled starts may be delayed.",
        "",
        "A successful run does **not** mean individual X, Instagram or Reddit feeds worked.",
        "For source failures inspect [source_health.md](https://github.com/Leonwei-cyb/roblox-research-scout/blob/main/watch/source_health.md).",
        "No paid AI models, private repositories, media downloads, commits or auto-restarts.",
        ""
    ])


def monitor():
    repo = REPOS[0]
    try:
        runs = research_runs_for(repo)
        state, report = live_report(runs)
    except RuntimeError as exc:
        state = "API UNAVAILABLE"
        report = ("## Public Roblox Research Bot — hourly health check\n\n"
                  "**State: API UNAVAILABLE**\n\n" + str(exc) +
                  "\n\nGitHub API availability is not proof that the bot itself failed.\n")
    print(report)
    path = os.environ.get("GITHUB_STEP_SUMMARY")
    if path:
        with open(path, "a", encoding="utf-8") as dest:
            dest.write(report)
    if state != "OK":
        print("::warning::Research bot health: " + state)
    # Advisory checks never create recurring failing runs or perform write actions.
    return state


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
    if "--monitor" in sys.argv:
        monitor()
    else:
        main()
