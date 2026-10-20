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
FEEDS = ROOT / "watch/feeds.json"
OUT = ROOT / "watch/source_quality.md"
BAD = re.compile(r"free robux|join our discord|crack|keygen|download .{0,30} free|giving away|\bgiveaway\b|\bprank\b|\btroll\b", re.I)
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

def active_source_ids(config):
    """Source IDs media_scout.py would poll today (same naming as feed_sources)."""
    ids = {str(f.get("id")) for f in config.get("feeds", []) if f.get("id")}
    ids |= {str(f.get("id")) for f in config.get("news_queries", []) if f.get("id")}
    ids |= {str(f.get("id")) for f in config.get("app_charts", []) if f.get("id")}
    ids |= {"youtube-" + str(ch.get("channel_id")) for ch in config.get("youtube_channels", [])
            if ch.get("channel_id")}
    return ids

def publisher_of(row):
    """Where an indexed redirect really points, without resolving the redirect."""
    host = urlparse(str(row.get("publisher", ""))).hostname
    if host:
        return host
    title = str(row.get("title", ""))
    if " - " in title:
        suffix = title.rsplit(" - ", 1)[1].strip()
        if 0 < len(suffix) <= 40:
            return suffix.replace("|", "/") + " (title suffix)"
    return "unknown"

def pct(part, whole):
    return f"{(part / whole * 100 if whole else 0):.1f}%"

def report(rows, active_sources=None):
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
        ""]
    if active_sources is not None:
        active = [r for r in rows if str(r.get("source", "")) in active_sources]
        paused = [r for r in rows if str(r.get("source", "")) not in active_sources]
        _, a_total, a_original, a_indexed = score(active)
        lines += ["## Active configured sources", "",
            "The store keeps history from feeds that are no longer polled; this section counts only feeds in watch/feeds.json today.", "",
            "Active-source entries: **"+str(a_total)+"**; direct originals **"+str(a_original)+"**; indexed redirects **"+str(a_indexed)+"**.",
            "Active-source direct-original share: **"+pct(a_original, a_total)+"** (still unwatched).",
            "Entries from paused/unconfigured sources: **"+str(len(paused))+"**"
            + (" (" + ", ".join(sorted({str(r.get("source", "")) for r in paused})[:12]) + ")" if paused else "") + ".",
            ""]
    redirects = Counter(publisher_of(r) for r in rows if classify(r) == "indexed redirect (not original)")
    if redirects:
        lines += ["## Indexed redirects by publisher", "",
            "Google News redirect links are not resolved: the current article format needs Google's undocumented batchexecute endpoint, which this bot does not call. Search the publisher directly instead.", "",
            "| Publisher | Redirects |", "|---|---:|"]
        lines += ["| "+name+" | "+str(n)+" |" for name, n in sorted(redirects.items(), key=lambda kv: (-kv[1], kv[0]))[:12]]
        lines.append("")
    lines += ["## Actionable interpretation", "",
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
    active = active_source_ids(json.loads(FEEDS.read_text(encoding="utf-8"))) if FEEDS.exists() else None
    output = report(rows, active_sources=active)
    if not OUT.exists() or OUT.read_text(encoding="utf-8") != output:
        OUT.write_text(output, encoding="utf-8")
    print("Source quality: "+str(score(rows)[2])+" direct links of "+str(len(rows))+" entries")
if __name__ == "__main__":
    main()
