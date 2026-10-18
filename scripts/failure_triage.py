#!/usr/bin/env python3
"""Source failure triage with compact, deduped advisory output; zero paid AI."""
from __future__ import annotations
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HEALTH = ROOT / "watch/source_health.md"
STATE = ROOT / "watch/failure_streaks.json"
REPORT = ROOT / "watch/failure_triage.md"

def failures(text):
    lines = []
    in_fail = False
    for line in text.splitlines():
        if line.strip().startswith("## Failures"):
            in_fail = True
            continue
        if in_fail and line.startswith("## "):
            break
        if in_fail and line.startswith("- "):
            name, sep, issue = line[2:].partition(": ")
            if sep and re.fullmatch(r"[A-Za-z0-9_-]{2,95}",name):
                lines.append((name,issue[:150]))
    return dict(lines)

def deferred(text):
    """A cooldown is NOT a successful read and must not reset its failure streak."""
    lines = []
    inside = False
    for line in text.splitlines():
        if line.strip().startswith("## Deferred feeds"):
            inside = True
            continue
        if inside and line.startswith("## "):
            break
        if inside and line.startswith("- "):
            name, sep, issue = line[2:].partition(": ")
            if sep and re.fullmatch(r"[A-Za-z0-9_-]{2,95}",name):
                lines.append((name,issue[:150]))
    return dict(lines)


def next_state(previous, current, deferred_sources=None):
    # Count attempted failures; keep the existing streak during cooldown.
    deferred_sources = deferred_sources or {}
    state = {k: {"reason":v, "streak": int(previous.get(k,{}).get("streak",0)) + 1}
             for k,v in current.items()}
    for k,reason in deferred_sources.items():
        if k not in state and k in previous:
            state[k] = previous[k]
    return state

def render(state, deferred_sources=None):
    deferred_sources = deferred_sources or {}
    lines = ["# Source failure triage", "",
        "Counts only attempted feed failures. Deferred rate-limited sources retain their previous failure count until actually retried.", "",
        "| Source | Consecutive observed failures | What to do |", "|---|---:|---|"]
    if not state:
        lines.append("| None | 0 | No feed-level failure in latest scan. |")
    for name, info in sorted(state.items(), key=lambda x:(-x[1]["streak"],x[0])):
        reason = info["reason"]
        deferred_label = " [cooling down — not retried]" if name in deferred_sources else ""
        if "429" in reason:
            action = "Rate limited: reduce frequency; do not retry immediately."
        elif "403" in reason or "401" in reason:
            action = "Access restriction: use permitted official feeds, not cookies/bypass."
        elif "timed out" in reason:
            action = "Timeout: try later; preserve last good report."
        else:
            action = "Investigate public URL and source schema."
        lines.append("| "+name+deferred_label+" ("+reason.replace("|","/")+") | "+str(info["streak"])+" | "+action+" |")
    lines += ["", "Never assume a Google News result is original media or that a 200 response proves content quality.", ""]
    return "\n".join(lines)

def main():
    if not HEALTH.exists():
        print("No feed health snapshot yet; triage deferred")
        return
    health_text = HEALTH.read_text(encoding="utf-8")
    current = failures(health_text)
    cooling_down = deferred(health_text)
    previous = json.loads(STATE.read_text(encoding="utf-8")) if STATE.exists() else {}
    new = next_state(previous, current, cooling_down)
    if new != previous:
        STATE.write_text(json.dumps(new,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    report = render(new, cooling_down)
    if not REPORT.exists() or REPORT.read_text(encoding="utf-8") != report:
        REPORT.write_text(report,encoding="utf-8")
    print("Source triage: "+str(len(current))+" failed feeds")
if __name__ == "__main__":
    main()
