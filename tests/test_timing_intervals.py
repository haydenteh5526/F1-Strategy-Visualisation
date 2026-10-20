"""Failure cases for the lap-boundary reference calculation, without downloads."""
import importlib.util
from pathlib import Path
import unittest

import pandas as pd

spec = importlib.util.spec_from_file_location('prepare_race', Path(__file__).resolve().parents[1]/'scripts/prepare_race.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class TimingIntervalTests(unittest.TestCase):
    def setUp(self):
        self.field = pd.DataFrame({
            'DriverNumber':['63','3','63','3','77'],
            'LapNumber':[1,1,2,2,1], 'Position':[1,2,1,2,22],
            'Time':pd.to_timedelta([100,101,200,202,80],unit='s')})
        self.selected = self.field.iloc[:4].copy()

    def test_unaligned_retiree_cannot_set_reference(self):
        gaps = module.lap_boundary_intervals(self.field,self.selected)
        self.assertEqual(gaps.to_list(),[0,1,0,2])
        with self.assertRaisesRegex(ValueError,'position'):
            module.lap_boundary_intervals(self.field,self.selected,excluded_drivers=())

    def test_missing_completion_is_rejected(self):
        self.field.loc[1,'Time'] = pd.NaT
        with self.assertRaisesRegex(ValueError,'completion'):
            module.lap_boundary_intervals(self.field,self.selected)

    def test_missing_selected_reference_is_rejected(self):
        with self.assertRaisesRegex(ValueError,'Missing reference'):
            module.lap_boundary_intervals(self.field[self.field.LapNumber.eq(1)],self.selected)

    def test_duplicate_reference_keys_are_rejected(self):
        field = pd.concat([self.field,self.field.iloc[[0]]],ignore_index=True)
        with self.assertRaisesRegex(ValueError,'Duplicate'):
            module.lap_boundary_intervals(field,self.selected)

    def test_selected_time_before_reference_is_rejected(self):
        self.selected.loc[1,'Time'] = pd.Timedelta(seconds=99)
        with self.assertRaisesRegex(ValueError,'precedes'):
            module.lap_boundary_intervals(self.field,self.selected)

    def test_reference_missing_position_is_rejected(self):
        self.field.loc[0,'Position'] = float('nan')
        with self.assertRaisesRegex(ValueError,'position'):
            module.lap_boundary_intervals(self.field,self.selected)


if __name__ == '__main__':
    unittest.main()
