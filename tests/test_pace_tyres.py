"""Guard the exploratory comparisons against mixing excluded laps or tyre sets."""
import importlib.util
from pathlib import Path
import unittest

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('explore_pace_tyres', ROOT/'scripts/explore_pace_tyres.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class PaceTyreTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.laps = pd.read_csv(module.DATA/'selected_laps.csv')
        cls.tables = module.analyse(cls.laps)

    def test_all_laps_accounted_for_without_using_excluded_times(self):
        summary = self.tables['pace_summary']
        self.assertEqual(summary.EligibleLaps.sum(), 361)
        self.assertEqual(summary.RecordedLaps.sum(), 426)
        changed = self.laps.copy()
        changed.loc[~changed.EligibleForPace, 'LapTimeSeconds'] = 10000
        pd.testing.assert_frame_equal(summary, module.analyse(changed)['pace_summary'])

    def test_pairs_use_same_lap_compound_and_two_eligible_drivers(self):
        eligible = self.laps.loc[self.laps.EligibleForPace].set_index(['Driver', 'LapNumber'])
        matched = self.tables['matched_laps']
        self.assertFalse(matched.duplicated(['Team', 'LapNumber']).any())
        for r in matched.itertuples():
            a, b = eligible.loc[(r.DriverA, r.LapNumber)], eligible.loc[(r.DriverB, r.LapNumber)]
            self.assertEqual(a.Team, b.Team)
            self.assertEqual(a.Compound, b.Compound)
            self.assertAlmostEqual(r.DifferenceSecondsAminusB, a.LapTimeSeconds-b.LapTimeSeconds)
        # Independently enumerate the expected pairs so omissions are caught too.
        expected = 0
        for (_, _), rows in self.laps.groupby(['Team', 'LapNumber']):
            expected += bool(rows.EligibleForPace.all() and rows.Compound.nunique() == 1)
        self.assertEqual(len(matched), expected)
        self.assertEqual(self.tables['matched_windows'].MatchedLaps.sum(), expected)

    def test_same_compound_sets_and_used_tyres_remain_separate(self):
        stints = self.tables['stint_summary']
        self.assertEqual(len(stints), 20)
        self.assertEqual(stints.RecordedLaps.sum(), 426)
        self.assertEqual(stints.EligibleLaps.sum(), 361)
        had = stints.loc[stints.Driver.eq('HAD')]
        self.assertEqual(had.Compound.tolist().count('MEDIUM'), 2)
        ham_soft = stints.loc[stints.Driver.eq('HAM') & stints.Compound.eq('SOFT')].iloc[0]
        self.assertFalse(ham_soft.FreshTyreAtStart)
        self.assertEqual(ham_soft.FirstRecordedTyreAge, 3)

    def test_slope_uses_only_one_eligible_stint_and_requires_five_laps(self):
        changed = self.laps.copy()
        target = changed.Driver.eq('HAM') & changed.Stint.eq(1)
        changed.loc[target & changed.EligibleForPace, 'LapTimeSeconds'] = 80 + 0.25*changed.loc[target & changed.EligibleForPace, 'TyreLife']
        summary = module.analyse(changed)['stint_summary']
        self.assertAlmostEqual(summary.loc[summary.Driver.eq('HAM') & summary.Stint.eq(1), 'DescriptiveSecondsPerTyreLap'].iloc[0], .25)
        keep = changed.loc[target & changed.EligibleForPace].index[:4]
        changed.loc[target & ~changed.index.isin(keep), 'EligibleForPace'] = False
        summary = module.analyse(changed)['stint_summary']
        self.assertTrue(np.isnan(summary.loc[summary.Driver.eq('HAM') & summary.Stint.eq(1), 'DescriptiveSecondsPerTyreLap'].iloc[0]))

    def test_duplicate_laps_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            module.analyse(pd.concat([self.laps, self.laps.iloc[[0]]]))


if __name__ == '__main__':
    unittest.main()
