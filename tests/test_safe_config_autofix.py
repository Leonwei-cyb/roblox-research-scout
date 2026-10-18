import importlib.util,tempfile,json,unittest
from pathlib import Path
p=Path(__file__).resolve().parents[1]/"scripts/safe_config_autofix.py"
spec=importlib.util.spec_from_file_location("safe_config_autofix",p)
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
class SafeRepairTests(unittest.TestCase):
    def test_exact_duplicates_only(self):
        value={"feeds":[{"id":"x","url":"https://example.org/rss"},{"id":"x","url":"https://example.org/rss"}]}
        fixed,report=m.repair(value,{"feeds":"id"})
        self.assertEqual(report,{"feeds":1})
        self.assertEqual(len(fixed["feeds"]),1)
    def test_conflicting_same_id_cannot_be_auto_repaired(self):
        value={"feeds":[{"id":"x","url":"https://a"},{"id":"x","url":"https://b"}]}
        with self.assertRaises(ValueError):
            m.repair(value,{"feeds":"id"})
    def test_dry_run_and_source_scope(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/"watch").mkdir()
            a=root/"watch/config.json";b=root/"watch/feeds.json"
            a.write_text(json.dumps({"watch_repos":["Roblox/luau","Roblox/luau"]}))
            b.write_text(json.dumps({"feeds":[{"id":"a","url":"https://x"}]}))
            m.work(root,False)
            self.assertEqual(json.loads(a.read_text())["watch_repos"],["Roblox/luau","Roblox/luau"])
            m.work(root,True)
            self.assertEqual(json.loads(a.read_text())["watch_repos"],["Roblox/luau"])
            self.assertFalse((root/"src").exists())
if __name__=="__main__":
    unittest.main()
