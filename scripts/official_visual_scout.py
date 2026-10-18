#!/usr/bin/env python3
"""Index direct, original creator-hosted still-image links without downloading assets.

This is NOT video playback, an AI quality review, or permission to reuse artwork.
Run once daily inside the existing public GitHub research workflow.
"""
from __future__ import annotations

import html
import json
import re
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import unquote, urljoin, urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "watch" / "official_visual_pages.json"
STATE = ROOT / "watch" / "official_visual_state.json"
REPORT = ROOT / "watch" / "official_visual_sources.md"
PAGE_HOSTS = {"www.biggames.io"}
IMAGE_HOSTS = {"bigblog-storage.s3.us-east-1.amazonaws.com"}
IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".webp", ".gif")
INTERVAL = timedelta(hours=24)
MAX_HTML = 1_500_000


def permitted_asset(raw_url, page_url):
    url = urljoin(page_url, html.unescape(str(raw_url).strip()))
    parsed = urlparse(url)
    if (parsed.scheme != "https" or parsed.hostname not in IMAGE_HOSTS or
            parsed.username or parsed.password or
            not parsed.path.lower().endswith(IMAGE_EXTS)):
        return ""
    return url


class OriginalImages(HTMLParser):
    def __init__(self, page_url):
        super().__init__(convert_charrefs=True)
        self.page_url = page_url
        self.images = []
        self.seen = set()

    def handle_starttag(self, tag, attrs):
        if tag not in {"img", "a", "source"}:
            return
        a = dict(attrs)
        urls = [a.get(k, "") for k in ("src", "data-src", "data-original", "href")]
        if a.get("srcset"):
            urls.append(a["srcset"].split(",")[0].strip().split(" ")[0])
        for raw in urls:
            if not raw:
                continue
            link = permitted_asset(raw, self.page_url)
            if not link or link in self.seen:
                continue
            self.seen.add(link)
            title = str(a.get("alt") or a.get("title") or "").strip()
            name = unquote(urlparse(link).path.rsplit("/", 1)[-1])
            self.images.append({"url": link, "name": name, "label": title or name})


class OriginalOnlyRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        p = urlparse(newurl)
        if p.scheme != "https" or p.hostname not in PAGE_HOSTS:
            raise ValueError("Redirected outside original creator website")
        return super().redirect_request(request, fp, code, msg, headers, newurl)


def fetch_page(url):
    p = urlparse(url)
    if p.scheme != "https" or p.hostname not in PAGE_HOSTS or p.username:
        raise ValueError("Not an approved original creator page")
    req = Request(url, headers={"User-Agent": "Roblox-Research-Original-Visuals/1.0", "Accept": "text/html"})
    with build_opener(OriginalOnlyRedirect()).open(req, timeout=12) as response:
        if urlparse(response.geturl()).hostname not in PAGE_HOSTS:
            raise ValueError("Invalid final page host")
        data = response.read(MAX_HTML + 1)
    if len(data) > MAX_HTML:
        raise ValueError("Page exceeded content limit")
    return data.decode("utf-8", errors="replace")


def select(images, keywords, limit=12):
    scored = []
    for item in images:
        label = (item["name"] + " " + item["label"]).lower()
        strength = sum(1 for keyword in keywords if str(keyword).lower() in label)
        if strength:
            scored.append((strength, item))
    scored.sort(key=lambda r: (-r[0], r[1]["name"], r[1]["url"]))
    return [item for _, item in scored[:limit]]


def markdown_safe(value):
    return re.sub(r"[\x00-\x1f]+", " ", str(value))[:150].replace("[", "\\[").replace("]", "\\]").replace("|", "\\|")


def render(groups, errors):
    lines = [
        "# Original creator visual source links",
        "",
        "**Actual direct still-image URLs on verified developer websites, NOT video watched or automatically analyzed imagery.**",
        "Asset ownership remains with the original creator; these are reference links, NOT download/reuse licenses.",
        "",
    ]
    for page, pictures in groups:
        lines.extend(["## " + markdown_safe(page["publisher"]), "",
                      "Original developer page: " + page["url"], ""])
        if not pictures:
            lines.append("No task-relevant directly hosted images found.")
        for image in pictures:
            lines.append("- [" + markdown_safe(image["label"]) + "](" + image["url"] + ")"
                         + " — original developer-hosted still, pixels NOT inspected by this bot")
        lines.append("")
    if errors:
        lines.extend(["## Unavailable sources", ""])
        for source, message in errors:
            lines.append("- " + markdown_safe(source) + ": " + markdown_safe(message))
        lines.append("")
    lines.append("For visual critique, a reviewer must OPEN the source image. For video motion or sound, inspect permitted real footage.")
    return "\n".join(lines).rstrip() + "\n"


def run(now=None):
    now = now or datetime.now(timezone.utc)
    old = json.loads(STATE.read_text(encoding="utf-8")) if STATE.exists() else {}
    if old.get("checked_at"):
        try:
            if now - datetime.fromisoformat(old["checked_at"]) < INTERVAL:
                print("Original creator image index is fresh (<24h), skipping.")
                return
        except ValueError:
            pass
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    groups, errors = [], []
    for source in config["pages"]:
        try:
            page = fetch_page(source["url"])
            parser = OriginalImages(source["url"])
            parser.feed(page)
            groups.append((source, select(parser.images, source["keywords"])))
        except (HTTPError, URLError, TimeoutError, ValueError, OSError) as exc:
            errors.append((source["id"], type(exc).__name__))
    if not groups:
        # Do not overwrite previously useful evidence on a network outage.
        print("All original visual sources unavailable; preserving existing report.")
    else:
        result = render(groups, errors)
        if not REPORT.exists() or REPORT.read_text(encoding="utf-8") != result:
            REPORT.write_text(result, encoding="utf-8")
            print("Updated original developer still-image reference links.")
    STATE.write_text(json.dumps({"checked_at": now.isoformat(), "failed_sources": len(errors),
                                "successful_sources": len(groups)}, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    run()
