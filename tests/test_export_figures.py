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


if __name__ == '__main__':
    unittest.main()
