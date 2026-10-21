"""Check the data each replay car drives on, and what the replay actually draws."""
from pathlib import Path
import re
import shutil
import subprocess
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


NODE = r"""
const vm = require('vm'); let src = '';
process.stdin.on('data', chunk => src += chunk).on('end', () => {
  const svg = {clientWidth: 1000, innerHTML: ''};
  const context = vm.createContext({document: {getElementById: id => id === 'chart' ? svg : {}}, console,
                                    matchMedia: () => ({matches: true}), requestAnimationFrame: () => {}, addEventListener: () => {}});
  vm.runInContext(src, context);  // Reduced motion, so this draws the finished race.
  if (process.argv[1] !== 'end') vm.runInContext(`frame(${process.argv[1]})`, context);  // Redraw at a session time.
  process.stdout.write(svg.innerHTML);
});
"""


def render(page: str, at: float | None = None) -> str:
    """Run the replay's own drawing script and return the SVG, at the end of the race or at a session time (seconds)."""
    script = re.search(r'<script>(.*)</script>', page, re.S).group(1)
    return subprocess.run(['node', '-e', NODE, 'end' if at is None else str(at)], input=script,
                          capture_output=True, text=True, check=True).stdout


@unittest.skipUnless(shutil.which('node'), 'needs Node.js to run the replay script')
class ReplayRenderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.laps = charts.load_data(ROOT/'data/processed/austria-2026')['laps']

    def test_vsc_chart_draws_vsc_laps_and_markers(self):
        drawn = render(replay.html(self.laps, 'vsc', 'dark', 420))
        self.assertIn('HAD lap 25: 100.460 s', drawn)
        self.assertEqual(drawn.count('>VSC</text>'), 2)
        self.assertNotIn('HAD lap 1: ', drawn)

    def test_vsc_status_follows_the_recorded_clock(self):
        page = replay.html(self.laps, 'vsc', 'dark', 420)
        for name, start, ending, clear in [(w['event'], w['start'], w['ending'], w['clear']) for w in
                                           [{'event': f'VSC {i}', **c} for i, c in enumerate(replay.vsc_clock(), 1)]]:
            with self.subTest(name):
                self.assertNotIn('VSC DEPLOYED', render(page, start-30))   # Affected laps have begun; VSC has not.
                self.assertNotIn('VSC ENDING', render(page, start-30))
                self.assertIn('VSC DEPLOYED', render(page, start+1))
                self.assertIn('VSC ENDING', render(page, ending+1))
                self.assertNotIn('VSC DEPLOYED', render(page, ending+1))
                self.assertNotIn('VSC ENDING', render(page, clear+1))

    def test_no_status_text_without_the_recorded_clock(self):
        page = replay.html(self.laps, 'vsc', 'dark', 420).replace('"vscClock": [', '"vscClock": [], "unused": [')
        self.assertNotIn('VSC DEPLOYED', render(page, replay.vsc_clock()[0]['start']+1))

    def test_every_replay_draws(self):
        for kind in ['timeline', 'positions', 'pace', 'tyres', 'vsc']:
            with self.subTest(kind):
                self.assertIn('<defs>', render(replay.html(self.laps, kind, 'dark', 420)))


if __name__ == '__main__':
    unittest.main()
