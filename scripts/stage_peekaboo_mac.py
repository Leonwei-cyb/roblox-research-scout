#!/usr/bin/env python3
"""Explicit one-shot Mac staging of reviewed Peekaboo adapter, NO launchd changes.

This script is inert unless invoked with --stage; it runs no browser, game,
screenshot or automation operation. Never add local-peekaboo/ to Git.
"""
from __future__ import annotations
import argparse
import base64
import hashlib
import json
import os
import platform
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "local-peekaboo"
HUB = "Leonwei-cyb/Roblox-Studio-Hub"
# Exact Hub draft PR #87 revision; change these ONLY after source review.
HEAD = "8c730ec9239ba440021ab26bd7b819eefd11bb09"
ALLOWED = {
    "leon-mac-vision/peekaboo_probe.py": ("peekaboo_probe.py", "38656adfe7c6c52205020eaf35276bd979c3c13f"),
    "leon-mac-vision/tests/test_peekaboo_probe.py": ("tests/test_peekaboo_probe.py", "ea990c4bec7ee1662f8cf52eb4ca66663b41f5ac"),
}


def decode_git_blob(response: dict, expected_sha: str) -> bytes:
    if response.get("encoding") != "base64" or response.get("sha") != expected_sha:
        raise ValueError("Pinned GitHub blob identity did not match")
    raw = base64.b64decode(response["content"], validate=False)
    actual = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
    if actual != expected_sha:
        raise ValueError("Decoded source did not match pinned Git blob")
    compile(raw, "<pinned-readonly-source>", "exec")
    return raw


def download_pin(path: str, sha: str) -> bytes:
    # The Mac's existing gh authentication is used locally. No secrets printed.
    if path not in ALLOWED:
        raise ValueError("Path not allowlisted")
    url = f"repos/{HUB}/contents/{path}?ref={HEAD}"
    try:
        cmd = subprocess.run(["gh", "api", "--method", "GET", url],
                             capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired) as ex:
        raise ValueError("Mac gh could not access reviewed Hub source") from ex
    if cmd.returncode or len(cmd.stdout) > 200_000:
        raise ValueError("Mac gh cannot read the pinned private adapter")
    try:
        return decode_git_blob(json.loads(cmd.stdout), sha)
    except (ValueError, KeyError, TypeError) as ex:
        raise ValueError("Private adapter integrity check failed") from ex


def stage():
    if platform.system() != "Darwin" or int((platform.mac_ver()[0] or "0").split(".")[0]) < 15:
        raise ValueError("Stage only on the owner's existing macOS 15+ host")
    existing = Path.home() / ".local" / "bin" / "peekaboo"
    if not existing.is_file() or not os.access(existing, os.X_OK):
        raise ValueError("Existing Intel Peekaboo CLI not found; no downloads or installation attempted")
    if "local-peekaboo/" not in (ROOT / ".gitignore").read_text(encoding="utf-8"):
        raise ValueError("Private adapter directory is not gitignored; refusing write")
    files = {relative: download_pin(source, sha)
             for source, (relative, sha) in ALLOWED.items()}
    for relative, data in files.items():
        target = DEST / relative
        if target.exists() and target.read_bytes() != data:
            raise ValueError("Existing local adapter differs; will not overwrite or interrupt it")
    # Test in an isolated temp directory, BEFORE placing any files in the Scout clone.
    with tempfile.TemporaryDirectory(prefix="leon-peekaboo-smoke-") as tmp:
        for relative, data in files.items():
            target = Path(tmp) / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        proc = subprocess.run([sys.executable, "-m", "unittest", "discover",
                               "-s", str(Path(tmp) / "tests"), "-v"],
                              capture_output=True, text=True, timeout=60, cwd=tmp)
        if proc.returncode:
            raise ValueError("Pinned adapter offline tests failed; not staged")
    DEST.mkdir(mode=0o700, parents=True, exist_ok=True)
    DEST.chmod(0o700)
    for relative, data in files.items():
        target = DEST / relative
        target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        if not target.exists():
            # Byte-identical and py_compile-tested; no executable bit required.
            target.write_bytes(data)
            target.chmod(0o600)
    return {"status": "CODE_STAGED_ONLY", "hub_head": HEAD, "offline_adapter_tests": "PASS",
            "peekaboo_cli_installed": True, "mac_capture_verified": False,
            "research_scout_schedule_unchanged": True, "social_media_access_unlocked": False}


def main(argv=None):
    p = argparse.ArgumentParser(description="One-shot, operator-invoked Peekaboo Mac staging")
    p.add_argument("--stage", action="store_true", help="Explicit local staging only; no capture or scheduler change")
    args = p.parse_args(argv)
    if not args.stage:
        print(json.dumps({"status": "NOT_RUN", "reason": "Pass --stage on existing Mac after reviewing PRs #22/#87"}))
        return 0
    try:
        print(json.dumps(stage()))
    except (OSError, ValueError, subprocess.TimeoutExpired) as error:
        print(json.dumps({"status": "BLOCKED", "reason": str(error) if isinstance(error, ValueError) else "Local staging failure"}))
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
