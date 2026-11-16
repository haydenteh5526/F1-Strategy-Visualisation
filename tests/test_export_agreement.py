"""The static exports draw the same values the dashboard draws, view by view.

Most dashboard views are drawn by the replay script from its own data payload, while the exports are Altair charts.
These tests render each export to SVG and read the marks that were actually drawn (Vega labels every data mark for
screen readers), so a value that is still in a chart's data but filtered out or hidden by a transform is caught. They
compare those marks with the dashboard payload. The matched-pace export and dashboard chart share one function and
are checked against the exploration tables in test_matched_dashboard.py.
"""
from __future__ import annotations

import importlib.util
import sys
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

import vl_convert as vlc

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'app'))
spec = importlib.util.spec_from_file_location('export_figures', ROOT/'scripts/export_figures.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
import replay  # noqa: E402


def drawn(chart, kind: str) -> list[dict[str, str]]:
    """Fields of every rendered mark of one kind, read from the labels Vega writes on each mark in the SVG."""
    root = ET.fromstring(vlc.vegalite_to_svg(chart.to_dict()))
    marks = []
    for element in root.iter():
        if element.get('role') == 'graphics-symbol' and element.get('aria-roledescription') == kind:
            fields = (part.split(': ', 1) for part in element.get('aria-label', '').split('; '))
            marks.append({key: value for key, value in (f for f in fields if len(f) == 2)})
    return marks


def number(text: str) -> float:
    return float(text.replace('−', '-'))


def time(value: float) -> float:
    return round(value, 3)


class ExportAgreementTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        data = module.charts.load_data(module.DATA)
        cls.figures = module.figures(data)
        cls.payload = replay.race_data(data['laps'], 'light')
        cls.laps = [{'Driver': d['code'], **lap} for d in cls.payload['drivers'] for lap in d['laps']]

    def test_stint_timeline_draws_the_dashboard_stints(self):
        stints = {}
        for lap in self.laps:
            first, last, compound = stints.get((lap['Driver'], lap['stint']), (lap['lap'], lap['lap'], lap['compound']))
            stints[(lap['Driver'], lap['stint'])] = (min(first, lap['lap']), max(last, lap['lap']), compound)
        shown = {(driver, first, last, compound) for (driver, _), (first, last, compound) in stints.items()}
        exported = {(m['Driver'], *map(int, m['Laps'].split('–')), m['Compound'])
                    for m in drawn(self.figures['stint-timeline'], 'point')}
        self.assertEqual(len(shown), 20)
        self.assertEqual(exported, shown)

    def test_pace_summary_draws_the_dashboard_bars(self):
        exported = {m['Driver']: m for m in drawn(self.figures['pace'], 'point')}
        self.assertEqual(set(exported), {bar['code'] for bar in self.payload['pace']})
        for bar in self.payload['pace']:
            with self.subTest(driver=bar['code']):
                mark = exported[bar['code']]
                self.assertEqual(number(mark['Typical lap (s)']), time(bar['typical']))
                self.assertEqual(number(mark['Middle half from (s)']), time(bar['low']))
                self.assertEqual(number(mark['Middle half to (s)']), time(bar['high']))
                self.assertEqual(int(mark['Laps']), bar['n'])

    def test_tyre_age_draws_every_dashboard_dot(self):
        marks = drawn(self.figures['tyre-age'], 'circle')
        exported = {(m['Driver'], int(m['Stint']), int(m['Tyre age (laps)']), number(m['Lap time (s)'])) for m in marks}
        shown = {(lap['Driver'], lap['stint'], lap['age'], time(lap['time'])) for lap in self.laps if lap['normal']}
        self.assertEqual(len(marks), self.payload['normalLaps'])
        self.assertEqual(exported, shown)

    def test_positions_and_pit_markers_match_the_dashboard(self):
        points = drawn(self.figures['positions'], 'point')
        stops = {(m['Driver'], int(m['Lap'])) for m in points if 'Pit stop on lap' in m}
        positions = {(m['Driver'], int(m['Lap']), int(m['Position'])) for m in points if 'Pit stop on lap' not in m}
        self.assertEqual(positions, {(lap['Driver'], lap['lap'], lap['pos']) for lap in self.laps})
        self.assertEqual(stops, {(lap['Driver'], lap['lap']) for lap in self.laps if lap['pitIn']})
        self.assertEqual(len(stops), 14)

    def test_vsc_bands_and_laps_match_the_dashboard(self):
        chart = self.figures['vsc']
        bands = sorted([int(m['Lap']), int(m['End'])] for m in drawn(chart, 'rect mark'))
        self.assertEqual(bands, sorted(self.payload['vsc']))
        exported = {(m['Driver'], int(m['Lap']), number(m['Lap time (s)']))
                    for m in drawn(chart, 'point') if m.get('Phase') == 'VSC lap'}
        shown = {(s['code'], p['lap'], time(p['time'])) for e in self.payload['events'] for s in e['series']
                 for p in s['points'] if p['vscLap'] and p['time'] is not None}
        self.assertEqual(len(shown), 21)   # Every non-pit VSC-affected lap is drawn in both views.
        self.assertEqual(exported, shown)


if __name__ == '__main__':
    unittest.main()
