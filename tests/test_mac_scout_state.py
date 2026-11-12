"""Real runner state recovery tests; no collector, network or installed state access."""
import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import mac_scout as scout


class StateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.state = self.root / 'state.json'
        for name, value in [('HOME', self.root), ('STATE', self.state),
                            ('STOP', self.root / 'STOP'), ('LOGS', self.root / 'logs')]:
            p = patch.object(scout, name, str(value))
            p.start()
            self.addCleanup(p.stop)

    def refuses(self, text):
        self.state.write_text(text)
        with patch.object(scout, 'cycle', return_value=(True, {'skipped': 'nothing due'})) as cycle:
            self.assertEqual(1, scout.run())
        cycle.assert_not_called()
        self.assertEqual(text, self.state.read_text(), 'Invalid state was overwritten')

    def test_missing_state_can_start_normally(self):
        with patch.object(scout, 'cycle', return_value=(True, {'skipped': 'nothing due'})) as cycle:
            self.assertEqual(0, scout.run())
        cycle.assert_called_once()
        self.assertEqual(0, json.loads(self.state.read_text())['failures'])

    def test_malformed_json_does_not_reset_schedule(self):
        self.refuses('{"retry_research": true,')

    def test_non_object_state_is_reported_without_traceback(self):
        for text in ('[]', 'null', '42', '"state"'):
            with self.subTest(text=text):
                self.refuses(text)

    def test_invalid_schedule_fields_do_not_start_collectors(self):
        for state in ({'backoff_until': 'tomorrow'}, {'last_research': float('nan')},
                      {'last_discovery': True}, {'backoff_until': 10 ** 400},
                      {'last_research': 1e30}, {'retry_research': 'yes'},
                      {'failures': -1}, {'failures': 1.5}, {'last_receipt': []}):
            with self.subTest(state=state):
                self.refuses(json.dumps(state))

    def test_status_preserves_invalid_state_and_returns_failure(self):
        self.state.write_text('[]')
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(1, scout.status())
        self.assertEqual('[]', self.state.read_text())


if __name__ == '__main__':
    unittest.main()
