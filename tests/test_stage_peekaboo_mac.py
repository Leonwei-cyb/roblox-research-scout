"""Offline tests for Mac Peekaboo staging; no app, network, UI or model calls."""
import base64
import contextlib
import hashlib
import io
import json
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
            root = Path(dirname)
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
            root = Path(dirname)
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
                 patch.object(s, "download_pin", return_value=b"new source"):
                with self.assertRaisesRegex(ValueError, "will not overwrite"):
                    s.stage()
            self.assertEqual((dest / "peekaboo_probe.py").read_text(), "prior private content")


if __name__ == "__main__":
    unittest.main()
