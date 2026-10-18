#!/usr/bin/env python3
"""Public feed collector, without GPT/Claude/Codex calls or third-party packages.

Keeps source attribution and coverage failures. Reports are discovery leads,
NOT evidence that an AI watched a video or conducted an in-depth gameplay review.
"""

from __future__ import annotations

import hashlib
import html
import json
import os
import re
import sys
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode, urlparse, urlunparse, parse_qsl
from urllib.request import Request, HTTPRedirectHandler, build_opener

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "watch" / "feeds.json"
STATE = ROOT / "watch" / "media_state.json"
BRIEF = ROOT / "watch" / "media_brief.md"
HEALTH = ROOT / "watch" / "source_health.md"
COOLDOWNS = ROOT / "watch" / "media_cooldowns.json"

# Explicitly authorized public metadata/feeds, not an arbitrary web spider.
ALLOWED_HOSTS = {
    "raw.githubusercontent.com", "devforum.roblox.com", "www.reddit.com",
    "news.google.com", "www.youtube.com",
    "rss.marketingtools.apple.com", "rss.applemarketingtools.com"
}
MAX_BYTES = 1_250_000
MAX_STORED = 600
USER_AGENT = "Roblox-Research-Public-Feed-Monitor/1.0 (+https://github.com/Leonwei-cyb/Roblox-Research)"


def clean(value, size=360):
    if value is None:
        return ""
    text = html.unescape(re.sub(r"<[^>]+>", " ", str(value)))
    text = re.sub(r"\s+", " ", text).strip()
    return text[:size]


def markdown(value, size=220):
    return clean(value, size).replace("\\", "\\\\").replace("[", "\\[").replace("]", "\\]").replace("|", "\\|").replace(chr(96), "'")


def canonical(url):
    """Strip only marketing parameters, preserve content identifiers."""
    u = urlparse(url)
    if u.scheme != "https" or not u.netloc or u.username or u.password:
        return ""
    query = urlencode([
        (k, v) for k, v in parse_qsl(u.query, keep_blank_values=True)
        if not k.lower().startswith("utm_") and k.lower() not in {"fbclid", "gclid"}
    ])
    return urlunparse(("https", u.netloc.lower(), u.path or "/", "", query, ""))


def make_id(record):
    # Identity follows an ORIGINAL/canonical source URL, not a title:
    # different Roblox videos called "Update" must remain distinct.
    # Identical Google News indexed URLs across search queries still dedupe.
    return hashlib.sha256(canonical(record["url"]).encode("utf-8")).hexdigest()[:24]


def parse_time(value):
    if not value:
        return ""
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc).strftime("%Y-%m-%d")
    except (ValueError, TypeError, OverflowError):
        try:
            return parsedate_to_datetime(value).astimezone(timezone.utc).strftime("%Y-%m-%d")
        except (ValueError, TypeError, OverflowError):
            return ""


def local(tag):
    return tag.rsplit("}", 1)[-1]


def child(element, names):
    wanted = set(names)
    for node in element:
        if local(node.tag) in wanted:
            return node
    return None


def ctext(element, names):
    node = child(element, names)
    if node is None:
        return ""
    return clean(" ".join(node.itertext()))


def parse_feed(xml_bytes, source, limit=20):
    if b"<!DOCTYPE" in xml_bytes.upper():
        raise ValueError("DTD declarations are disabled")
    root = ET.fromstring(xml_bytes)
    if local(root.tag) not in {"rss", "RDF", "feed"}:
        raise ValueError("Unrecognized RSS/Atom root")
    records = []
    for item in root.iter():
        if local(item.tag) not in {"item", "entry"}:
            continue
        title = ctext(item, ["title"])
        node = child(item, ["link"])
        link = (node.get("href", "") if node is not None else "") or (
            clean(node.text) if node is not None else ""
        )
        link = canonical(link)
        if not title or not link:
            continue
        description = ctext(item, ["summary", "description", "content"])
        published = parse_time(ctext(item, ["published", "updated", "pubDate", "date"]))
        record = {
            "source": source["id"], "label": source["label"],
            "category": source["category"], "title": title[:200],
            "url": link, "published": published,
            "excerpt": description[:300],
            "creator": ctext(item, ["author"])[:120]
        }
        record["id"] = make_id(record)
        records.append(record)
        if len(records) >= limit:
            break
    return records


class RestrictedRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        u = urlparse(newurl)
        if u.scheme != "https" or u.hostname not in ALLOWED_HOSTS:
            raise ValueError("Redirect to disallowed hostname")
        return super().redirect_request(request, fp, code, msg, headers, newurl)


def parse_apple_chart(data, source, limit=20):
    """Only games in Apple's general top-free *apps* list; not a full game ranking."""
    obj = json.loads(data.decode("utf-8"))
    apps = obj.get("feed", {}).get("results", [])
    if not isinstance(apps, list):
        raise ValueError("Apple feed results not a list")
    output = []
    for rank, app in enumerate(apps, 1):
        genres = app.get("genres", []) or []
        is_game = any(str(g.get("genreId", "")) == "6014" or
                      str(g.get("name", "")).lower() == "games"
                      for g in genres if isinstance(g, dict))
        if not is_game:
            continue
        title, url = clean(app.get("name"), 180), canonical(app.get("url", ""))
        if not title or not url:
            continue
        rec = {
            "source": source["id"], "label": source["label"],
            "category": source["category"], "title": title,
            "url": url, "published": "",
            "excerpt": "General top-free app chart position " + str(rank)
                    + "; developer " + clean(app.get("artistName", ""), 100)
                    + ". Genre-filtered subset; not the full games-only chart."
        }
        rec["id"] = make_id(rec)
        output.append(rec)
        if len(output) >= limit:
            break
    return output


def fetch_url(url, timeout=12):
    parts = urlparse(url)
    if parts.scheme != "https" or parts.hostname not in ALLOWED_HOSTS:
        raise ValueError("Disallowed source hostname")
    req = Request(url, headers={
        "User-Agent": USER_AGENT, "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml;q=0.9"
    })
    try:
        with build_opener(RestrictedRedirect()).open(req, timeout=timeout) as response:
            if response.geturl() and urlparse(response.geturl()).hostname not in ALLOWED_HOSTS:
                raise ValueError("Feed redirected to disallowed hostname")
            data = response.read(MAX_BYTES + 1)
            if len(data) > MAX_BYTES:
                raise ValueError("Oversized feed")
            return data
    except HTTPError as exc:
        raise RuntimeError("HTTP " + str(exc.code)) from exc
    except URLError as exc:
        raise RuntimeError("Network/availability error") from exc


def google_news_url(query):
    return "https://news.google.com/rss/search?" + urlencode({
        "q": query, "hl": "en-CA", "gl": "CA", "ceid": "CA:en"
    })


def feed_sources(config):
    for f in config.get("feeds", []):
        yield dict(f)
    for f in config.get("news_queries", []):
        yield {
            "id": f["id"], "category": f["category"],
            "label": "Google News indexed: " + f["query"],
            "url": google_news_url(f["query"])
        }
    for f in config.get("app_charts", []):
        yield dict(f, format="apple_json")
    for ch in config.get("youtube_channels", []):
        channel_id = ch.get("channel_id", "")
        if not re.fullmatch(r"UC[A-Za-z0-9_-]{22}", channel_id):
            raise ValueError("YouTube channel ID must be a verified UC... ID")
        yield {
            "id": "youtube-" + channel_id, "category": ch.get("category", "youtube"),
            "label": "YouTube direct channel: " + clean(ch.get("label", channel_id)),
            "url": "https://www.youtube.com/feeds/videos.xml?channel_id=" + quote(channel_id)
        }


def read_json(path, fallback):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else fallback


def relevance(item):
    """Deterministic triage, not AI quality or credibility evaluation."""
    value = (item["title"] + " " + item["excerpt"]).lower()
    patterns = [
        r"\brelease\b|\bupdate\b|\bchangelog\b|\bbreaking\b|\bdeprecated\b",
        r"roblox studio|claude code|mcp|luau|creator hub|playtest",
        r"open.source|github|free plugin|tutorial|workflow",
        r"tycoon|progression|core loop|replay|retention|saving",
    ]
    return sum(bool(re.search(pat, value)) for pat in patterns)


def render(records, new_ids, limit=45, baseline=False):
    selected = [r for r in records if baseline or r["id"] in new_ids]
    selected.sort(key=lambda x: (-relevance(x), x["published"] or "", x["title"]))
    # Highest relevance first; stable on ties. Don't emit a wall of hundreds of posts.
    selected = selected[:limit]
    title = "# Roblox research — " + ("first baseline" if baseline else "new public leads")
    lines = [title, "",
        "Automatic feed metadata, not firsthand gameplay or verified advice. No AI model was called.",
        "",
        "Coverage: GitHub releases/source in the existing scout, RSS/Atom here, public YouTube channels if configured.",
        "X/Instagram are **indexed leads only**, not direct full feeds. Full YouTube transcripts/videos were not analyzed.",
        ""]
    if not selected:
        lines.append("No new findings.")
    for category in sorted({r["category"] for r in selected}):
        lines.extend(["## " + markdown(category, 75).replace("_", " ").title(), ""])
        for r in selected:
            if r["category"] != category:
                continue
            lines.append("- **[" + markdown(r["title"], 160) + "](" + r["url"] + ")** · "
                         + markdown(r["label"], 85) + (" · " + r["published"] if r["published"] else ""))
            if r["excerpt"]:
                lines.append("  - Feed excerpt: " + markdown(r["excerpt"], 240))
        lines.append("")
    lines.extend([
        "---", "",
        "Next step for a promising lead: check the original source, license, actual gameplay or video and real task-fit.",
        "Never treat feed excerpts, indexed social mentions or popularity as proof of quality."
    ])
    return "\n".join(lines) + "\n"


def retry_after(error, now):
    """Back off explicit rate limits and timeouts; never bypass access control."""
    lower = str(error).lower()
    if "429" in lower:
        return (now + timedelta(hours=12)).isoformat()
    if "timed out" in lower:
        return (now + timedelta(hours=6)).isoformat()
    return None


def not_yet_due(entry, now):
    try:
        when = datetime.fromisoformat(entry.get("until", ""))
        return when.tzinfo is not None and when > now
    except (ValueError, TypeError, AttributeError):
        return False


def run():
    cfg = read_json(CONFIG, {})
    old = read_json(STATE, {"seen": [], "items": []})
    baseline = not STATE.exists()
    limit = int(cfg.get("limits", {}).get("per_source", 20))
    timeout = int(cfg.get("limits", {}).get("timeout_seconds", 12))
    successes, failures, incoming = [], {}, []
    original_sources = list(feed_sources(cfg))
    previous_cooldowns = read_json(COOLDOWNS, {})
    active_cooldowns = dict(previous_cooldowns)
    now = datetime.now(timezone.utc)
    deferred = []
    sources = []
    for source in original_sources:
        entry = active_cooldowns.get(source["id"], {})
        if not_yet_due(entry, now):
            deferred.append((source["id"], entry.get("reason", "Temporary backoff")))
        else:
            sources.append(source)
            active_cooldowns.pop(source["id"], None)
    # Bounded concurrent I/O cuts hosted CI minutes without changing source order.
    # Only up to four public RSS reads at once; results are handled deterministically.
    def read_one(source):
        data = fetch_url(source["url"], timeout)
        if source.get("format") == "apple_json":
            return parse_apple_chart(data, source, limit=limit)
        return parse_feed(data, source, limit=limit)

    with ThreadPoolExecutor(max_workers=4) as pool:
        future_list = [pool.submit(read_one, source) for source in sources]
        for source, future in zip(sources, future_list):
            try:
                items = future.result()
                successes.append(source["id"] + ": " + str(len(items)))
                incoming.extend(items)
                active_cooldowns.pop(source["id"], None)
            except (ValueError, ET.ParseError, RuntimeError, OSError) as exc:
                # One blocked feed must NOT erase the good sources.
                failures[source["id"]] = clean(str(exc), 100)
                until = retry_after(exc, now)
                if until:
                    active_cooldowns[source["id"]] = {"until": until, "reason": failures[source["id"]]}

    if not successes:
        raise RuntimeError("All active public feeds failed; saved research is unchanged")

    if active_cooldowns != previous_cooldowns:
        COOLDOWNS.write_text(json.dumps(active_cooldowns, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    # Keep old IDs for already-collected URLs during the title-ID to URL-ID
    # migration. The first production run will NOT rediscover every old link.
    old_url_ids = {r.get("url"): r.get("id") for r in old.get("items", [])
                   if r.get("url") and r.get("id")}
    for item in incoming:
        if item["url"] in old_url_ids:
            item["id"] = old_url_ids[item["url"]]
    # One source URL = one saved item, including after legacy-ID migrations.
    # Without this, old title IDs and new URL IDs can duplicate the same post.
    all_items = {r["url"]: r for r in old.get("items", []) if r.get("url")}
    for r in incoming:
        all_items[r["url"]] = r
    seen = set(old.get("seen", []))
    new_ids = {r["id"] for r in incoming} - seen
    ordered = sorted(all_items.values(), key=lambda r: (r["published"], r["id"]), reverse=True)[:MAX_STORED]
    new_seen = list(dict.fromkeys(old.get("seen", []) + [r["id"] for r in incoming]))[-4000:]
    new_state = {
        "seen": new_seen,
        "items": ordered
    }
    STATE.parent.mkdir(parents=True, exist_ok=True)
    if new_state != old:
        STATE.write_text(json.dumps(new_state, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    current_health = [
        "# Public research feed coverage", "",
        "Feeds read successfully: " + str(len(successes)),
        "Feeds unavailable: " + str(len(failures)),
        "Feeds deferred (temporary cooldown): " + str(len(deferred)), "",
        "Availability is not guaranteed for public Reddit, third-party indexed searches or YouTube feeds.", "",
        "## Successful source reads (item counts)", ""
    ]
    current_health += ["- " + markdown(line, 130) for line in successes]
    current_health.append("")
    if deferred:
        current_health += ["## Deferred feeds — retry after temporary cooldown", ""]
        current_health += ["- " + markdown(k,75) + ": " + markdown(v,120) for k,v in sorted(deferred)]
        current_health.append("")
    if failures:
        current_health += ["## Failures (not silently skipped)", ""]
        current_health += ["- " + markdown(k, 75) + ": " + markdown(v, 120) for k, v in sorted(failures.items())]
    else:
        current_health.append("No new source failures on the most recent scan." + (" Deferred feeds remain." if deferred else ""))
    status = "\n".join(current_health) + "\n"
    if not HEALTH.exists() or HEALTH.read_text(encoding="utf-8") != status:
        HEALTH.write_text(status, encoding="utf-8")

    if baseline or new_ids:
        report = render(incoming, new_ids, limit=int(cfg.get("limits", {}).get("max_new_report", 45)), baseline=baseline)
        if not BRIEF.exists() or BRIEF.read_text(encoding="utf-8") != report:
            BRIEF.write_text(report, encoding="utf-8")
        print(("Initial baseline: " if baseline else "New public leads: ") + str(len(new_ids))
              + "; sources succeeded " + str(len(successes)) + ", failed " + str(len(failures)))
    else:
        print("No new feed entries; report unchanged. Feed failures: " + str(len(failures)))


if __name__ == "__main__":
    try:
        run()
    except (ValueError, ET.ParseError, RuntimeError, OSError, KeyError, TypeError) as exc:
        print("Public-feed scout failed: " + str(exc), file=sys.stderr)
        sys.exit(1)
