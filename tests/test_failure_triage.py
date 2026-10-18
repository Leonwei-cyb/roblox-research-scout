import importlib.util
import unittest
from pathlib import Path
p=Path(__file__).resolve().parents[1]/"scripts/failure_triage.py"
spec=importlib.util.spec_from_file_location("failure_triage",p)
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
class FailureTests(unittest.TestCase):
    def test_extract_only_failures(self):
        text="# Coverage\n\n## Successful source reads\n- foo: 5\n\n## Failures\n- reddit-one: HTTP 429\n- apple-feed: The read operation timed out\n"
        d=m.failures(text)
        self.assertEqual(d["reddit-one"],"HTTP 429")
        self.assertNotIn("foo",d)
    def test_streak_recovery(self):
        a=m.next_state({},{"reddit-one":"HTTP 429"})
        b=m.next_state(a,{"reddit-one":"HTTP 429"})
        self.assertEqual(b["reddit-one"]["streak"],2)
        self.assertFalse(m.next_state(b,{}))
    def test_deferred_sources_do_not_fake_recovery(self):
        before=m.next_state({},{"reddit-one":"HTTP 429"})
        deferred=m.next_state(before,{},{"reddit-one":"HTTP 429"})
        self.assertEqual(deferred["reddit-one"]["streak"],1)
        after=m.next_state(deferred,{"reddit-one":"HTTP 429"},{})
        self.assertEqual(after["reddit-one"]["streak"],2)
        self.assertFalse(m.next_state(after,{},{}))
        source_health = "# health\\n## Deferred feeds — retry after temporary cooldown\\n- reddit-one: HTTP 429\\n"
        self.assertIn("reddit-one",m.deferred(source_health.replace("\\n","\n")))
        self.assertIn("cooling down",m.render(deferred,{"reddit-one":"HTTP 429"}))

    def test_prior_untracked_cooldown_is_not_hidden(self):
        state=m.next_state({}, {}, {"reddit-one":"HTTP 429"})
        self.assertIn("reddit-one",state)
        self.assertEqual(state["reddit-one"]["streak"],0)
        self.assertIn("cooling down",m.render(state,{"reddit-one":"HTTP 429"}))

    def test_respect_rate_limit(self):
        r=m.render({"redd": {"reason":"HTTP 429","streak":3}})
        self.assertIn("reduce frequency",r)
        self.assertIn("3",r)
if __name__=="__main__":
    unittest.main()
