#!/usr/bin/env python3
"""Curated creator-source digest from existing public feed metadata. ZERO model calls.

A creator mentioned by an indexed search result is NOT assumed to have authored
that post. Account links are verified separately from individual media.
"""
import json
import re
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
CREATORS = ROOT / "watch" / "creators.json"
INPUT = ROOT / "watch" / "media_state.json"
OUTPUT = ROOT / "watch" / "creator_digest.md"
MAX_ROWS = 5


def clean(s, limit=165):
    return (str(s or "").replace("\n", " ").replace("\r", " ")
            .replace("[", "\\[").replace("]", "\\]")
            .replace(chr(96), "'").replace("|", "\\|"))[:limit]


def matches(row, creator):
    src = str(row.get("source", ""))
    channel = str(creator.get("youtube_channel_id", "") or creator.get("candidate_youtube_channel_id", ""))
    if channel and src == "youtube-" + channel:
        return "channel upload — creator identity check" if creator.get("candidate_youtube_channel_id") else "verified channel upload"
    # Never match a creator because the SEARCH QUERY in the source label contains
    # their name. A title/excerpt/author needs to mention the creator independently.
    text = " ".join(str(row.get(k, "")) for k in ("creator", "title", "excerpt")).lower()
    for alias in creator.get("aliases", []):
        name = str(alias).lower()
        # Avoid generic "Steal An Egg" matching random fan content as developer posts.
        if len(name) < 6 or name in {"steal an egg", "roblox", "game"}:
            continue
        if re.search(r"(?<![a-z0-9])@?" + re.escape(name) + r"(?![a-z0-9])", text):
            host = urlparse(str(row.get("url", ""))).hostname or ""
            if host.endswith("news.google.com"):
                return "indexed public mention — authorship NOT verified"
            return "public source mention — authorship NOT verified"
    return None


def group(creators, records):
    result = []
    for c in creators:
        matched = [(row, matches(row, c)) for row in records]
        matched = [(r, label) for r, label in matched if label]
        matched.sort(key=lambda x: (str(x[0].get("published", "")),
                                    str(x[0].get("title", ""))), reverse=True)
        # Stable priority: real channel uploads first, then source mentions, then
        # indexed leads. Within each class, newest posts first.
        matched.sort(key=lambda x: (
            0 if "channel upload" in x[1] else
            1 if "source mention" in x[1] else 2
        ))
        result.append((c, matched[:MAX_ROWS], len(matched)))
    return result


def render(creators, records):
    lines = [
        "# Developer source watchlist — public evidence only", "",
        "Automatically updated creator account links and feed/index leads; "
        "**no Instagram Reel, TikTok or YouTube video was watched by this program**.",
        "A search-result mention is NOT a creator-authored post. Distinct channel handles "
        "are not silently treated as one account.", ""
    ]
    for creator, posts, count in group(creators, records):
        lines.extend(["## " + clean(creator["label"]), "",
                      "Research focus: " + clean(creator.get("focus", ""), 250), "",
                      "Account provenance: [" + clean(creator.get("source_of_identity", ""), 80) +
                      "](" + creator.get("source_of_identity", "") + ")", "",
                      "**Account links** (public profile URLs, not guaranteed feed access):"])
        for account in creator.get("accounts", []):
            lines.append("- [" + clean(account["platform"]) + "](" + account["url"] +
                         ") — " + clean(account.get("provenance", ""), 100) +
                         "; direct posts: " + clean(account.get("direct_posts_access", ""), 85))
        lines.extend(["", "**Collected media leads:** " + str(count) + " matched metadata records."])
        if not posts:
            lines.append("- None verified in currently collected public feeds.")
        for row, status in posts:
            url = str(row.get("url", ""))
            if not url.startswith("https://"):
                continue
            lines.append("- [" + clean(row.get("title"), 125) + "](" + url + ") — " +
                         clean(status, 90) + (" · " + clean(row.get("published"), 15) if row.get("published") else ""))
        lines.append("")
    lines.extend([
        "---", "",
        "Before adding any footage insight to a game: examine the ORIGINAL public video/post "
        "and record timecodes, observable mechanics and licensing. "
        "No scraping private feeds, logged-in cookies or restricted media.", ""
    ])
    return "\n".join(lines)


def main():
    if not CREATORS.exists() or not INPUT.exists():
        raise SystemExit("Creator config/media state missing; run public scout first.")
    creators = json.loads(CREATORS.read_text(encoding="utf-8")).get("creators", [])
    records = json.loads(INPUT.read_text(encoding="utf-8")).get("items", [])
    report = render(creators, records)
    if not OUTPUT.exists() or OUTPUT.read_text(encoding="utf-8") != report:
        OUTPUT.write_text(report, encoding="utf-8")
        print("Updated sourced creator-watch digest.")
    else:
        print("Creator watch unchanged.")


if __name__ == "__main__":
    main()
