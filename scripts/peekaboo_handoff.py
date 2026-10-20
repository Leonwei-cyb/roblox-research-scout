#!/usr/bin/env python3
"""Explicit, local-only handoff from Scout's public media queue to Leon Peekaboo.

No scheduler, account login, browser navigation, screenshots or Peekaboo calls
occur unless an operator supplies an exact existing window and opts in.
Never upload desktop screenshots to the public research repository.
"""
import argparse
import json
import re
import os
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "watch" / "learning_index.json"
VISUAL = ROOT / "local-peekaboo" / "peekaboo_probe.py"
SOCIAL = {"x", "instagram", "tiktok", "youtube"}


def candidate(key, index):
    records = index.get("posts", [])
    matches = [p for p in records if isinstance(p, dict) and p.get("key") == key]
    if len(matches) != 1:
        raise ValueError("Specify one exact saved original-post key from learning_index.json")
    p = matches[0]
    url = urlsplit(str(p.get("url", "")))
    kind = p.get("kind")
    hosts = {
        "x": {"x.com", "www.x.com", "twitter.com", "www.twitter.com"},
        "instagram": {"instagram.com", "www.instagram.com"},
        "tiktok": {"tiktok.com", "www.tiktok.com"},
        "youtube": {"youtube.com", "www.youtube.com", "youtu.be"},
    }
    if (url.scheme != "https" or not url.hostname or url.username or url.password or
            kind not in SOCIAL or url.hostname.lower() not in hosts[kind]):
        raise ValueError("Only original, allowlisted public social/video URLs are supported")
    original = str(p.get("url", ""))
    expected_patterns = {
        "x": r"^/[^/]+/status/\d+/?$",
        "instagram": r"^/(?:p|reel)/[A-Za-z0-9_-]+/?$",
        "tiktok": r"^/@[^/]+/video/\d+/?$",
        "youtube": r"^(?:/watch|/shorts/[A-Za-z0-9_-]+|/[A-Za-z0-9_-]{11})/?$",
    }
    if not re.fullmatch(expected_patterns[kind], url.path):
        raise ValueError("Candidate is not an individual original social/video post")
    if kind == "youtube" and url.path == "/watch" and not re.search(r"(?:^|&)v=[A-Za-z0-9_-]{11}(?:&|$)", url.query):
        raise ValueError("YouTube link lacks a verified video ID")
    if p.get("evidence") != "UNVIEWED_METADATA":
        raise ValueError("Unexpected source evidence marker")
    return p


def prepare(key, index):
    p = candidate(key, index)
    return {"status": "AWAITING_ORIGINAL_REVIEW", "key": p["key"], "url": p["url"],
            "creator_verified": False, "original_post_opened": False,
            "video_watched": False, "audio_heard": False, "screenshot_uploaded": False,
            "next": "Open original post manually in an isolated public-only browser window; inspect author, date and rights"}


def capture(key, app, window_id, index, probe=VISUAL, *, keep_private=False, public_window_confirmed=False):
    require = candidate(key, index)
    if not probe.is_file():
        raise ValueError("Local Peekaboo adapter missing. Stage reviewed Leon Hub PR #87 into local-peekaboo/, do not install or merge automatically")
    if app not in ("Google Chrome", "Safari", "Firefox", "Brave Browser"):
        raise ValueError("Only a dedicated public-only browser window is eligible")
    if type(window_id) is not int or window_id <= 0:
        raise ValueError("An exact positive window ID is required")
    if keep_private and not public_window_confirmed:
        raise ValueError("Retaining a screenshot requires confirming a dedicated public-only browser window")
    command = [sys.executable, str(probe), "capture", "--app", app,
               "--window-id", str(window_id), "--allow-browser"]
    if keep_private:
        command += ["--keep-private"]
    # Even a successful capture is NOT an assertion that it shows the right post.
    proc = subprocess.run(command, capture_output=True, text=True, timeout=75)
    if proc.returncode:
        raise ValueError("Peekaboo refused or failed the isolated window capture")
    try:
        receipt = json.loads(proc.stdout)
    except ValueError as error:
        raise ValueError("Peekaboo receipt malformed") from error
    if receipt.get("status") != "OBSERVED_READ_ONLY" or receipt.get("local_only") is not True:
        raise ValueError("Capture lacked a verified read-only local receipt")
    result = {"status": "CAPTURE_ONLY_UNVERIFIED_CONTENT", "key": require["key"],
              "screen_capture_completed": True, "original_post_opened": False,
              "video_watched": False, "audio_heard": False, "social_feed_access_unlocked": False,
              "private_image_retained": False,
              "next": "Inspect the original post and any retained local screenshot before recording gameplay evidence."}
    if keep_private:
        private_path = Path(str(receipt.get("local_path", "")))
        expected = Path.home() / "Library" / "Application Support" / "Leon" / "peekaboo-private"
        if private_path.parent != expected or not private_path.name.endswith(".png") or not private_path.is_file():
            raise ValueError("Retained screenshot missing or outside private Leon directory")
        result["private_image_retained"] = True
        result["private_image_name"] = private_path.name
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description="Local-only Peekaboo-assisted social source handoff")
    parser.add_argument("key", help="Exact original-post key from watch/learning_index.json")
    parser.add_argument("--capture", action="store_true", help="One read-only exact-window attempt only")
    parser.add_argument("--app", choices=("Google Chrome", "Safari", "Firefox", "Brave Browser"))
    parser.add_argument("--window-id", type=int)
    parser.add_argument("--keep-private", action="store_true", help="retain one private local screenshot for actual review")
    parser.add_argument("--confirm-public-only-window", action="store_true", help="operator attests browser window contains only public, permitted content")
    args = parser.parse_args(argv)
    try:
        index = json.loads(INDEX.read_text(encoding="utf-8"))
        if args.capture:
            if not args.app or args.window_id is None:
                raise ValueError("Capture requires --app and --window-id, dedicated public-only browser")
            result = capture(args.key, args.app, args.window_id, index,
                             keep_private=args.keep_private,
                             public_window_confirmed=args.confirm_public_only_window)
        else:
            result = prepare(args.key, index)
    except (OSError, ValueError, subprocess.TimeoutExpired) as error:
        # Don't emit subprocess stdout/stderr; it could contain window titles.
        result = {"status": "BLOCKED", "reason": str(error) if isinstance(error, ValueError) else "Local handoff failed"}
        print(json.dumps(result))
        return 2
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
