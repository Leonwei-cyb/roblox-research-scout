#!/usr/bin/env python3
"""Offline original-source shortlist for publicly indexed Instagram/X leads.

This is *triage*, not a social scraper or footage reviewer. Never use cookies,
headless account access, proxies, search redirects as source evidence, or media
downloads. Input is the scout's existing public metadata and creator register.
"""
from __future__ import annotations
import json
import re
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "watch" / "social_original_shortlist.md"
MAX_PER_CREATOR = 4
SOCIAL = {"instagram", "x"}
IGNORE = re.compile(r"free robux|giveaway|\bprank\b|\btroll\b|keygen", re.I)

def url_kind(value):
    try:
        u = urlparse(str(value))
        if u.scheme != "https" or u.username or u.password:
            return None
        host = (u.hostname or "").lower()
        path = u.path.rstrip("/")
        if host in {"x.com", "www.x.com", "twitter.com", "www.twitter.com"} and re.fullmatch(r"/[A-Za-z0-9_]{1,15}/status/\d+", path):
            return "x"
        if host in {"instagram.com", "www.instagram.com"} and re.fullmatch(r"/(p|reel)/[A-Za-z0-9_-]+", path):
            return "instagram"
        if host in {"youtube.com", "www.youtube.com"} and (re.fullmatch(r"/shorts/[A-Za-z0-9_-]+", path) or (path == "/watch" and re.search(r"(?:^|&)v=[A-Za-z0-9_-]+(?:&|$)", u.query))):
            return "youtube"
    except (TypeError, ValueError):
        pass
    return None

def clean(value, n=155):
    return re.sub(r"[\x00-\x1f\x7f]+", " ", str(value or "")).replace("[", "\\[").replace("]", "\\]").replace("|", "\\|")[:n]

def creator_handles(creator):
    result = set()
    for account in creator.get("accounts", []):
        if account.get("platform") in SOCIAL:
            u = urlparse(account.get("url", ""))
            if u.hostname in {"x.com", "www.x.com", "instagram.com", "www.instagram.com"}:
                result.add((account["platform"], u.path.strip("/").lower()))
    return result

def shortlist(creators, items):
    output = []
    for creator in creators:
        handles = creator_handles(creator)
        if not handles:
            continue
        direct, crosspost = [], []
        channel = creator.get("youtube_channel_id")
        candidates = set()
        for item in items:
            url = str(item.get("url", ""))
            kind = url_kind(url)
            if not kind or url in candidates or IGNORE.search(str(item.get("title", ""))):
                continue
            candidates.add(url)
            path = urlparse(url).path.split("/")
            # A direct social post URL under an exact registered handle is a
            # candidate URL, NOT proof the video exists or was watched.
            handle = path[1].lower() if len(path) > 1 else ""
            if (kind, handle) in handles:
                direct.append(item)
            elif kind == "youtube" and channel and item.get("source") == "youtube-" + channel:
                crosspost.append(item)
        sortkey = lambda it: (str(it.get("published", "")), str(it.get("title", "")))
        output.append((creator, sorted(direct, key=sortkey, reverse=True)[:MAX_PER_CREATOR],
                       sorted(crosspost, key=sortkey, reverse=True)[:MAX_PER_CREATOR]))
    return output

def render(creators, items):
    lines = ["# Instagram/X original-source shortlist (offline)", "",
        "**Candidate URLs only; no posts or videos opened, viewed, authenticated, or downloaded.**",
        "A URL under a registered handle is stronger provenance than a search-result mention,",
        "but does NOT prove that the author posted this particular content.",
        "A YouTube upload by the same creator is a *cross-platform alternative*,",
        "not proof it is the identical Instagram/X post. Zero matches means NO verified direct posts.",
        ""]
    direct_total = alternate_total = 0
    for c, direct, alternate in shortlist(creators, items):
        direct_total += len(direct); alternate_total += len(alternate)
        lines += ["## " + clean(c.get("label", c.get("id"))), "",
                  "Focus: " + clean(c.get("focus", "")), "",
                  "**Direct Instagram/X post URL candidates:**"]
        lines += ["- [" + clean(it.get("title")) + "](" + it["url"] + ") — URL matches registered profile; media NOT viewed" for it in direct]
        if not direct: lines.append("- None found in current index.")
        lines += ["", "**Creator-channel YouTube alternatives (NOT matched to social post):**"]
        lines += ["- [" + clean(it.get("title")) + "](" + it["url"] + ") — indexed channel upload; NOT viewed" for it in alternate]
        if not alternate: lines.append("- None found with confirmed channel ID.")
        lines.append("")
    lines += [f"**Totals:** {direct_total} direct URL candidates; {alternate_total} separate creator-channel YouTube alternatives (max {MAX_PER_CREATOR} per creator).", "",
              "For Cat Magic PC-first, inspect permitted original media, verify exact author and timestamps, then record specific build/animation/UI observations. Do not treat indexed metadata or cross-posts as gameplay observations.", ""]
    return "\n".join(lines)

def main():
    creators = json.loads((ROOT / "watch/creators.json").read_text(encoding="utf-8"))["creators"]
    items = json.loads((ROOT / "watch/media_state.json").read_text(encoding="utf-8")).get("items", [])
    result = render(creators, items)
    if not OUTPUT.exists() or OUTPUT.read_text(encoding="utf-8") != result:
        OUTPUT.write_text(result, encoding="utf-8")
        print("Wrote social original-source shortlist.")
    else:
        print("Social original-source shortlist unchanged.")

if __name__ == "__main__":
    main()
