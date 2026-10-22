"""Check dashboard comparisons against the reviewed exploration evidence."""
from pathlib import Path
import sys
import unittest

import pandas as pd
import vl_convert as vlc

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'app'))
import charts


class MatchedDashboardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.laps = charts.load_data(ROOT/'data/processed/austria-2026')['laps']

    def test_every_window_matches_reviewed_exploration(self):
        actual = charts.matched_pace(self.laps).drop(columns='Pair')
        expected = pd.read_csv(ROOT/'docs/pace-tyre-exploration/matched_windows.csv')
        keys = ['Team', 'Window', 'Compound']
        pd.testing.assert_frame_equal(actual.sort_values(keys).reset_index(drop=True),
                                      expected.sort_values(keys).reset_index(drop=True),
                                      check_dtype=False, atol=1e-6, rtol=0)
        self.assertEqual(actual.MatchedLaps.sum(), 126)

    def test_all_stints_match_reviewed_counts_and_ages(self):
        actual = charts.stint_context(self.laps)
        expected = pd.read_csv(ROOT/'docs/pace-tyre-exploration/stint_summary.csv')[actual.columns]
        keys = ['Team', 'Driver', 'Stint']
        pd.testing.assert_frame_equal(actual.sort_values(keys).reset_index(drop=True),
                                      expected.sort_values(keys).reset_index(drop=True), check_dtype=False)

    def test_no_eligible_laps_or_teammate_does_not_invent_pairs(self):
        no_pace = self.laps.assign(EligibleForPace=False)
        self.assertTrue(charts.matched_pace(no_pace).empty)
        self.assertTrue(charts.matched_pace(self.laps.loc[self.laps.Driver.eq('ANT')]).empty)
        context = charts.stint_context(no_pace)
        self.assertEqual(context.RecordedLaps.sum(), 426)
        self.assertEqual(context.EligibleLaps.sum(), 0)

    def test_chart_driver_rows_follow_the_team_filter(self):
        summary = charts.matched_pace(self.laps.loc[self.laps.Team.eq('Mercedes')])
        spec = charts.matched_pace_chart(summary.loc[summary.Window.eq('1–20')]).to_dict()
        self.assertEqual(spec['layer'][1]['encoding']['y']['scale']['domain'], ['ANT − RUS'])

    def test_chart_renders_sparse_samples_in_both_themes(self):
        summary = charts.matched_pace(self.laps)
        hard = summary.loc[summary.Compound.eq('HARD') & summary.Window.eq('21–40')]
        for mode in ['light', 'dark']:
            svg = vlc.vegalite_to_svg(charts.matched_pace_chart(hard, mode).to_dict())
            self.assertIn('n=3', svg)
            self.assertIn('Fewer than 5 pairs', svg)


if __name__ == '__main__':
    unittest.main()
