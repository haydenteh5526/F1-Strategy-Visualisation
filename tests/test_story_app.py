"""Run the story interface headlessly and check what it shows."""
from pathlib import Path
import sys
import unittest

import pandas as pd
from streamlit.testing.v1 import AppTest

APP = Path(__file__).resolve().parents[1]/'app/story.py'
sys.path.insert(0, str(APP.parent))
import charts  # noqa: E402


class StoryAppTests(unittest.TestCase):
    def setUp(self):
        self.app = AppTest.from_file(str(APP), default_timeout=30).run()

    def test_runs_without_errors(self):
        self.assertFalse(self.app.exception)
        self.assertEqual(len(self.app.get('vega_lite_chart')), 5)
        self.assertEqual(len(self.app.dataframe), 2)

    def test_strategy_table_matches_stints(self):
        strategy = self.app.dataframe[0].value.set_index('Driver')
        self.assertEqual(len(strategy), 6)
        self.assertEqual(strategy.loc['HAM', 'Tyres (laps)'],
                         'Medium 1–12 → Hard 13–25 → Soft (used) 26–42 → Hard 43–71')
        self.assertEqual(strategy['Pit stops'].sum(), 14)

    def test_team_filter_limits_every_table(self):
        self.app.multiselect[0].set_value(['Ferrari']).run()
        self.assertFalse(self.app.exception)
        for table in self.app.dataframe:
            self.assertEqual(set(table.value.Team), {'Ferrari'})

    def test_pace_chart_values_match_prepared_data(self):
        pace = pd.read_csv(APP.parents[1]/'data/processed/austria-2026/pace_laps.csv')
        summary = charts.pace_summary(pace).set_index('Driver')
        for driver, laps in pace.groupby('Driver'):
            self.assertAlmostEqual(summary.loc[driver, 'Typical'], laps.LapTimeSeconds.median())
            self.assertEqual(summary.loc[driver, 'Laps'], len(laps))

    def test_vsc_laps_are_summarised(self):
        self.assertTrue(any('laps 24–26, 52–53' in text.value for text in self.app.markdown))


if __name__ == '__main__':
    unittest.main()
