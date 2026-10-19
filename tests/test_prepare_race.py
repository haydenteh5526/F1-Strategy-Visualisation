"""Regression checks against the actual downloaded race snapshot."""
import importlib.util
from pathlib import Path
import unittest
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('prepare_race',ROOT/'scripts/prepare_race.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)

class RacePreparationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        snapshot=ROOT/'data/raw/austria-2026/laps.csv'
        if not snapshot.exists(): raise unittest.SkipTest('Run prepare_race.py to download the raw snapshot first')
        cls.raw=pd.read_csv(snapshot,dtype={'TrackStatus':str,'DriverNumber':str})
        for f in module.TIME_FIELDS:cls.raw[f]=pd.to_timedelta(cls.raw[f])
        cls.prepared=module.prepare(cls.raw)

    def test_duplicate_source_keys_are_rejected(self):
        driver_row=self.raw[self.raw.Team.isin(module.TEAMS)].iloc[[0]]
        with self.assertRaisesRegex(ValueError,'Duplicate'):
            module.prepare(pd.concat([self.raw,driver_row],ignore_index=True))

    def test_sector_timing_corruption_is_rejected(self):
        changed=self.prepared.copy()
        index=changed[changed.EligibleForPace].index[0]
        changed.loc[index,'Sector1TimeSeconds']+=1
        with self.assertRaisesRegex(ValueError,'sector'):
            module.validate(changed,self.raw,module.pit_visits(changed))

    def test_interrupted_laps_never_enter_normal_pace(self):
        eligible=self.prepared[self.prepared.EligibleForPace]
        self.assertGreater(len(eligible),0)
        self.assertTrue(eligible.TrackStatus.eq('1').all())
        self.assertFalse((eligible.IsPitInLap|eligible.IsPitOutLap|eligible.IsFirstLap).any())
        self.assertEqual(len(self.prepared),len(self.raw[self.raw.Team.isin(module.TEAMS)]))

if __name__=='__main__':unittest.main()
