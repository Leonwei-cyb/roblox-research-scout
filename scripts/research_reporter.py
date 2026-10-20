#!/usr/bin/env python3
"""Evidence-safe Cat Magic research analysis and report, within the existing scout.

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

import learning_radar

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "watch" / "learning_index.json"
OUTPUT = ROOT / "watch"

# Actual current game acceptance questions, not hypothetical new game features.
LANES = (
    ("first-session and mobile", "P0", "Can a new player identify and reach the first FREE pad from the normal spawn camera?"),
    ("physical tycoon purchases", "P0", "Does buying a pad visibly build a desk and bring a cat into the classroom?"),
    ("cat animation and audio", "P1", "Does an arriving cat walk, sit, study and cast without clipping through the player?"),
    ("UI and menus", "P1", "Is the next upgrade price readable without covering the cat or Roblox mobile controls?"),
    ("tuition and economy", "P1", "Does a completed lesson produce server-owned tuition and enable the next purchase?"),
    ("world and visual design", "P1", "Are the blue grounds, simple entrance and first classroom visible and uncluttered?"),
)
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

# Topic gates are intentionally narrower than the broad discovery radar. A
# reference has to name a *relevant gameplay problem* in its title to occupy one
# of six scarce implementation-review slots. Otherwise report a research gap.
TITLE_GATES = {
    "first-session and mobile": (
        r"onboard\w*|\bretention\b|\bfirst.{0,10}(minute|session)|\bnew.{0,8}player"
        r"|\bplayers? leave\b|\btutorial.{0,15}(game|tycoon|first)"
        r"|\bmobile.{0,18}(ui|controls?|tutorial|onboard|experience)"
    ),
    "physical tycoon purchases": (
        r"\btycoon\b.{0,24}\b(purchase|buy|pad|button|build|upgrade)\b"
        r"|\b(purchas|buy|upgrad)\w*.{0,16}\b(pad|button|desk|classroom|building)\b"
        r"|\b(build|construct)\w*.{0,18}\b(animation|effect|purchase|pad|button|desk)\b"
    ),
    "cat animation and audio": (
        r"\banimat\w*.{0,16}(cat|pet)|\b(cat|pet).{0,18}(animation|controller|walking|rig|movement)"
        r"|\b(character|avatar).{0,12}animation|\banimation.{0,15}(mobile|game feel)"
    ),
    "UI and menus": r"\bui\b|\bhud\b|\bshop\b|\bmenu\b|\binventory\b|\bhotbar\b",
    "tuition and economy": (
        r"\btuition\b|\bincome\b|\bearnings?\b|\beconomy\b"
        r"|\bidle (game|tycoon|income)|\btycoon (currency|money|pricing|income)"
        r"|\bupgrade (economy|balance|cost)"
    ),
    "world and visual design": (
        r"\bterrain\b|\bgrass\b|\bclassroom\b|\blighting\b|\benvironment\b"
        r"|\blow.poly\b|\bgame.world\b|\b3d (art|models|assets)"
    ),
}


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


def analyze(index: dict, limit: int = 6) -> dict:
    """Choose candidate direct-platform links, not validated original sources."""
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
    seen, used_sources, results = set(), Counter(), []
    for lane, priority, question in LANES:
        # The learning index may assign a signal based on an excerpt alone.
        # Require the actual public TITLE to independently mention the topic;
        # otherwise general-feed items get mislabeled as Cat Magic leads.
        title_pattern = learning_radar.FOCUS[lane][0]
        strong_pattern = TITLE_GATES[lane]
        candidates = [p for p in eligible if lane in p["signals"] and p["key"] not in seen
                      and used_sources[str(p.get("source", ""))] < 2
                      and re.search(title_pattern, p["title"], re.I)
                      and re.search(strong_pattern, p["title"], re.I)]
        # Excerpts can be adversarial and generic titles are poor references.
        # Rank only topical title evidence and source kind; never excerpt score.
        candidates.sort(key=lambda p: (
            -(min(3, len(re.findall(strong_pattern, p["title"], re.I))) * 6
              + min(3, len(re.findall(title_pattern, p["title"], re.I))) * 2
              + WEIGHT[p["kind"]]),
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
            "creator_verified": False, "original_media_verified": False,
            "question_for_reviewer": question,
        })
    return {
        "schema": "LEON_CAT_MAGIC_RESEARCH_REPORT_V1",
        "status": "TRIAGE_ONLY_NOT_GAMEPLAY_ANALYSIS",
        "input_unique_posts": len(index["posts"]),
        "direct_platform_candidates": len(eligible),
        "proven_original_media": 0,
        "inspected_videos": 0, "observed_gameplay_findings": 0,
        "new_code_changes_authorized": False,
        "candidates": results,
        "unfilled_topics": [lane for lane, _, _ in LANES if not any(p["topic"] == lane for p in results)],
    }


def render(report: dict) -> str:
    lines = [
        "# Cat Magic research intelligence — evidence-gated", "",
        "**Current stage: metadata triage only. No video watched, game tested, model inspected, or verified design finding.**",
        "A direct platform URL does NOT establish original creator, video ownership, permission or reuse rights.",
        "This is a bounded reading queue, not an instruction to copy assets or automatically edit a Roblox game.", "",
        f"Indexed entries: {report['input_unique_posts']}; direct-platform links: {report['direct_platform_candidates']};",
        "Inspected videos: **0**; verified gameplay findings: **0**.", "",
        "## Highest-value direct-link checks (authorship unverified)", "",
    ]
    if not report["candidates"]:
        lines.append("No eligible direct-platform leads. Original author, media content and rights remain unknown.")
    for p in report["candidates"]:
        lines.extend([
            f"- **{p['priority']} · {clean(p['topic'])}:** [{clean(p['title'])}]({p['url']})",
            f"  - {p['kind']} · **UNVIEWED_METADATA** · creator/ownership UNVERIFIED · Check: {clean(p['question_for_reviewer'], 260)}",
        ])
    if report["unfilled_topics"]:
        lines.extend(["", "## Research gaps", ""])
        lines.extend("- " + clean(topic) + ": no qualifying direct-platform candidate" for topic in report["unfilled_topics"])
    lines.extend(["", "## Required before a verified improvement", "",
        "1. Inspect the original permitted source and record actual time-coded observations, creator, usage rights and uncertainty.",
        "2. Compare the observation to the **existing** Cat Magic first-session defect and choose ONE measurable code/scene change.",
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
    report = analyze(index)
    written = [
        save(OUTPUT / "cat_magic_research_report.json", json.dumps(report, indent=2, ensure_ascii=False) + "\n"),
        save(OUTPUT / "cat_magic_research_report.md", render(report) + "\n"),
    ]
    print("Updated" if any(written) else "Unchanged", "evidence-safe Cat Magic research report")


if __name__ == "__main__":
    main()
