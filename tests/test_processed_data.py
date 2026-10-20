"""Consistency checks on the committed prepared files; no raw download or network access needed."""
import json
from pathlib import Path
import unittest

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'data/processed/austria-2026'
KEY = ['Driver', 'LapNumber']
STATUS = {'TrackStatus': str, 'EntryTrackStatus': str, 'ExitTrackStatus': str}


def read(name: str) -> pd.DataFrame:
    return pd.read_csv(OUT/name, dtype=STATUS)


class PreparedDataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.laps, cls.pace, cls.flagged = [read(name).fillna({'PaceExclusionReasons': ''})
            for name in ['selected_laps.csv', 'pace_laps.csv', 'flagged_laps.csv']]
        cls.visits = read('pit_visits.csv')
        cls.stints = read('stints.csv')
        cls.summary = json.loads((OUT/'audit_summary.json').read_text())

    def test_counts_match_audit_summary(self):
        s = self.summary
        self.assertEqual(len(self.laps), s['selected_rows'])
        self.assertEqual(len(self.pace), s['pace_eligible'])
        self.assertEqual(len(self.flagged), s['accuracy_flagged'])
        self.assertEqual(len(self.visits), s['pit_visits'])
        self.assertEqual(self.laps.Compound.value_counts().to_dict(), s['compound_counts'])
        self.assertEqual(self.laps.TrackStatus.value_counts().to_dict(), s['track_status_counts'])
        drivers = self.laps.groupby(['Team', 'Driver']).agg(RecordedLaps=('LapNumber', 'size'),
            PaceEligibleLaps=('EligibleForPace', 'sum'), Stints=('Stint', 'nunique')).reset_index()
        self.assertEqual(drivers.to_dict('records'), s['drivers'])

    def test_audit_figures_match_lap_records(self):
        x, s = self.laps, self.summary
        self.assertEqual(int(x.IsGreenOnly.sum()), s['green_only_laps'])
        self.assertEqual(int(x.HasVSC.sum()), s['vsc_affected_laps'])
        self.assertEqual(int(x.HasYellow.sum()), s['yellow_affected_laps'])
        self.assertEqual(int(x.HasSafetyCar.sum()), s['safety_car_affected_laps'])
        self.assertEqual(int(x.Deleted.sum()), s['deleted_laps'])
        self.assertEqual(int(x.FastF1Generated.sum()), s['generated_laps'])
        for name, count in s['sector_missing'].items():
            self.assertEqual(int(x[name+'Seconds'].isna().sum()), count, name)
        core = {'LapTime': 'LapTimeSeconds', 'Time': 'TimeSeconds'}
        for name, count in s['core_missing'].items():
            self.assertEqual(int(x[core.get(name, name)].isna().sum()), count, name)
        visits = self.visits.PitLaneElapsedSeconds
        self.assertTrue(np.allclose([visits.min(), visits.max()], s['pit_lane_elapsed_range_seconds'], atol=1e-6))
        # Mutually exclusive categories for the accuracy-flagged laps; pit activity takes priority.
        flagged = ~x.IsAccurate
        pit = flagged & (x.IsPitInLap | x.IsPitOutLap)
        first = flagged & x.IsFirstLap & ~pit & x.IsGreenOnly
        status = flagged & ~pit & ~first & ~x.IsGreenOnly
        self.assertEqual({'pit_laps': int(pit.sum()), 'first_laps': int(first.sum()),
                          'other_status_affected_laps': int(status.sum()),
                          'unexplained': int((flagged & ~pit & ~first & ~status).sum())},
                         s['flagged_exclusive_categories'])

    def test_every_driver_has_one_record_per_lap(self):
        self.assertFalse(self.laps.duplicated(KEY).any())
        for driver, laps in self.laps.groupby('Driver'):
            self.assertEqual(sorted(laps.LapNumber), list(range(1, len(laps)+1)), driver)

    def test_subset_files_match_selected_rows(self):
        laps = self.laps
        for name, subset, mask in [('pace_laps', self.pace, laps.EligibleForPace),
                                   ('flagged_laps', self.flagged, ~laps.IsAccurate)]:
            pd.testing.assert_frame_equal(subset.reset_index(drop=True),
                                          laps[mask].reset_index(drop=True), obj=name)

    def test_status_flags_follow_track_status_codes(self):
        status = self.laps.TrackStatus
        self.assertTrue(self.laps.IsGreenOnly.eq(status.eq('1')).all())
        self.assertTrue(self.laps.HasVSC.eq(status.str.contains('[67]', regex=True)).all())
        self.assertTrue(self.laps.HasYellow.eq(status.str.contains('2', regex=False)).all())
        self.assertTrue(self.laps.HasSafetyCar.eq(status.str.contains('4', regex=False)).all())

    def test_pace_rule_is_reproducible_and_explained(self):
        x = self.laps
        rule = (x.IsAccurate & x.IsGreenOnly & ~x.IsPitInLap & ~x.IsPitOutLap & ~x.IsFirstLap
                & ~x.Deleted & ~x.FastF1Generated & x.LapTimeSeconds.gt(0))
        self.assertTrue(x.EligibleForPace.eq(rule).all())
        self.assertTrue(x.loc[x.EligibleForPace, 'PaceExclusionReasons'].eq('').all())
        self.assertTrue(x.loc[~x.EligibleForPace, 'PaceExclusionReasons'].ne('').all())

    def test_eligible_sector_totals_match_lap_time(self):
        eligible = self.pace
        sectors = eligible[[f'Sector{i}TimeSeconds' for i in [1, 2, 3]]].sum(axis=1, min_count=3)
        self.assertTrue(np.allclose(sectors, eligible.LapTimeSeconds, atol=.003, rtol=0))

    def test_lap_times_and_gaps_are_in_recorded_ranges(self):
        low, high = self.summary['lap_time_range_seconds']
        self.assertAlmostEqual(self.laps.LapTimeSeconds.min(), low, places=6)
        self.assertAlmostEqual(self.laps.LapTimeSeconds.max(), high, places=6)
        self.assertFalse(self.laps.GapToEarliestLapCompletionSeconds.lt(-.003).any())

    def test_lap_boundary_intervals_agree_with_positions(self):
        # The race leader completes each lap first, so a selected P1 driver must set the reference.
        leaders = self.laps[self.laps.Position.eq(1)]
        self.assertTrue(leaders.GapToEarliestLapCompletionSeconds.abs().le(.003).all())
        for lap, laps in self.laps.groupby('LapNumber'):
            order = laps.sort_values('TimeSeconds').Position
            self.assertTrue(order.is_monotonic_increasing and order.is_unique, lap)

    def test_stints_cover_each_race_without_gaps(self):
        for driver, stints in self.stints.sort_values(['Driver', 'Stint']).groupby('Driver'):
            self.assertEqual(stints.FirstLap.iloc[0], 1, driver)
            self.assertEqual(stints.LastLap.iloc[-1], self.laps[self.laps.Driver.eq(driver)].LapNumber.max())
            self.assertTrue((stints.FirstLap.values[1:] == stints.LastLap.values[:-1]+1).all(), driver)
            self.assertTrue((stints.RecordedLaps == stints.LastLap-stints.FirstLap+1).all(), driver)

    def test_stint_summaries_match_lap_records(self):
        laps = self.laps.sort_values(KEY)
        derived = laps.groupby(['Team', 'Driver', 'Stint', 'Compound']).agg(
            RecordedLaps=('LapNumber', 'size'), PaceEligibleLaps=('EligibleForPace', 'sum'),
            FirstRecordedTyreAge=('TyreLife', 'first'), LastRecordedTyreAge=('TyreLife', 'last')).reset_index()
        merged = self.stints.merge(derived, on=['Team', 'Driver', 'Stint', 'Compound'], suffixes=('', 'Laps'))
        self.assertEqual(len(merged), len(self.stints))
        for column in ['RecordedLaps', 'PaceEligibleLaps', 'FirstRecordedTyreAge', 'LastRecordedTyreAge']:
            self.assertTrue(merged[column].eq(merged[column+'Laps']).all(), column)

    def test_tyre_age_advances_one_lap_at_a_time_within_stints(self):
        steps = self.laps.sort_values(KEY).groupby(['Driver', 'Stint']).TyreLife.diff().dropna()
        self.assertTrue(steps.eq(1).all())

    def test_pit_visits_separate_consecutive_stints(self):
        laps = self.laps.set_index(KEY)
        for _, visit in self.visits.iterrows():
            self.assertTrue(laps.loc[(visit.Driver, visit.EntryLap), 'IsPitInLap'])
            self.assertTrue(laps.loc[(visit.Driver, visit.ExitLap), 'IsPitOutLap'])
            self.assertEqual(visit.ExitLap, visit.EntryLap+1)
            self.assertAlmostEqual(visit.PitLaneElapsedSeconds, visit.ExitSeconds-visit.EntrySeconds, places=6)
        for driver, stints in self.stints.groupby('Driver'):
            exits = sorted(self.visits.loc[self.visits.Driver.eq(driver), 'ExitLap'])
            self.assertEqual(exits, sorted(stints.FirstLap)[1:], driver)
        self.assertEqual(len(self.visits), int(self.laps.IsPitInLap.sum()))
        self.assertEqual(len(self.visits), int(self.laps.IsPitOutLap.sum()))


if __name__ == '__main__':
    unittest.main()
