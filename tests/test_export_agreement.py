"""The static exports plot the same values the dashboard draws, view by view.

Most dashboard views are drawn by the replay script from its own data payload, while the exports are Altair charts.
These tests read the values embedded in each exported chart and compare them with that payload, so a change to one
side that is not made to the other is caught. The matched-pace export and dashboard chart share one function and
are checked against the exploration tables in test_matched_dashboard.py.
"""
from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'app'))
spec = importlib.util.spec_from_file_location('export_figures', ROOT/'scripts/export_figures.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
import replay  # noqa: E402


def embedded(chart, *columns: str) -> pd.DataFrame:
    """The largest dataset in an exported chart that has all the given columns."""
    found = [rows for rows in chart.to_dict().get('datasets', {}).values()
             if rows and all(c in rows[0] for c in columns)]
    if not found:
        raise AssertionError(f'No exported dataset has columns {columns}')
    return pd.DataFrame(max(found, key=len))


class ExportAgreementTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        data = module.charts.load_data(module.DATA)
        cls.figures = module.figures(data)
        cls.payload = replay.race_data(data['laps'], 'light')
        cls.laps = pd.DataFrame([{'Driver': d['code'], **lap} for d in cls.payload['drivers'] for lap in d['laps']])

    def test_stint_timeline_matches_the_dashboard_stints(self):
        exported = embedded(self.figures['stint-timeline'], 'Driver', 'Stint', 'Compound', 'FirstLap', 'LastLap')
        exported = exported.drop_duplicates(['Driver', 'Stint']).astype({'Stint': int, 'FirstLap': int, 'LastLap': int})
        shown = self.laps.groupby(['Driver', 'stint']).agg(Compound=('compound', 'first'), FirstLap=('lap', 'min'),
                                                           LastLap=('lap', 'max')).reset_index().rename(columns={'stint': 'Stint'})
        keys = ['Driver', 'Stint']
        self.assertEqual(len(exported), 20)
        pd.testing.assert_frame_equal(exported[shown.columns].sort_values(keys).reset_index(drop=True),
                                      shown.sort_values(keys).reset_index(drop=True), check_dtype=False)

    def test_pace_summary_matches_the_dashboard_bars(self):
        exported = embedded(self.figures['pace'], 'Driver', 'Typical', 'Low', 'High', 'Laps').set_index('Driver')
        for bar in self.payload['pace']:
            with self.subTest(driver=bar['code']):
                row = exported.loc[bar['code']]
                self.assertAlmostEqual(row.Typical, bar['typical'], places=6)
                self.assertAlmostEqual(row.Low, bar['low'], places=6)
                self.assertAlmostEqual(row.High, bar['high'], places=6)
                self.assertEqual(int(row.Laps), bar['n'])
        self.assertEqual(set(exported.index), {bar['code'] for bar in self.payload['pace']})

    def test_tyre_age_dots_match_the_dashboard_dots(self):
        exported = embedded(self.figures['tyre-age'], 'Driver', 'Stint', 'TyreLife', 'LapTimeSeconds')
        shown = self.laps.loc[self.laps.normal]
        self.assertEqual(len(exported), len(shown))
        self.assertEqual(len(shown), self.payload['normalLaps'])
        as_set = lambda frame, cols: set(zip(*(frame[c].round(6) if frame[c].dtype.kind == 'f' else frame[c] for c in cols)))
        self.assertEqual(as_set(exported.astype({'Stint': int, 'TyreLife': int}), ['Driver', 'Stint', 'TyreLife', 'LapTimeSeconds']),
                         as_set(shown, ['Driver', 'stint', 'age', 'time']))

    def test_positions_and_pit_markers_match_the_dashboard(self):
        chart = self.figures['positions']
        exported = embedded(chart, 'Driver', 'LapNumber', 'Position')
        self.assertEqual(set(zip(exported.Driver, exported.LapNumber.astype(int), exported.Position.astype(int))),
                         set(zip(self.laps.Driver, self.laps.lap, self.laps.pos)))
        stops = embedded(chart, 'Driver', 'EntryLap')
        self.assertEqual(set(zip(stops.Driver, stops.EntryLap.astype(int))),
                         set(zip(self.laps.loc[self.laps.pitIn, 'Driver'], self.laps.loc[self.laps.pitIn, 'lap'])))

    def test_vsc_bands_and_laps_match_the_dashboard(self):
        chart = self.figures['vsc']
        bands = embedded(chart, 'Start', 'End', 'Label')
        self.assertEqual(sorted([int(b.Start)-1, int(b.End)] for b in bands.itertuples()), sorted(self.payload['vsc']))
        dots = embedded(chart, 'Driver', 'LapNumber', 'LapTimeSeconds', 'Phase')
        exported = dots.loc[dots.Phase.eq('VSC lap')]
        shown = {(s['code'], p['lap'], round(p['time'], 6)) for e in self.payload['events'] for s in e['series']
                 for p in s['points'] if p['vscLap'] and p['time'] is not None}
        self.assertEqual(len(shown), 21)   # Every non-pit VSC-affected lap is kept in both views.
        self.assertEqual(set(zip(exported.Driver, exported.LapNumber.astype(int), exported.LapTimeSeconds.round(6))), shown)


if __name__ == '__main__':
    unittest.main()
