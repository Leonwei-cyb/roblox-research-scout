"""Offline tests for Mac Peekaboo staging; no app, network, UI or model calls."""
import base64
import contextlib
import hashlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import stage_peekaboo_mac as s


class PeekabooMacStageTests(unittest.TestCase):
    def test_no_flag_never_runs_or_modifies_mac(self):
        output = io.StringIO()
        with patch.object(s, "stage") as stage, contextlib.redirect_stdout(output):
            self.assertEqual(s.main([]), 0)
        stage.assert_not_called()
        self.assertEqual(json.loads(output.getvalue())["status"], "NOT_RUN")

    def test_pinned_blob_integrity(self):
        raw = b"print('read-only test')\n"
        blob = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
        response = {"encoding": "base64", "sha": blob, "content": base64.b64encode(raw).decode()}
        self.assertEqual(s.decode_git_blob(response, blob), raw)
        with self.assertRaisesRegex(ValueError, "identity"):
            s.decode_git_blob(response, "0" * 40)
        altered = dict(response, content=base64.b64encode(raw + b"x").decode())
        with self.assertRaisesRegex(ValueError, "Decoded source"):
            s.decode_git_blob(altered, blob)

    def test_invalid_source_refuses_before_shell(self):
        with patch.object(s.subprocess, "run") as run:
            with self.assertRaisesRegex(ValueError, "allowlisted"):
                s.download_pin("another-repo/secrets.env", "0" * 40)
        run.assert_not_called()

    def test_gh_errors_do_not_print_tokens(self):
        fake = type("P", (), {"returncode": 1, "stdout": "", "stderr": "token abc-secret"})()
        with patch.object(s.subprocess, "run", return_value=fake):
            with self.assertRaises(ValueError) as result:
                s.download_pin("leon-mac-vision/peekaboo_probe.py", "0" * 40)
        self.assertNotIn("abc-secret", str(result.exception))

    def test_stages_only_reviewed_files_after_offline_tests(self):
        with tempfile.TemporaryDirectory() as dirname:
            root = Path(dirname).resolve()
            subprocess.run(["git", "init", "-q", str(root)], check=True)
            (root / ".gitignore").write_text("local-peekaboo/\n", encoding="utf-8")
            cli = root / ".local" / "bin" / "peekaboo"
            cli.parent.mkdir(parents=True)
            cli.write_bytes(b"test")
            cli.chmod(0o700)
            contents = {
                "peekaboo_probe.py": b"def read_only(): return True\n",
                "tests/test_peekaboo_probe.py": (
                    b"import unittest\n"
                    b"class ProbeCheck(unittest.TestCase):\n"
                    b"    def test_works(self):\n"
                    b"        self.assertTrue(True)\n"),
            }
            def fake_download(src, sha):
                return contents[s.ALLOWED[src][0]]
            with patch.object(s, "ROOT", root), patch.object(s, "DEST", root / "local-peekaboo"), \
                 patch.object(s.Path, "home", return_value=root), \
                 patch.object(s.platform, "system", return_value="Darwin"), \
                 patch.object(s.platform, "mac_ver", return_value=("26.5.2", ("", "", ""), "")), \
                 patch.object(s, "download_pin", side_effect=fake_download):
                result = s.stage()
            self.assertEqual(result["status"], "CODE_STAGED_ONLY")
            self.assertEqual(result["offline_adapter_tests"], "PASS")
            self.assertFalse(result["mac_capture_verified"])
            self.assertEqual((root / "local-peekaboo" / "peekaboo_probe.py").read_bytes(),
                             contents["peekaboo_probe.py"])
            self.assertEqual((root / "local-peekaboo" / "peekaboo_probe.py").stat().st_mode & 0o777, 0o600)
            self.assertFalse((root / "local-peekaboo" / "launchd.plist").exists())

    def test_existing_unreviewed_adapter_not_overwritten(self):
        with tempfile.TemporaryDirectory() as dirname:
            root = Path(dirname).resolve()
            subprocess.run(["git", "init", "-q", str(root)], check=True)
            (root / ".gitignore").write_text("local-peekaboo/\n")
            cli = root / ".local" / "bin" / "peekaboo"
            cli.parent.mkdir(parents=True)
            cli.write_bytes(b"fixture")
            cli.chmod(0o700)
            dest = root / "local-peekaboo"
            dest.mkdir()
            (dest / "peekaboo_probe.py").write_text("prior private content")
            with patch.object(s, "ROOT", root), patch.object(s, "DEST", dest), \
                 patch.object(s.Path, "home", return_value=root), \
                 patch.object(s.platform, "system", return_value="Darwin"), \
                 patch.object(s.platform, "mac_ver", return_value=("26.5.2", ("", "", ""), "")), \
                 patch.object(s, "download_pin", return_value=b"# new source\n"):
                with self.assertRaisesRegex(ValueError, "will not overwrite"):
                    s.stage()
            self.assertEqual((dest / "peekaboo_probe.py").read_text(), "prior private content")


class SafePlacementTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.dest = self.root / "local-peekaboo"
        self.files = {"peekaboo_probe.py": b"exact source\n",
                      "tests/test_peekaboo_probe.py": b"exact test\n"}
        self.patch = patch.object(s, "ROOT", self.root)
        self.patch.start()
        self.addCleanup(self.patch.stop)

    def place(self):
        s.place_files(self.files)

    def test_existing_matching_source_and_permissions(self):
        self.place()
        source = self.dest / "peekaboo_probe.py"
        inode = source.stat().st_ino
        source.chmod(0o644)
        (self.dest / "tests").chmod(0o755)
        self.place()
        self.assertEqual(source.stat().st_ino, inode)
        for relative, data in self.files.items():
            target = self.dest / relative
            self.assertEqual(target.read_bytes(), data)
            self.assertEqual(target.stat().st_mode & 0o7777, 0o600)
            self.assertEqual(target.parent.stat().st_mode & 0o7777, 0o700)

    def test_parent_leaf_and_dangling_symlinks(self):
        for relative in (".", "tests", "peekaboo_probe.py",
                         "tests/test_peekaboo_probe.py"):
            for dangling in (False, True):
                with self.subTest(relative=relative, dangling=dangling):
                    with tempfile.TemporaryDirectory(dir=self.root) as tmp:
                        root = Path(tmp)
                        dest = root / "local-peekaboo"
                        outside = root / "outside"
                        if not dangling:
                            outside.mkdir()
                        target = dest if relative == "." else dest / relative
                        target.parent.mkdir(parents=True, exist_ok=True)
                        target.symlink_to(outside)
                        with patch.object(s, "ROOT", root):
                            with self.assertRaises((OSError, ValueError)):
                                self.place()
                        self.assertTrue(target.is_symlink())
                        if not dangling:
                            self.assertEqual(list(outside.iterdir()), [])

    def test_symlink_in_root_parent_is_refused(self):
        alias = self.root / "alias"
        alias.symlink_to(self.root, target_is_directory=True)
        with patch.object(s, "ROOT", alias):
            with self.assertRaises(OSError):
                self.place()
        self.assertFalse(self.dest.exists())

    def test_differing_bytes_are_preserved_and_new_files_rolled_back(self):
        (self.dest / "tests").mkdir(parents=True)
        existing = self.dest / "tests/test_peekaboo_probe.py"
        existing.write_bytes(b"different")
        with self.assertRaisesRegex(ValueError, "will not overwrite"):
            self.place()
        self.assertEqual(existing.read_bytes(), b"different")
        self.assertFalse((self.dest / "peekaboo_probe.py").exists())
        self.assertFalse((self.dest / ".stage-lock").exists())

    def test_incomplete_and_failed_writes_roll_back(self):
        write = os.write
        for failure in (0, OSError("disk full")):
            with self.subTest(failure=failure):
                calls = []
                def broken(fd, data):
                    calls.append(data)
                    if len(calls) == 1:
                        return write(fd, data[:2])
                    if isinstance(failure, Exception):
                        raise failure
                    return failure
                with patch.object(s.os, "write", side_effect=broken):
                    with self.assertRaises((OSError, ValueError)):
                        self.place()
                self.assertFalse((self.dest / "peekaboo_probe.py").exists())
                self.assertFalse((self.dest / ".stage-lock").exists())

    def test_short_writes_are_completed(self):
        write = os.write
        with patch.object(s.os, "write", side_effect=lambda fd, data: write(fd, data[:2])):
            self.place()
        self.assertEqual((self.dest / "peekaboo_probe.py").read_bytes(),
                         self.files["peekaboo_probe.py"])

    def test_concurrent_staging_is_refused(self):
        write = os.write
        attempted = []
        def concurrent(fd, data):
            if not attempted:
                attempted.append(True)
                with self.assertRaises(FileExistsError):
                    self.place()
            return write(fd, data)
        with patch.object(s.os, "write", side_effect=concurrent):
            self.place()
        self.assertTrue(attempted)

    def test_leaf_creation_race_does_not_clobber(self):
        original = os.open
        def racing(path, flags, *args, **kwargs):
            if path == "peekaboo_probe.py" and flags & os.O_EXCL:
                (self.dest / path).write_bytes(b"racer")
            return original(path, flags, *args, **kwargs)
        with patch.object(s.os, "open", side_effect=racing):
            with self.assertRaisesRegex(ValueError, "will not overwrite"):
                self.place()
        self.assertEqual((self.dest / "peekaboo_probe.py").read_bytes(), b"racer")

    def test_directory_replacement_is_detected(self):
        write = os.write
        replaced = []
        outside = self.root / "outside"
        outside.mkdir()
        def racing(fd, data):
            if not replaced:
                replaced.append(True)
                self.dest.rename(self.root / "displaced")
                self.dest.symlink_to(outside, target_is_directory=True)
            return write(fd, data)
        with patch.object(s.os, "write", side_effect=racing):
            with self.assertRaisesRegex(ValueError, "replaced"):
                self.place()
        self.assertEqual(list(outside.iterdir()), [])
        self.assertFalse((self.root / "displaced/peekaboo_probe.py").exists())

    def test_leaf_replacement_symlink_is_detected_without_touching_target(self):
        fsync = os.fsync
        outside = self.root / "outside"
        outside.write_bytes(b"untouched")
        replaced = []
        def racing(fd):
            fsync(fd)
            if not replaced:
                replaced.append(True)
                target = self.dest / "peekaboo_probe.py"
                target.unlink()
                target.symlink_to(outside)
        with patch.object(s.os, "fsync", side_effect=racing):
            with self.assertRaisesRegex(ValueError, "Unsafe adapter file|replaced"):
                self.place()
        self.assertEqual(outside.read_bytes(), b"untouched")
        self.assertTrue((self.dest / "peekaboo_probe.py").is_symlink())
        self.assertFalse((self.dest / "tests/test_peekaboo_probe.py").exists())

    def test_final_bytes_are_rechecked(self):
        fsync = os.fsync
        calls = []
        def corrupt(fd):
            fsync(fd)
            calls.append(fd)
            if len(calls) == 2:
                (self.dest / "peekaboo_probe.py").write_bytes(b"corruption")
        with patch.object(s.os, "fsync", side_effect=corrupt):
            with self.assertRaisesRegex(ValueError, "will not overwrite"):
                self.place()
        self.assertFalse((self.dest / "peekaboo_probe.py").exists())

    def test_actual_gitignore_and_tracked_files(self):
        subprocess.run(["git", "init", "-q", str(self.root)], check=True)
        ignore = self.root / ".gitignore"
        for pattern in ("# local-peekaboo/\n", "local-peekaboo/\n!local-peekaboo/\n"):
            ignore.write_text(pattern)
            with self.assertRaisesRegex(ValueError, "not gitignored"):
                s.validate_gitignore()
        ignore.write_text("local-peekaboo/\n")
        s.validate_gitignore()
        self.place()
        subprocess.run(["git", "-C", str(self.root), "add", "-f",
                        "local-peekaboo/peekaboo_probe.py"], check=True)
        with self.assertRaisesRegex(ValueError, "Tracked"):
            s.validate_gitignore()


if __name__ == "__main__":
    unittest.main()
