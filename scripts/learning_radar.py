#!/usr/bin/env python3
"""Offline per-post research triage for the existing Mac scout.

No feeds, downloads, browser automation, model calls or footage viewing. This
is a metadata index, NOT a report of observed gameplay or learned mechanics.
"""
from __future__ import annotations
import json
import re
from collections import Counter
from pathlib import Path
from urllib.parse import urlsplit, parse_qs

import active_game

ROOT = Path(__file__).resolve().parents[1]
MEDIA = ROOT / "watch/media_state.json"
OUT = ROOT / "watch"

# General Roblox signal patterns. The questions shown for each live in
# active_game.PROFILES, so a held game never gets fresh current-game tasks.
FOCUS = {
    "first-session and mobile":
        r"\bonboard\w*|\btutorial\b|\bretention\b|\bleav\w*|\bmobile\b|\bphone\b|\bfirst.minute\b|\bux\b",
    "board game and turn flow":
        r"\bboard.?games?\b|\bcatan\b|\bcolonists?\b|\bhex(es|agon\w*)?\b|\bturn.based\b|\bdice\b",
    "building and purchases":
        r"\btycoon\b|\bpurchas\w*|\bconstruct\w*|\bbuild\w*|\bupgrade\w*|\bbuy\b|\bpad\b",
    "economy and income":
        r"\btuition\b|\bincome\b|\bearn\w*|\beconom\w*|\bcoins?\b|\bcash\b|\bidle\b",
    "UI and menus":
        r"\bui\b|\bhud\b|\bshop\b|\bmenu\b|\binventory\b|\bhotbar\b|\blayout\b",
    "animation and audio":
        r"\bcats?\b|\bpets?\b|\banimat\w*|\bvfx\b|\bsfx\b|\bsounds?\b|\btween\w*",
    "world and visual design":
        r"\bgrass\b|\bterrain\b|\bclassroom\b|\benvironment\b|\blighting\b|\b3d\b|\bmodels?\b",
    "genres and successful loops":
        r"\bsteal\b|\bsimulator\b|\bviral\b|\brebirth\b|\bprestige\b|\brare\b|\bhatch\b|\bclicker\b|\btrend\b",
    "player feedback and marketing":
        r"\bfeedback\b|\breviews?\b|\bplayers?\b|\bads?\b|\bimpressions?\b|\bthumbnail\b|\bctr\b|\bfunnel\b",
    "tools and performance":
        r"\bplugin\b|\bluau\b|\bscript\w*|\bperformance\b|\bserver\b|\bmemory\b|\bsecurity\b|\bstudio\b",
}
HOSTS = {
    "www.youtube.com": "youtube", "youtube.com": "youtube", "youtu.be": "youtube",
    "www.instagram.com": "instagram", "instagram.com": "instagram",
    "www.tiktok.com": "tiktok", "tiktok.com": "tiktok",
    "x.com": "x", "www.x.com": "x", "twitter.com": "x", "www.twitter.com": "x",
    "devforum.roblox.com": "devforum", "reddit.com": "reddit", "www.reddit.com": "reddit",
    "news.google.com": "index-only",
}

def identity(url):
    """Same original post gets one key even with common redirect/Shorts aliases."""
    try:
        p = urlsplit(str(url))
        if p.scheme != "https" or not p.hostname or p.username or p.password:
            return None, None
        host, path = p.hostname.lower(), p.path.rstrip("/")
        kind = HOSTS.get(host, "web")
        if kind == "youtube":
            video = (parse_qs(p.query).get("v") or [""])[0] if path == "/watch" else (
                path.rsplit("/", 1)[-1] if host == "youtu.be" or path.startswith("/shorts/") else "")
            if re.fullmatch(r"[A-Za-z0-9_-]{11}", video):
                return "youtube:" + video, kind
        if kind == "x":
            m = re.fullmatch(r"/[A-Za-z0-9_]{1,15}/status/(\d+)", path)
            if m: return "x:" + m[1], kind
        if kind == "instagram":
            m = re.fullmatch(r"/(?:p|reel)/([A-Za-z0-9_-]+)", path)
            if m: return "instagram:" + m[1], kind
        if kind == "tiktok":
            m = re.fullmatch(r"/@[^/]+/video/(\d+)", path)
            if m: return "tiktok:" + m[1], kind
        if kind in {"x", "instagram", "tiktok", "youtube"}:
            return None, None  # A creator profile / hashtag page is not an individual post.
        if kind == "reddit":
            m = re.match(r"/r/[^/]+/comments/([a-z0-9]+)(?:/|$)", path, re.I)
            if m: return "reddit:" + m[1].lower(), kind
        if kind == "devforum":
            m = re.fullmatch(r"/t/(?:[^/]+/)?(\d+)(?:/(\d+))?", path)
            if m: return "devforum:" + m[1] + ":" + (m[2] or "1"), kind
        return host + path + (("?" + p.query) if kind == "web" else ""), kind
    except ValueError:
        return None, None

def triage(items):
    """Read every existing record; canonicalize and tag without pretending to see it."""
    seen, raw = {}, 0
    for item in items:
        if not isinstance(item, dict): continue
        raw += 1
        key, kind = identity(item.get("url", ""))
        title = str(item.get("title") or "")[:220].strip()
        if not key or not title: continue
        excerpt = str(item.get("excerpt") or "")
        signals = []
        score = 4 if kind in ("youtube", "tiktok", "instagram", "x") else (
            2 if kind in ("devforum", "reddit") else 0)
        for label, pattern in FOCUS.items():
            in_title = bool(re.search(pattern, title, re.I))
            if in_title or re.search(pattern, excerpt, re.I):
                signals.append(label)
                score += 3 if in_title else 1
        if kind == "index-only": score = 0
        rec = dict(key=key, url=str(item["url"]), title=title, source=str(item.get("source", "")),
                   published=str(item.get("published", "")), kind=kind,
                   signals=signals, score=score, evidence="UNVIEWED_METADATA")
        prev = seen.get(key)
        if prev is None or (score, rec["published"]) > (prev["score"], prev["published"]):
            seen[key] = rec
    ranked = sorted(seen.values(), key=lambda x: (-x["score"], x["key"]))
    return dict(records_read=raw, unique_posts=len(ranked), reviewed_posts=0, posts=ranked)

def question(game, label):
    if game not in active_game.PROFILES:
        return active_game.NO_GAME_QUESTION
    return active_game.PROFILES[game]["radar"].get(label, active_game.GENERIC_QUESTION)


def render(result, game=None):
    """game=None (unresolved authority) keeps the leads but proposes no game tasks."""
    name = active_game.PROFILES[game]["name"] if game in active_game.PROFILES else None
    lines = ["# Leon media learning queue (Mac research scout)", "",
        f"Active game: **{name}**." if name else "Active game: **UNKNOWN**. No game-specific tests are proposed.", "",
        "**Metadata-only. No videos watched, posts fully read, audio heard or gameplay verified.**",
        "Every captured public lead was triaged and deduplicated; this is NOT every post",
        "on X, Instagram, TikTok or the wider internet. Inaccessible sources stay UNKNOWN.",
        "",
        f"Records processed: {result['records_read']}; unique posts: {result['unique_posts']}; fully reviewed: 0.", ""]
    used = set()  # one original post per displayed queue, even across topics
    counts = Counter(p["kind"] for p in result["posts"])
    lines += ["## Saved source coverage", ""]
    lines += ["- " + kind + ": " + str(n) for kind, n in sorted(counts.items())]
    for label in FOCUS:
        test = question(game, label)
        lines += ["", "## " + label.title(), ""]
        selected = [p for p in result["posts"] if label in p["signals"] and
                    p["kind"] != "index-only" and p["key"] not in used][:2]
        if not selected: lines.append("- No relevant direct candidate in stored leads.")
        for p in selected:
            used.add(p["key"])
            # Public feed fields are untrusted, even though collection is restricted.
            name = (re.sub(r"[\x00-\x1f\x7f]+", " ", p["title"])
                    .replace("\\", "\\\\").replace("[", "\\[").replace("]", "\\]"))
            url = p["url"]
            if any(c in url for c in "()<> \n\r\t"):
                continue
            lines.append(f"- [{name}]({url}) — {p['kind']}; **unviewed metadata**. Proposed test: {test}")
    lines += ["", "## Evidence required to turn a candidate into learning", "",
        "1. Open original source with creator/date; for gameplay video, record actually viewed timestamps.",
        "2. Note specific observed UI, mechanics, animation and audio; flag each missing or inferred element.",
        "3. Explain WHY it matters and propose one " + (name or "active-game") + " test with measurable pass/fail.",
        "4. Track ADOPT / TEST / REJECT only after source review and in-game evidence.",
        "5. Respect licenses and platform access; do not automate signed-in Chrome, download unpermitted media or bypass restrictions.", ""]
    return "\n".join(lines)

def save(path, body):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_file() and path.read_text(encoding="utf-8") == body: return False
    path.write_text(body, encoding="utf-8")
    return True

def main():
    data = json.loads(MEDIA.read_text(encoding="utf-8"))
    if not isinstance(data.get("items"), list):
        raise ValueError("media_state.items must be a list")
    result = triage(data["items"])
    a = save(OUT / "learning_index.json", json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    game, _ = active_game.resolve()
    b = save(OUT / "learning_queue.md", render(result, game) + "\n")
    print("Updated" if a or b else "Unchanged", "learning radar; metadata only")

if __name__ == "__main__":
    main()
