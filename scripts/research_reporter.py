#!/usr/bin/env python3
"""Evidence-safe research analysis and report for the ONE active Leon game.

The game comes from the shared authority (active_game.resolve). Held games keep
their historical report files untouched; an unknown game gets no game tasks.

All inputs are public feed metadata. No network, AI, video playback, window
capture, installations, GitHub issues or changes to game code. An unviewed
source NEVER becomes an observed finding or an instruction to Codex.
"""
from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from urllib.parse import urlsplit

import active_game
import learning_radar

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "watch" / "learning_index.json"
OUTPUT = ROOT / "watch"

# Source host must match its existing normalized type, never an arbitrary web URL.
HOSTS = {
    "youtube": {"youtube.com", "www.youtube.com", "youtu.be"},
    "instagram": {"instagram.com", "www.instagram.com"},
    "tiktok": {"tiktok.com", "www.tiktok.com"},
    "x": {"x.com", "www.x.com", "twitter.com", "www.twitter.com"},
    "devforum": {"devforum.roblox.com"},
    "reddit": {"reddit.com", "www.reddit.com"},
}
WEIGHT = {"youtube": 5, "devforum": 4, "instagram": 3, "tiktok": 3, "x": 3, "reddit": 1}
NOISE = re.compile(r"free robux|giveaway|\bprank\b|\btroll\b|download.*free.*windows|join.*discord", re.I)


def valid_source(post: object) -> bool:
    if not isinstance(post, dict) or post.get("evidence") != "UNVIEWED_METADATA":
        return False
    kind, url, key = post.get("kind"), post.get("url"), post.get("key")
    if kind not in HOSTS or not isinstance(url, str) or not isinstance(key, str) or len(url) > 700:
        return False
    if any(c in "()<>[]{}" or ord(c) <= 32 or ord(c) in (92, 127) for c in url):
        return False
    try:
        parsed = urlsplit(url)
        if parsed.scheme != "https" or parsed.hostname not in HOSTS[kind] or parsed.username or parsed.password:
            return False
    except ValueError:
        return False
    return learning_radar.identity(url) == (key, kind)


def clean(text: object, max_length: int = 130) -> str:
    value = re.sub(r"[\x00-\x1f\x7f]+", " ", str(text or ""))[:max_length].strip()
    for ch in "\\[]<>|":
        value = value.replace(ch, "\\" + ch)
    return value


def analyze(index: dict, game: str | None, limit: int = 6) -> dict:
    """Choose independent, primary-source leads, not purported gameplay insights.

    game=None means the active game is unknown: no lanes, no game-specific tasks.
    """
    if not isinstance(index, dict) or not isinstance(index.get("posts"), list):
        raise ValueError("Learning index missing or invalid")
    if len(index["posts"]) > 10000 or not 1 <= limit <= 12:
        raise ValueError("Research report exceeds its bounded input")
    eligible = []
    for p in index["posts"]:
        if not valid_source(p):
            continue
        title = p.get("title")
        signals = p.get("signals")
        score = p.get("score")
        if (not isinstance(title, str) or not title.strip() or NOISE.search(title)
                or not isinstance(signals, list) or not isinstance(score, int)
                or isinstance(score, bool) or not 0 <= score <= 100):
            continue
        if not all(isinstance(label, str) for label in signals):
            continue
        eligible.append(p)
    profile = active_game.PROFILES.get(game)
    lanes = profile["lanes"] if profile else ()
    seen, used_sources, results = set(), Counter(), []
    for lane, priority, question in lanes:
        # The learning index may assign a signal based on an excerpt alone.
        # Require the actual public TITLE to independently mention the topic;
        # otherwise general-feed items get mislabeled as active-game leads.
        title_pattern = learning_radar.FOCUS[lane]
        candidates = [p for p in eligible if lane in p["signals"] and p["key"] not in seen
                      and used_sources[str(p.get("source", ""))] < 2
                      and re.search(title_pattern, p["title"], re.I)]
        # Excerpts may contain irrelevant or adversarial keyword stuffing.
        # Rank by actual title matches and primary-source type, NOT excerpt score.
        candidates.sort(key=lambda p: (
            -(min(3, len(re.findall(title_pattern, p["title"], re.I))) * 3 + WEIGHT[p["kind"]]),
            str(p.get("key", "")),
        ))
        if not candidates or len(results) >= limit:
            continue
        p = candidates[0]
        seen.add(p["key"])
        used_sources[str(p.get("source", ""))] += 1
        results.append({
            "priority": priority, "topic": lane, "key": p["key"],
            "title": p["title"][:160], "url": p["url"], "kind": p["kind"],
            "published": str(p.get("published", ""))[:30],
            "stage": "UNVIEWED_METADATA", "observation_verified": False,
            "question_for_reviewer": question,
        })
    return {
        "schema": ("LEON_" + profile["slug"].upper() + "_RESEARCH_REPORT_V1") if profile
                  else "LEON_ACTIVE_GAME_RESEARCH_REPORT_V1",
        "status": "TRIAGE_ONLY_NOT_GAMEPLAY_ANALYSIS" if profile else "ACTIVE_GAME_UNKNOWN_NO_GAME_TASKS",
        "active_game": profile["name"] if profile else None,
        "held_games_not_current": [active_game.PROFILES[g]["name"] for g in active_game.held(game)],
        "input_unique_posts": len(index["posts"]),
        "original_source_candidates": len(eligible),
        "inspected_videos": 0, "observed_gameplay_findings": 0,
        "new_code_changes_authorized": False,
        "candidates": results,
        "unfilled_topics": [lane for lane, _, _ in lanes if not any(p["topic"] == lane for p in results)],
    }


def render(report: dict) -> str:
    name = report.get("active_game")
    lines = [
        "# " + (clean(name) if name else "Active game UNKNOWN") + " research intelligence — evidence-gated", "",
        "**Current stage: metadata triage only. No video watched, game tested, model inspected, or verified design finding.**",
        "This is a bounded reading queue, not an instruction to copy assets or automatically edit a Roblox game.", "",
        f"Indexed entries: {report['input_unique_posts']}; direct candidates: {report['original_source_candidates']};",
        "Inspected videos: **0**; verified gameplay findings: **0**.", "",
    ]
    if report.get("held_games_not_current"):
        lines.extend(["On hold, NOT current work: " + ", ".join(clean(g) for g in report["held_games_not_current"])
                      + ". Their older report files are historical only.", ""])
    lines.extend(["## Highest-value source checks", ""])
    if not name:
        lines.append("The shared active-game authority was missing or unrecognized, so no game-specific checks are listed.")
    elif not report["candidates"]:
        lines.append("No eligible first-party/original leads. Research quality needs improvement before making recommendations.")
    for p in report["candidates"]:
        lines.extend([
            f"- **{p['priority']} · {clean(p['topic'])}:** [{clean(p['title'])}]({p['url']})",
            f"  - {p['kind']} · **UNVIEWED_METADATA** · Check: {clean(p['question_for_reviewer'], 260)}",
        ])
    if report["unfilled_topics"]:
        lines.extend(["", "## Research gaps", ""])
        lines.extend("- " + clean(topic) + ": no qualifying original/source-linked candidate" for topic in report["unfilled_topics"])
    lines.extend(["", "## Required before a verified improvement", "",
        "1. Inspect the original permitted source and record actual time-coded observations, creator, usage rights and uncertainty.",
        "2. Compare the observation to an **existing** " + (clean(name) if name else "active-game") + " defect and choose ONE measurable code/scene change.",
        "3. Codex works on an isolated branch; test Luau and normal-player Studio input with evidence before merging.",
        "4. Do not copy proprietary models, import untrusted scripts, or treat a screen capture alone as proof a video was watched.",
        "5. Peekaboo and full-video analysis remain separate, opt-in Mac verification gates; no Mac screenshots are uploaded here.", ""])
    return "\n".join(lines)


def save(path: Path, body: str) -> bool:
    if path.is_file() and path.read_text(encoding="utf-8") == body:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    return True


def main() -> None:
    if not INDEX.is_file():
        raise FileNotFoundError("Run existing learning_radar first; no index")
    if INDEX.stat().st_size > 8_000_000:
        raise ValueError("Learning index exceeds limit")
    index = json.loads(INDEX.read_text(encoding="utf-8"))
    game, authority = active_game.resolve()
    report = analyze(index, game)
    report["authority"] = authority
    body_json = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    body_md = render(report) + "\n"
    written = [save(OUTPUT / "current_game_research_report.json", body_json),
               save(OUTPUT / "current_game_research_report.md", body_md)]
    if game:
        # Held games' files are never touched, so they stay as historical records.
        slug = active_game.PROFILES[game]["slug"]
        written += [save(OUTPUT / (slug + "_research_report.json"), body_json),
                    save(OUTPUT / (slug + "_research_report.md"), body_md)]
    print("Updated" if any(written) else "Unchanged", "evidence-safe research report for",
          report["active_game"] or "UNKNOWN active game", "(" + authority + ")")


if __name__ == "__main__":
    main()
