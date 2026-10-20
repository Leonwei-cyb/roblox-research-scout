#!/usr/bin/env python3
"""Three deterministic research bots: review queue, topic mentions and source coverage.

Reads only existing public feed metadata. No model calls, videos, external logins
or private repo access. A source link is NOT proof its content was watched.
"""
from __future__ import annotations
import json
import re
from collections import Counter
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
MEDIA = ROOT / "watch/media_state.json"
HEALTH = ROOT / "watch/source_health.md"
OUT = ROOT / "watch"

FOCUS = {
    "Game loops / progression": ["tycoon", "simulator", "idle", "steal", "upgrade", "progression", "puzzle", "pet", "defense", "strategy"],
    "UI / menus / effects": ["ui", "hud", "menu", "shop", "button", "interface", "tween", "effects", "vfx", "animation"],
    "3D / models / environments": ["model", "blender", "texture", "building", "builds", "terrain", "mesh", "map", "scenery", "3d"],
    "Claude / automation / testing": ["claude", "mcp", "agentic", "plugin", "luau", "playtest", "automati", "github", "tool"],
}
WORDS = {
    "Tycoon / idle": ["tycoon", "dropper", "idle", "automation", "conveyor"],
    "Steal / risk": ["steal", "stolen", "escape", "chase", "snatch"],
    "Pets / collection": ["pet", "collection", "egg", "hatch", "rarity"],
    "Progression / upgrades": ["upgrade", "rebirth", "prestige", "level", "progression"],
    "UI / UX": ["ui", "ux", "menu", "hud", "interface", "shop"],
    "3D / art": ["blender", "texture", "3d", "model", "building", "map", "terrain"],
    "Animation / feel": ["animation", "animate", "tween", "impact", "vfx", "feel"],
}
SPAM = re.compile(r"free robux|robux giveaway|giving away|\bgiveaway\b|\bprank\b|\btroll\b|crack|keygen|join (our )?discord|download.*free.*windows", re.I)

def safe(s, n=145):
    return re.sub(r"[\x00-\x1f\x7f]+", " ", str(s or ""))[:n].replace("[", "\\[").replace("]", "\\]").replace("|", "\\|").strip()

def media_url(url):
    u = urlparse(str(url))
    host, path = u.hostname or "", u.path
    if u.scheme != "https":
        return False
    if host in {"www.youtube.com", "youtube.com"}:
        return path.startswith("/shorts/") or (path == "/watch" and "v=" in u.query)
    if host == "youtu.be":
        return bool(path.strip("/"))
    if host in {"www.tiktok.com", "tiktok.com"}:
        return bool(re.fullmatch(r"/@[^/]+/video/\d+/?", path))
    if host in {"www.instagram.com", "instagram.com"}:
        return bool(re.fullmatch(r"/(reel|p)/[\w-]+/?", path))
    if host in {"www.x.com", "x.com", "twitter.com"}:
        return bool(re.fullmatch(r"/[^/]+/status/\d+/?", path))
    return False

def matches(item, terms):
    text = (str(item.get("title", "")) + " " + str(item.get("excerpt", ""))).lower()
    if SPAM.search(text):
        return 0
    return sum(1 for x in terms if re.search(r"\b" + re.escape(x) + r"\w*\b", text))

def choose(items, per_category=3):
    result = {}
    for cat, terms in FOCUS.items():
        candidates = []
        for item in items:
            u = urlparse(str(item.get("url", "")))
            if u.scheme != "https" or not u.hostname or not str(item.get("title", "")).strip():
                continue
            # Broad Google News search redirects made up most collected entries;
            # they are coverage metadata, not useful original-source build leads.
            # Keep them in media_state and source_quality, NEVER promote them to
            # the limited implementation-facing inspection queue.
            if u.hostname == "news.google.com":
                continue
            # Visual-reference queues should prefer inspectable creator videos
            # and first-party Roblox developer discussions, not novice Reddit
            # troubleshooting posts labeled "UI" merely due to one word.
            if cat in {"UI / menus / effects", "3D / models / environments"} and not media_url(item["url"]) and u.hostname != "devforum.roblox.com":
                continue
            # The title must independently establish task relevance.
            count = matches({"title": item.get("title", ""), "excerpt": ""}, terms)
            if not count:
                continue
            title = str(item.get("title", "")).lower()
            if cat in {"UI / menus / effects", "3D / models / environments"} and (
                title.startswith(("missing ", "how to get ", "looking for ",
                    "any good ", "please help ", "help with ", "question about "))
                or "error" in title or "not working" in title
            ):
                continue
            weight = 10 if media_url(item["url"]) else 5
            weight += 3 if str(item.get("source", "")).startswith("youtube-") else 0
            candidates.append((count * 2 + weight, item))
        candidates.sort(key=lambda a: (a[0], str(a[1].get("published", ""))), reverse=True)
        result[cat] = []
        seen, used_sources = set(), Counter()
        for score, item in candidates:
            src = str(item.get("source", ""))
            if item["url"] in seen or used_sources[src] >= 1:
                continue
            seen.add(item["url"])
            used_sources[src] += 1
            result[cat].append((score, item))
            if len(result[cat]) == per_category:
                break
    return result

def review_queue(items):
    lines = ["# What to inspect next", "",
        "**Metadata triage only. Videos not watched; design/quality not assessed.**",
        "Only direct media or primary discussion pages enter this small queue; indexed Google News redirects are excluded.", "Only inspect one lead when it unlocks a concrete fix in an existing game; this list is not a to-do mandate.", ""]
    for cat, picks in choose(items).items():
        lines.extend(["## " + cat, ""])
        for _, item in picks:
            link = item["url"]
            status = "Original media link, not watched" if media_url(link) else (
                "Indexed lead only" if urlparse(link).hostname == "news.google.com" else "Public text/page, video not confirmed")
            lines.append("- **[" + safe(item["title"]) + "](" + link + ")** — " + status)
        if not picks:
            lines.append("No supported leads in current feeds.")
        lines.append("")
    return "\n".join(lines)

def topic_signals(items):
    counts, examples = Counter(), {k: [] for k in WORDS}
    for item in items:
        if SPAM.search(str(item.get("title", ""))):
            continue
        for cat, words in WORDS.items():
            if matches({"title": item.get("title", ""), "excerpt": ""}, words):
                counts[cat] += 1
                if len(examples[cat]) < 2 and str(item.get("url", "")).startswith("https://"):
                    examples[cat].append("[" + safe(item["title"], 76) + "](" + item["url"] + ")")
    lines = ["# Topic mentions in our public feeds", "",
        "**Biased sampled metadata, NOT Roblox CCU, user interest, gameplay quality or a general trend forecast.**",
        "", "| Topic | Mention count | Source examples |", "|---|---:|---|"]
    for cat, count in sorted(counts.items(), key=lambda a: (-a[1], a[0])):
        lines.append("| " + cat + " | " + str(count) + " | " + "; ".join(examples[cat]) + " |")
    return "\n".join(lines) + "\n"

def coverage_audit(items, health):
    direct = sum(media_url(x.get("url", "")) for x in items)
    indexed = sum(urlparse(str(x.get("url", ""))).hostname == "news.google.com" for x in items)
    problems = [x[2:] for x in health.splitlines() if x.startswith("- ") and re.search(r"HTTP 4\d\d|timed out|unavailable", x, re.I)]
    lines = ["# Coverage audit", "",
        "Links and metadata collected; original social videos are NOT automatically played.", "",
        "| Observation | Count |", "|---|---:|",
        "| Saved source entries | " + str(len(items)) + " |",
        "| Original media URLs | " + str(direct) + " |",
        "| Indexed redirects, original unknown | " + str(indexed) + " |",
        "| Failed feeds | " + str(len(problems)) + " |", "",
        "## Failures to resolve", ""]
    lines.extend("- " + safe(x, 200) for x in problems)
    lines.extend(["", "## Actions", "",
        "- Improve source provenance and original links; avoid promotional or unrelated headline spam.",
        "- Respect platform rate limits. Never put personal Instagram/TikTok/X cookies in public CI.",
        "- Use the LOCAL video lab for authorized video clips and sampled visual evidence.", ""])
    return "\n".join(lines)

def save(path, content):
    content = content.rstrip() + "\n"
    if path.exists() and path.read_text(encoding="utf-8") == content:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return True

def main():
    if not MEDIA.is_file():
        print("Run media_scout.py first; no source state.")
        return
    records = json.loads(MEDIA.read_text(encoding="utf-8")).get("items", [])
    if not isinstance(records, list):
        raise ValueError("media_state.json items must be a list")
    health = HEALTH.read_text(encoding="utf-8") if HEALTH.is_file() else ""
    for name, body in [
        ("review_queue.md", review_queue(records)),
        ("topic_signals.md", topic_signals(records)),
        ("coverage_audit.md", coverage_audit(records, health)),
    ]:
        print(("Updated" if save(OUT / name, body) else "Unchanged"), name)
    # Existing Mac hourly refresh: tag every captured post, but never claim
    # metadata represents inspected videos, gameplay or audio.
    import learning_radar
    learning_radar.main()
    # One research schedule, three stages: collect -> triage -> evidence-safe report.
    # This stage reads existing public metadata; it NEVER inspects a video or sends instructions to Codex.
    import research_reporter
    research_reporter.main()

if __name__ == "__main__":
    main()
