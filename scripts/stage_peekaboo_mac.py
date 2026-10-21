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
import stat
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "local-peekaboo"
HUB = "Leonwei-cyb/Roblox-Studio-Hub"
# Exact Hub draft PR #87 revision; change these ONLY after source review.
HEAD = "ddf2be9b1539851372bb02002e490186149078dc"
ALLOWED = {
    "leon-mac-vision/peekaboo_probe.py": ("peekaboo_probe.py", "a2bd1b3d321b43c1bfcf5ba672453da753d7b730"),
    "leon-mac-vision/tests/test_peekaboo_probe.py": ("tests/test_peekaboo_probe.py", "76c0c6c3e77a1a5b8f5d721f8d4167717b669b8b"),
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


def validate_gitignore():
    paths = ["local-peekaboo/" + relative for relative, _ in ALLOWED.values()]
    tracked = subprocess.run(["git", "ls-files", "--", "local-peekaboo"],
                             cwd=ROOT, capture_output=True, text=True, check=True)
    if tracked.stdout:
        raise ValueError("Tracked adapter files; refusing write")
    for path in paths:
        ignored = subprocess.run(
            ["git", "-c", "core.excludesFile=/dev/null", "check-ignore",
             "--no-index", "-v", "--", path], cwd=ROOT,
            capture_output=True, text=True)
        if (ignored.returncode or not ignored.stdout.startswith(".gitignore:")
                or ignored.stdout.split("\t", 1)[0].split(":", 2)[-1].startswith("!")):
            raise ValueError("Private adapter directory is not gitignored; refusing write")


def place_files(files):
    """Anchor every lookup to held directories; never follow a destination link."""
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    fds, created = [], []
    lock = None
    def directory(parent, name, create=False):
        if create:
            try:
                os.mkdir(name, 0o700, dir_fd=parent)
            except FileExistsError:
                pass
        fd = os.open(name, flags, dir_fd=parent)
        fds.append(fd)
        return fd
    def same(parent, name, fd):
        entry = os.stat(name, dir_fd=parent, follow_symlinks=False)
        held = os.fstat(fd)
        if (entry.st_dev, entry.st_ino) != (held.st_dev, held.st_ino):
            raise ValueError("Staging path replaced concurrently")
    def verify(fd, data):
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
            raise ValueError("Unsafe adapter file")
        os.lseek(fd, 0, os.SEEK_SET)
        chunks = []
        while True:
            chunk = os.read(fd, 65536)
            if not chunk:
                break
            chunks.append(chunk)
        if b"".join(chunks) != data:
            raise ValueError("Existing local adapter differs; will not overwrite or interrupt it")
    try:
        root = os.open("/", flags)
        fds.append(root)
        links = []
        for part in ROOT.absolute().parts[1:]:
            child = directory(root, part)
            links.append((root, part, child))
            root = child
        dest = directory(root, "local-peekaboo", True)
        links.append((root, "local-peekaboo", dest))
        lock = os.open(".stage-lock", os.O_WRONLY | os.O_CREAT | os.O_EXCL |
                       os.O_NOFOLLOW, 0o600, dir_fd=dest)
        records = []
        for relative, data in files.items():
            parts = Path(relative).parts
            parent = dest
            for part in parts[:-1]:
                child = directory(parent, part, True)
                links.append((parent, part, child))
                parent = child
            name = parts[-1]
            try:
                fd = os.open(name, os.O_RDWR | os.O_CREAT | os.O_EXCL |
                             os.O_NOFOLLOW, 0o600, dir_fd=parent)
                fds.append(fd)
                created.append((parent, name, fd))
                written = 0
                while written < len(data):
                    count = os.write(fd, data[written:])
                    if count <= 0:
                        raise ValueError("Incomplete adapter write")
                    written += count
                os.fsync(fd)
            except FileExistsError:
                fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
                             dir_fd=parent)
                fds.append(fd)
            verify(fd, data)
            os.fchmod(fd, 0o600)
            records.append((parent, name, fd, data))
        for parent, name, fd in links:
            same(parent, name, fd)
        # Only staging directories receive private permissions, never ancestors.
        staging_dirs = {dest} | {parent for parent, _, _, _ in records}
        for fd in staging_dirs:
            os.fchmod(fd, 0o700)
            if stat.S_IMODE(os.fstat(fd).st_mode) != 0o700:
                raise ValueError("Unsafe adapter directory permissions")
        for parent, name, fd, data in records:
            same(parent, name, fd)
            verify(fd, data)
            if stat.S_IMODE(os.fstat(fd).st_mode) != 0o600:
                raise ValueError("Unsafe adapter file permissions")
        for parent, name, fd in links:
            same(parent, name, fd)
    except BaseException:
        for parent, name, fd in reversed(created):
            try:
                same(parent, name, fd)
                os.unlink(name, dir_fd=parent)
            except (OSError, ValueError):
                pass
        raise
    finally:
        try:
            if lock is not None:
                try:
                    same(dest, ".stage-lock", lock)
                    os.unlink(".stage-lock", dir_fd=dest)
                finally:
                    os.close(lock)
        finally:
            for fd in reversed(fds):
                os.close(fd)


def stage():
    if platform.system() != "Darwin" or int((platform.mac_ver()[0] or "0").split(".")[0]) < 15:
        raise ValueError("Stage only on the owner's existing macOS 15+ host")
    existing = Path.home() / ".local" / "bin" / "peekaboo"
    if not existing.is_file() or not os.access(existing, os.X_OK):
        raise ValueError("Existing Intel Peekaboo CLI not found; no downloads or installation attempted")
    validate_gitignore()
    files = {relative: download_pin(source, sha)
             for source, (relative, sha) in ALLOWED.items()}
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
    place_files(files)
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
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print(json.dumps({"status": "BLOCKED", "reason": str(error) if isinstance(error, ValueError) else "Local staging failure"}))
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
