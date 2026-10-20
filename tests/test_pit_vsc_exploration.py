"""Guard event boundaries, clock pairing and retention of the VSC observations."""
import importlib.util
import json
from pathlib import Path
import unittest

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('explore_pit_vsc', ROOT/'scripts/explore_pit_vsc.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class EventBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.status = pd.DataFrame({'Time': pd.to_timedelta([0, 10, 20, 25], unit='s'),
                                    'Status': ['1', '6', '7', '1']})

    def test_ending_remains_restricted_until_green(self):
        window = module.vsc_windows(self.status)[0]
        self.assertEqual(window['deployed_seconds'], 10)
        self.assertEqual(window['restriction_seconds'], 15)
        self.assertEqual(module.overlap_seconds(21, 24, 10, window['clear_seconds']), 3)

    def test_touching_and_crossing_boundaries_are_distinct(self):
        self.assertEqual(module.overlap_seconds(5, 10, 10, 25), 0)
        self.assertEqual(module.overlap_seconds(25, 30, 10, 25), 0)
        self.assertEqual(module.overlap_seconds(9, 12, 10, 25), 2)

    def test_missing_green_or_deployment_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Unclosed'):
            module.vsc_windows(self.status.iloc[:-1])
        with self.assertRaisesRegex(ValueError, 'without'):
            module.vsc_windows(self.status.iloc[[0, 2, 3]])

    def test_out_of_order_status_timestamps_are_rejected(self):
        with self.assertRaisesRegex(ValueError, 'increasing'):
            module.vsc_windows(self.status.iloc[[0, 2, 1, 3]])

    def test_missing_or_inconsistent_message_pairs_are_rejected(self):
        windows = module.vsc_windows(self.status)
        messages = pd.DataFrame({'Message': ['VSC DEPLOYED', 'VSC ENDING'],
                                 'Time': ['2026-01-01 12:00:10', '2026-01-01 12:00:20'], 'Lap': [2, 3]})
        self.assertEqual(module.align_messages(windows, messages)['maximum_residual_seconds'], 0)
        with self.assertRaisesRegex(ValueError, 'count or order'):
            module.align_messages(windows, messages.iloc[:1])
        messages.loc[1, 'Time'] = '2026-01-01 12:00:25'
        with self.assertRaisesRegex(ValueError, 'clocks disagree'):
            module.align_messages(windows, messages)


class PublishedExplorationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.summary = json.loads((ROOT/'docs/pit-vsc-exploration/summary.json').read_text())
        cls.pits = pd.read_csv(ROOT/'docs/pit-vsc-exploration/pit_event_comparisons.csv')
        cls.laps = pd.read_csv(ROOT/'data/processed/austria-2026/selected_laps.csv')

    def test_recorded_boundary_cases_stay_distinct_from_whole_lap_flags(self):
        pits = self.pits.set_index(['Driver', 'EntryLap'])
        self.assertEqual(int(self.pits.TimestampOverlapsVSC.sum()), 1)
        self.assertEqual(int(self.pits.WholeLapHasVSC.sum()), 3)
        self.assertFalse(pits.loc[('ANT', 24), 'TimestampOverlapsVSC'])
        self.assertTrue(pits.loc[('ANT', 24), 'WithinOneSecondOfBoundary'])
        self.assertAlmostEqual(pits.loc[('ANT', 24), 'NearestVSCBoundarySeconds'], .132)
        self.assertFalse(pits.loc[('ANT', 51), 'TimestampOverlapsVSC'])
        self.assertAlmostEqual(pits.loc[('ANT', 51), 'NearestVSCBoundarySeconds'], 48.957)
        self.assertTrue(pits.loc[('HAM', 25), 'TimestampOverlapsVSC'])

    def test_all_affected_nonpit_laps_reach_the_plot_data(self):
        plotted = pd.concat([module.lap_time_plot_rows(self.laps, e) for e in self.summary['windows']])
        actual = plotted.loc[plotted.HasVSC]
        self.assertEqual(len(actual), 21)
        self.assertEqual(actual.index.nunique(), 21)
        self.assertEqual(actual.loc[actual.Driver.eq('HAD') & actual.LapNumber.eq(25), 'LapTimeSeconds'].iloc[0], 100.460)

    def test_before_after_tables_use_common_laps_on_the_correct_side(self):
        comparisons = pd.read_csv(ROOT/'docs/pit-vsc-exploration/event_lap_comparisons.csv')
        self.assertEqual(len(comparisons), 12)
        self.assertEqual(len(self.pits), 14)
        keys = self.laps.set_index(['Driver', 'LapNumber'])
        for event in self.summary['windows']:
            rows = comparisons.loc[comparisons.Event.eq(event['event'])]
            self.assertEqual(rows.BeforeLap.nunique(), 1)
            self.assertEqual(rows.AfterLap.nunique(), 1)
            for r in rows.itertuples():
                before, after = keys.loc[(r.Driver, r.BeforeLap)], keys.loc[(r.Driver, r.AfterLap)]
                self.assertLessEqual(before.TimeSeconds, event['start_seconds'])
                self.assertGreaterEqual(after.LapStartTimeSeconds, event['clear_seconds'])
                self.assertEqual(int(before.Position), r.BeforePosition)
                self.assertEqual(int(after.Position), r.AfterPosition)


@unittest.skipUnless(all((ROOT/'data/raw/austria-2026'/name).exists()
                         for name in ['laps.csv', 'track_status.csv', 'race_control_messages.csv']),
                     'Original raw snapshot needed for offline reproduction')
class SnapshotReproductionTests(unittest.TestCase):
    def test_committed_summary_reproduces_from_original_events(self):
        _, _, summary, _, _ = module.build_report()
        expected = json.loads((ROOT/'docs/pit-vsc-exploration/summary.json').read_text())
        self.assertEqual(summary, expected)


if __name__ == '__main__':
    unittest.main()
