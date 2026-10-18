import importlib.util
import unittest
from pathlib import Path

spec=importlib.util.spec_from_file_location("license_watch",
    Path(__file__).resolve().parents[1]/"scripts/license_watch.py")
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

class LicenseTests(unittest.TestCase):
    def test_safe_repo_names(self):
        x={"watch_repos":["Roblox/luau","evil.com/a","dev/studio","Roblox/luau","bad/../url"]}
        self.assertEqual(m.watched_repos(x),["Roblox/luau","dev/studio"])
    def test_covers_all_current_monitored_public_repos(self):
        config={"watch_repos":["owner/repo"+str(i) for i in range(17)]}
        self.assertEqual(len(m.watched_repos(config)),17)

    def test_license_caution(self):
        self.assertIn("do NOT copy",m.license_label({"license":None}))
        self.assertIn("copyleft",m.license_label({"license":{"spdx_id":"GPL-3.0"}}))
        self.assertIn("asset and dependency",m.license_label({"license":{"spdx_id":"MIT"}}))
    def test_source_metadata(self):
        row=("Roblox/luau",{"license":{"spdx_id":"MIT"},"pushed_at":"2026-10-18","archived":False},"")
        s=m.report([row])
        self.assertIn("MIT",s)
        self.assertIn("2026-10-18",s)
        self.assertIn("security audit",s)
if __name__=="__main__":
    unittest.main()
