#!/usr/bin/env python3
"""Make a verifiable *watch-next list* from collected public feed metadata.

No AI. Never equates a Google News social index item with a watchable reel.
Video access and the quality of the actual footage remain UNVERIFIED.
"""
import json
import re
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "watch" / "media_state.json"
OUTPUT = ROOT / "watch" / "video_candidates.md"

POSITIVE = (
    ("roblox studio", 5), ("robloxdev", 5), ("game dev", 3),
    ("devlog", 4), ("showcase", 4), ("ui", 3),
    ("animation", 3), ("studio", 2), ("cat", 2),
    ("3d model", 3), ("playtest", 3), ("tycoon", 5),
    ("gameplay", 3), ("tutorial", 2), ("agentic", 3),
    ("build", 2), ("creation", 2), ("roblox", 3),
)
BAD = re.compile(
    r"(download .* free|crack|keygen|robux gift|"
    r"join (our )?discord|free robux|vpn|crypto giveaway|giving away|\bgiveaway\b|\bprank\b|\btroll\b|"
    r"\bfps cheats\b)", re.IGNORECASE
)


def kind(item):
    url = str(item.get("url", ""))
    parts = urlparse(url)
    if parts.scheme != "https":
        return None
    host, path = parts.hostname or "", parts.path
    if host in {"www.youtube.com", "youtube.com", "youtu.be"}:
        if path.startswith(("/watch", "/shorts/", "/live/")) or host == "youtu.be":
            return "YouTube video"
        return None
    if host in {"www.tiktok.com", "tiktok.com"} and re.search(r"/@[^/]+/video/\d+", path):
        return "TikTok original video"
    if host in {"www.instagram.com", "instagram.com"} and re.search(r"/(reel|p)/[A-Za-z0-9_-]+", path):
        return "Instagram original Reel/post"
    if host in {"x.com", "www.x.com", "twitter.com"} and re.search(r"/status/\d+", path):
        return "X original post"
    if host in {"www.reddit.com", "reddit.com"} and re.search(r"/comments/[a-z0-9]+/", path):
        # A community discussion is not a video. Keep a separately labeled lead
        # only when its title actually advertises a visual demonstration.
        title = str(item.get("title", "")).lower()
        if re.search(r"animated|animation|showcase|devlog|demo|trailer|video|clip|prototype|playtest", title):
            return "Community showcase post (video not confirmed)"
        return None
    return None


def score(item):
    text = (str(item.get("title", "")) + " " + str(item.get("excerpt", ""))).lower()
    if BAD.search(text):
        return -10
    return sum(weight for word, weight in POSITIVE if word in text)


def shortlist(items, limit=14):
    candidates = []
    for item in items:
        media_kind = kind(item)
        if not media_kind or score(item) < 4:
            continue
        candidates.append((score(item), item, media_kind))
    # Direct watchable videos first; unverified community posts never bury them.
    candidates.sort(key=lambda r: (r[2].startswith("Community "), -r[0],
                                    str(r[1].get("published", "")), str(r[1].get("title", ""))))
    output, seen = [], set()
    for _, item, media_kind in candidates:
        url = item.get("url", "")
        if url in seen:
            continue
        seen.add(url)
        output.append((item, media_kind))
        if len(output) >= limit:
            break
    return output


def report(items):
    picks = shortlist(items)
    indexed = [p for p in items if p.get("category", "").lower() in {
        "tiktok indexed leads", "instagram indexed leads", "instagram reels",
        "x_index", "youtube_index", "ui showcases", "3d models",
        "gameplay prototypes"
    } and not kind(p)]
    lines = [
        "# Watch next: Roblox videos and posts", "",
        "**Automatic metadata shortlist, NOT a review of the actual footage.** "
        "Watch originals before borrowing gameplay/UI/model ideas.", "",
        "Only direct YouTube videos or original social posts (plus labeled Reddit community posts) qualify. "
        "Indexed Google News redirects do **not** qualify as watchable videos.", "",
    ]
    if not picks:
        lines.append("No source-confirmed media links passed the filters.")
    for item, media_kind in picks:
        name = str(item.get("title", "Untitled")).replace("[", "\\[").replace("]", "\\]").replace("|", "\\|")
        label = media_kind
        if item.get("published"):
            label += " · " + str(item["published"])
        lines += [
            "- **[" + name[:145] + "](" + item["url"] + ")** — " + label
        ]
    lines += ["", "## Coverage gap", "",
        str(len(indexed)) + " indexed or general showcase leads were **not** promoted "
        "because a verified original video/post URL was missing. "
        "TikTok/Instagram/X URL restrictions remain; this number isn't a count of videos watched.", "",
        "For actual game/UI/3D quality, a reviewer must open the source and examine the footage. "
        "The no-AI scout is only the discovery stage.", ""]
    return "\n".join(lines)


def main():
    if not INPUT.exists():
        raise SystemExit("No media_state.json yet. Run the media scout first.")
    items = json.loads(INPUT.read_text(encoding="utf-8")).get("items", [])
    new = report(items)
    if not OUTPUT.exists() or OUTPUT.read_text(encoding="utf-8") != new:
        OUTPUT.write_text(new, encoding="utf-8")
        print("Saved source-linked video candidate shortlist.")
    else:
        print("No changed video candidates.")


if __name__ == "__main__":
    main()
