"""Run the story interface headlessly and check what it shows."""
from pathlib import Path
import re
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

    def go_to(self, slide):
        while self.app.session_state.slide != slide:
            self.app.button(key='next').click().run()
        self.assertFalse(self.app.exception)

    def test_every_slide_shows_one_chart(self):
        titles = set()
        for slide in range(5):
            self.go_to(slide)
            charts_shown = len(self.app.get('vega_lite_chart'))+len(self.app.get('iframe'))
            self.assertEqual(charts_shown, 1)
            titles.add(self.app.subheader[0].value)
        self.assertEqual(len(titles), 5)

    def test_arrows_wrap_around(self):
        self.app.button(key='previous').click().run()
        self.assertEqual(self.app.session_state.slide, 4)
        self.app.button(key='next').click().run()
        self.assertEqual(self.app.session_state.slide, 0)

    def test_race_facts(self):
        cards = next(h.proto.body for h in self.app.get('html') if 'f1-facts' in h.proto.body)
        facts = dict(re.findall(r'class="label">([^<]+)</div><div class="value" data-value="([^"]+)"', cards))
        self.assertEqual(facts['Race laps'], '71')
        self.assertEqual(facts['Pit stops, selected teams'], '14')
        self.assertEqual(facts['Virtual Safety Car periods'], '2')

    def test_strategy_table_matches_stints(self):
        strategy = self.app.dataframe[0].value.set_index('Driver')
        self.assertEqual(len(strategy), 6)
        self.assertEqual(strategy.loc['HAM', 'Tyres (laps)'],
                         'Medium 1–12 → Hard 13–25 → Soft (used) 26–42 → Hard 43–71')
        self.assertEqual(strategy['Pit stops'].sum(), 14)

    def test_team_filter_limits_tables(self):
        self.app.multiselect[0].set_value(['Ferrari']).run()
        for slide in [0, 3]:
            self.go_to(slide)
            self.assertEqual(set(self.app.dataframe[0].value.Team), {'Ferrari'})

    def test_pace_chart_values_match_prepared_data(self):
        pace = pd.read_csv(APP.parents[1]/'data/processed/austria-2026/pace_laps.csv')
        summary = charts.pace_summary(pace).set_index('Driver')
        for driver, laps in pace.groupby('Driver'):
            self.assertAlmostEqual(summary.loc[driver, 'Typical'], laps.LapTimeSeconds.median())
            self.assertEqual(summary.loc[driver, 'Laps'], len(laps))

    def test_vsc_laps_are_summarised(self):
        self.go_to(4)
        self.assertTrue(any('laps 24–26, 52–53' in text.value for text in self.app.markdown))


if __name__ == '__main__':
    unittest.main()
