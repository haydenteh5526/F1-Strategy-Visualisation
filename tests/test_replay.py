"""Check the data each replay car drives on."""
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'app'))
import charts  # noqa: E402
import replay  # noqa: E402


class ReplayDataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.laps = charts.load_data(ROOT/'data/processed/austria-2026')['laps']
        cls.data = replay.race_data(cls.laps, 'dark')

    def test_every_lap_follows_on_from_the_last(self):
        self.assertEqual(len(self.data['drivers']), 6)
        for driver in self.data['drivers']:
            laps = driver['laps']
            self.assertEqual([lap['lap'] for lap in laps], list(range(1, 72)), driver['code'])
            self.assertTrue(all(lap['end'] > lap['start'] for lap in laps), driver['code'])
            self.assertTrue(all(b['start'] == a['end'] for a, b in zip(laps, laps[1:])), driver['code'])

    def test_finishing_positions_match_the_prepared_laps(self):
        final = self.laps.loc[self.laps.LapNumber.eq(71)].set_index('Driver').Position
        for driver in self.data['drivers']:
            self.assertEqual(driver['laps'][-1]['pos'], final[driver['code']])

    def test_race_clock_and_vsc_bands(self):
        self.assertEqual(self.data['vsc'], [[23, 26], [51, 53]])
        self.assertLess(self.data['t0'], self.data['t1'])
        self.assertIn('LAP ${leaderLap}', replay.html(self.laps, 'positions', 'dark', 420))


if __name__ == '__main__':
    unittest.main()
