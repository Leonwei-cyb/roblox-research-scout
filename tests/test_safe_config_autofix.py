import importlib.util,tempfile,json,unittest
from unittest.mock import patch
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
    def test_json_type_conflict_changes_neither_file(self):
        # Python equality conflates True/1 and False/0 even inside nested lists.
        for first, second in [(True, 1), (False, 0), (1, 1.0)]:
            with self.subTest(first=first, second=second), tempfile.TemporaryDirectory() as d:
                root=Path(d);(root/"watch").mkdir()
                a=root/"watch/config.json";b=root/"watch/feeds.json"
                a.write_text(json.dumps({"watch_repos":["Roblox/luau","Roblox/luau"]}))
                b.write_text(json.dumps({"feeds":[
                    {"id":"x","url":"https://example.org/rss","options":{"values":[first]}},
                    {"id":"x","url":"https://example.org/rss","options":{"values":[second]}}
                ]}))
                before=(a.read_bytes(),b.read_bytes())
                with self.assertRaisesRegex(ValueError, "Conflicting entries"):
                    m.work(root,True)
                self.assertEqual((a.read_bytes(),b.read_bytes()),before)

    def test_identical_objects_with_reordered_keys_are_deduplicated(self):
        value={"feeds":[{"id":"x","url":"https://example.org/rss"},
                        {"url":"https://example.org/rss","id":"x"}]}
        fixed,report=m.repair(value,{"feeds":"id"})
        self.assertEqual(report,{"feeds":1})
        self.assertEqual(fixed["feeds"],[value["feeds"][0]])

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
    def test_conflict_in_second_file_changes_neither_file(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/"watch").mkdir()
            a=root/"watch/config.json";b=root/"watch/feeds.json"
            a.write_text(json.dumps({"watch_repos":["Roblox/luau","Roblox/luau"]}))
            b.write_text(json.dumps({"feeds":[{"id":"x","url":"https://a"},{"id":"x","url":"https://b"}]}))
            before=(a.read_bytes(),b.read_bytes())
            with self.assertRaises(ValueError):
                m.work(root,True)
            self.assertEqual((a.read_bytes(),b.read_bytes()),before)

    def test_two_file_repair_and_idempotent_recheck(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/"watch").mkdir()
            a=root/"watch/config.json";b=root/"watch/feeds.json"
            a.write_text(json.dumps({"watch_repos":["Roblox/luau","Roblox/luau"]}))
            b.write_text(json.dumps({"feeds":[{"id":"x","url":"https://a"},{"id":"x","url":"https://a"}]}))
            self.assertEqual(m.work(root,True),[("watch/config.json",{"watch_repos":1}),("watch/feeds.json",{"feeds":1})])
            first=(a.read_bytes(),b.read_bytes())
            self.assertEqual(m.work(root,True),[("watch/config.json",{}),("watch/feeds.json",{})])
            self.assertEqual((a.read_bytes(),b.read_bytes()),first)

    def test_second_replace_error_rolls_back_first(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/"watch").mkdir()
            a=root/"watch/config.json";b=root/"watch/feeds.json"
            a.write_text(json.dumps({"watch_repos":["Roblox/luau","Roblox/luau"]}))
            b.write_text(json.dumps({"feeds":[{"id":"x"},{"id":"x"}]}))
            before=(a.read_bytes(),b.read_bytes())
            actual_replace=m.os.replace
            calls=[0]
            def fail_second(src,dst):
                calls[0]+=1
                if calls[0]==2:
                    raise OSError("simulated second-file write failure")
                return actual_replace(src,dst)
            with patch.object(m.os,"replace",side_effect=fail_second):
                with self.assertRaises(OSError):
                    m.work(root,True)
            self.assertEqual((a.read_bytes(),b.read_bytes()),before)
            self.assertEqual(list((root/"watch").glob(".leon-autofix-*")),[])

    def test_symlink_configuration_refused(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/"watch").mkdir()
            (root/"watch/config.json").write_text(json.dumps({"watch_repos":[]}))
            outside=root/"elsewhere.json"
            outside.write_text("{}")
            (root/"watch/feeds.json").symlink_to(outside)
            with self.assertRaises(ValueError):
                m.work(root,True)
            self.assertEqual(outside.read_text(),"{}")

    def test_non_object_config_refused(self):
        with self.assertRaises(ValueError):
            m.repair([],{"watch_repos":"string"})
if __name__=="__main__":
    unittest.main()
