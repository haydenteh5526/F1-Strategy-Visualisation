"""Keep the committed exploration summary and figures in step with the prepared data."""
import importlib.util
import json
from pathlib import Path
import unittest

import pandas as pd
import vl_convert as vlc

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('explore_pace_tyres', ROOT/'scripts/explore_pace_tyres.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class ExplorationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.laps = module.charts.load_data(module.DATA)['laps']
        cls.raw = pd.read_csv(module.RAW_LAPS, dtype={'DriverNumber': str}) if module.RAW_LAPS.exists() else None
        cls.summary = module.summarise(cls.laps, cls.raw)

    def test_committed_summary_matches_a_fresh_run(self):
        fresh = json.loads(json.dumps(self.summary, ensure_ascii=False))
        committed = json.loads(module.SUMMARY.read_text(encoding='utf-8'))
        if self.raw is None:  # The traffic check needs the raw snapshot.
            committed['traffic'] = fresh['traffic']
        self.assertEqual(fresh, committed)

    def test_every_figure_renders(self):
        for name, chart in module.figures(self.laps, self.summary).items():
            with self.subTest(name):
                self.assertIn('<svg', vlc.vegalite_to_svg(chart.to_dict()))


if __name__ == '__main__':
    unittest.main()
