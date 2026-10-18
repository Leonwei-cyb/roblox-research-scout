#!/usr/bin/env python3
"""Deterministic assessment of public source coverage; not vision/video understanding."""
from __future__ import annotations
import json
import re
from collections import Counter
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
MEDIA = ROOT / "watch/media_state.json"
OUT = ROOT / "watch/source_quality.md"
BAD = re.compile(r"free robux|join our discord|crack|keygen|download .{0,30} free", re.I)
ORIGINAL_HOSTS = {"www.youtube.com","youtube.com","youtu.be","www.tiktok.com",
                  "tiktok.com","www.instagram.com","instagram.com","x.com","www.x.com","twitter.com"}

def classify(row):
    u = urlparse(str(row.get("url","")))
    title = str(row.get("title",""))
    if u.scheme != "https" or not u.hostname:
        return "invalid"
    if BAD.search(title):
        return "promotional / risky title"
    if u.hostname == "news.google.com":
        return "indexed redirect (not original)"
    if u.hostname in ORIGINAL_HOSTS:
        path = u.path
        if (u.hostname in {"youtube.com","www.youtube.com"} and (path.startswith("/watch") or path.startswith("/shorts/"))) or (
            u.hostname == "youtu.be" and bool(path.strip("/"))) or (
            "tiktok.com" in u.hostname and re.fullmatch(r"/@[^/]+/video/\d+/?",path)) or (
            "instagram.com" in u.hostname and re.fullmatch(r"/(reel|p)/[\w-]+/?",path)) or (
            u.hostname in {"x.com","www.x.com","twitter.com"} and re.fullmatch(r"/[^/]+/status/\d+/?",path)):
            return "original video/post URL (unwatched)"
    return "public metadata / page"

def score(rows):
    counts = Counter(classify(row) for row in rows)
    total = len(rows)
    original = counts["original video/post URL (unwatched)"]
    indirect = counts["indexed redirect (not original)"]
    return counts, total, original, indirect

def report(rows):
    counts, total, original, indexed = score(rows)
    lines = ["# Source quality and usefulness audit", "",
        "**Public source metadata only.** No video was watched, no 3D model was graded.",
        "", "| Classification | Entries |", "|---|---:|"]
    for label in ["original video/post URL (unwatched)","public metadata / page",
                  "indexed redirect (not original)","promotional / risky title","invalid"]:
        lines.append("| "+label+" | "+str(counts[label])+" |")
    lines += ["", "Total sampled entries: **"+str(total)+"**.",
        "Direct-original share: **"+f"{(original / total * 100 if total else 0):.1f}"+"%** (still unwatched).",
        "Indexed redirects: **"+str(indexed)+"**. They require primary-source verification.",
        "", "## Actionable interpretation", "",
        "- Prefer curated original creator uploads and first-party Studio/DevForum content over broad Google News search results.",
        "- No ranking based on views, likes, search-index count or claims of gameplay quality.",
        "- Stop retrying consistently blocked feeds too frequently; inspect source_health.md and failure_triage.md.",
        "- Full visuals and gameplay remain dependent on permitted original footage and direct inspection.",
        ""]
    return "\n".join(lines)

def main():
    if not MEDIA.exists():
        print("No media_state.json; source-quality audit deferred")
        return
    state = json.loads(MEDIA.read_text(encoding="utf-8"))
    rows = state.get("items", [])
    if not isinstance(rows, list):
        raise ValueError("media state items must be a list")
    output = report(rows)
    if not OUT.exists() or OUT.read_text(encoding="utf-8") != output:
        OUT.write_text(output, encoding="utf-8")
    print("Source quality: "+str(score(rows)[2])+" direct links of "+str(len(rows))+" entries")
if __name__ == "__main__":
    main()
