"""Check the data each replay car drives on, and what the replay actually draws."""
from pathlib import Path
import json
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
  const context = vm.createContext({document: {getElementById: id => id === 'chart' ? svg : {classList: {}}}, console,
                                    matchMedia: () => ({matches: true}), requestAnimationFrame: () => {}, addEventListener: () => {}});
  vm.runInContext(src, context);  // Reduced motion, so this draws the finished race.
  const [mode, arg] = [process.argv[1], process.argv[2]];
  if (mode === 'eval') return process.stdout.write(JSON.stringify(vm.runInContext(arg, context)));
  if (mode !== 'end') vm.runInContext(`frame(${mode})`, context);  // Redraw at a session time.
  process.stdout.write(svg.innerHTML);
});
"""


def run_node(page: str, *args: str) -> str:
    script = re.search(r'<script>(.*)</script>', page, re.S).group(1)
    return subprocess.run(['node', '-e', NODE, *args], input=script, capture_output=True, text=True, check=True).stdout


def render(page: str, at: float | None = None) -> str:
    """Run the replay's own drawing script and return the SVG, at the end of the race or at a session time (seconds)."""
    return run_node(page, 'end' if at is None else str(at))


def evaluate(page: str, expression: str):
    """Evaluate a JavaScript expression inside the replay's own script and return its JSON value."""
    return json.loads(run_node(page, 'eval', expression))


@unittest.skipUnless(shutil.which('node'), 'needs Node.js to run the replay script')
class ReplayRenderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.laps = charts.load_data(ROOT/'data/processed/austria-2026')['laps']
        cls.page = lambda self, kind, height=480: replay.html(self.laps, kind, 'dark', height)

    def test_event_view_draws_the_affected_laps_and_both_windows(self):
        drawn = render(self.page('event', 800))
        self.assertIn('HAD lap 25: 100.460 s', drawn)
        self.assertNotIn('HAD lap 1: ', drawn)
        for title in ['VSC 1 (cars must slow down) · laps 23–27', 'VSC 2 (cars must slow down) · laps 51–54', 'DEPLOYED', 'ENDING', 'CLEAR',
                      'HAM has no non-pit lap-time observation in VSC 1']:
            self.assertIn(title, drawn)

    def test_event_view_places_laps_on_the_session_clock_only(self):
        events = evaluate(self.page('event', 800), 'D.events')
        for event in events:
            for series in event['series']:
                self.assertTrue(all(event['before'] <= p['lap'] <= event['after'] for p in series['points']))
        first = events[0]['series'][0]['points'][0]
        row = self.laps[(self.laps.Driver == events[0]['series'][0]['code']) & (self.laps.LapNumber == first['lap'])].iloc[0]
        self.assertAlmostEqual(first['x'], row.TimeSeconds - events[0]['start'], places=3)

    def test_pit_clock_separates_overlap_from_flagged_laps(self):
        drawn = render(self.page('pitclock'))
        self.assertIn('HAM lap 25: pit lane', drawn)
        self.assertIn('STOPPED DURING THE VSC · 21.2 s of it', drawn)
        self.assertEqual(drawn.count('TOO CLOSE TO CALL'), 1)
        self.assertEqual(drawn.count('flagged lap · stop was outside the VSC'), 1)
        self.assertIn('All 14 pit visits across the race', drawn)
        self.assertEqual(drawn.count('(cars must slow down)'), 2)

    def test_positions_change_only_when_a_lap_is_completed(self):
        page = self.page('positions', 420)
        for driver_index, driver in enumerate(self.laps.Driver.unique()):
            recorded = self.laps[self.laps.Driver == driver].set_index('LapNumber').Position
            order = evaluate(page, 'D.drivers.map(d => d.code)')
            i = order.index(driver)
            for lap in [10, 24, 51]:
                held = evaluate(page, f'[{lap}.01, {lap}.5, {lap}.99].map(p => posAt(D.drivers[{i}], p))')
                self.assertEqual(held, [int(recorded[lap])]*3, (driver, lap))

    def test_event_view_marks_a_normal_lap_and_the_slowest_lap(self):
        drawn = render(self.page('event', 800))
        self.assertEqual(drawn.count('a normal lap ≈'), 2)
        self.assertIn('slowest lap: HAD lap 25, 100.5 s', drawn)

    def test_pace_view_shows_sample_counts_and_teammate_shapes(self):
        drawn = render(self.page('pace', 400))
        counts = self.laps[self.laps.EligibleForPace].groupby('Driver').size()
        for driver, n in counts.items():
            self.assertIn(f'from {n} laps', drawn)
        # Each team's second driver is a triangle, both beside the driver name and as the typical-lap mark.
        self.assertEqual(len(re.findall(r'Z" fill="#[0-9a-f]{6}" stroke=', drawn)), 6)

    def test_tyre_age_view_has_one_point_per_normal_lap_and_no_lines(self):
        drawn = render(self.page('tyres', 650))
        self.assertEqual(drawn.count('tyre age'), int(self.laps.EligibleForPace.sum()))
        self.assertNotIn('<polyline', drawn)

    def test_every_replay_draws(self):
        for kind, height in [('timeline', 400), ('pace', 400), ('tyres', 650), ('pitclock', 480), ('event', 800), ('positions', 420)]:
            with self.subTest(kind):
                self.assertIn('<defs>', render(self.page(kind, height)))


if __name__ == '__main__':
    unittest.main()
