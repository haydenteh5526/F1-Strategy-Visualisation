"""Render every exported chart, so chart expression errors are caught before images are made."""
import importlib.util
from pathlib import Path
import unittest

import vl_convert as vlc

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('export_figures', ROOT/'scripts/export_figures.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class ExportFigureTests(unittest.TestCase):
    def test_every_figure_renders(self):
        figures = module.figures(module.charts.load_data(module.DATA))
        self.assertEqual(len(figures), 6)
        for name, chart in figures.items():
            with self.subTest(name):
                self.assertIn('<svg', vlc.vegalite_to_svg(chart.to_dict()))


class ExportLabelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.laps = module.charts.load_data(module.DATA)['laps']
        cls.pace = cls.laps.loc[cls.laps.EligibleForPace]

    def test_tyre_age_labels_clear_every_dot_and_label_inside_the_panel(self):
        charts, pace = module.charts, self.pace
        stint_laps = pace.groupby(['Driver', 'Stint']).LapNumber.transform('size')
        labels = 'S'+pace.Stint.astype(int).astype(str)+' '+pace.Compound.str[0]+' · '+stint_laps.astype(str)+' laps'
        placed = charts.label_boxes(pace, labels)
        self.assertEqual(len(placed), 20)   # One label per stint.
        self.assertTrue(placed.Clear.all())
        (x0, x1), (y0, y1) = charts.tyre_domains(pace)
        w, h = charts.TYRE_PANEL['width'], charts.TYRE_PANEL['height']
        for driver, rows in placed.join(pace.Driver).groupby('Driver'):
            boxes = list(rows.Box)
            dots = pace.loc[pace.Driver.eq(driver)]
            for i, (left, top, right, bottom) in enumerate(boxes):
                with self.subTest(driver=driver, label=labels[rows.index[i]]):
                    self.assertTrue(0 <= left and right <= w and 0 <= top and bottom <= h)
                    for a, t in zip(dots.TyreLife, dots.LapTimeSeconds):
                        x, y = (a-x0)/(x1-x0)*w, (y1-t)/(y1-y0)*h
                        self.assertFalse(left < x < right and top < y < bottom)
                    for other in boxes[i+1:]:
                        self.assertFalse(left < other[2] and other[0] < right and top < other[3] and other[1] < bottom)

    def test_matched_counts_never_cross_the_zero_line(self):
        summary = module.charts.matched_pace(self.laps)
        spec = module.charts.matched_pace_chart(summary).to_dict()
        sides = {(r['Pair'], r['Window'], r['Compound']): r['Side'] for r in spec['datasets'][spec['data']['name']]}
        self.assertEqual(sides[('ANT − RUS', '41–60', 'HARD')], 'left')   # −0.077 s: a right-hand label would cross zero.
        self.assertEqual(sides[('HAM − LEC', '1–20', 'HARD')], 'left')    # −0.214 s.
        self.assertEqual(sides[('ANT − RUS', '61–71', 'HARD')], 'right')  # −0.883 s: room before zero.
        self.assertEqual(sides[('ANT − RUS', '1–20', 'MEDIUM')], 'right') # Positive values point away from zero already.

    def test_vsc_laps_are_drawn_larger_than_other_laps(self):
        layer = module.charts.vsc_chart(self.laps, 'light').to_dict()['layer'][-1]
        scale = layer['encoding']['size']['scale']
        self.assertEqual(scale['domain'], ['VSC lap', 'Other lap'])
        self.assertGreater(scale['range'][0], scale['range'][1])


if __name__ == '__main__':
    unittest.main()
