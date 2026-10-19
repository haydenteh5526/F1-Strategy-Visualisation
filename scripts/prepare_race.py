"""Download, audit and prepare the Austria 2026 race without deleting source laps."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import fastf1
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
TEAMS = ['Red Bull Racing', 'Mercedes', 'Ferrari']
TIME_FIELDS = ['Time', 'LapTime', 'LapStartTime', 'PitInTime', 'PitOutTime',
               'Sector1Time', 'Sector2Time', 'Sector3Time']
CORE = ['LapTime', 'Compound', 'TyreLife', 'Position', 'Time', 'Stint']


def prepare(laps: pd.DataFrame) -> pd.DataFrame:
    """Retain all selected laps; add explicit eligibility flags and units."""
    x = laps.loc[laps.Team.isin(TEAMS)].copy().sort_values(['Driver', 'LapNumber'])
    if x.duplicated(['Driver', 'LapNumber']).any():
        raise ValueError('Duplicate driver-lap records require investigation, not silent deletion')
    if x.Driver.nunique() != 6 or not x.groupby('Team').Driver.nunique().eq(2).all():
        raise ValueError('Expected both drivers from each of the three selected teams')
    x['TrackStatus'] = x.TrackStatus.fillna('').astype(str)
    for field in TIME_FIELDS:
        x[field + 'Seconds'] = x[field].dt.total_seconds()
    x['IsPitInLap'] = x.PitInTime.notna()
    x['IsPitOutLap'] = x.PitOutTime.notna()
    x['IsFirstLap'] = x.LapNumber.eq(1)
    x['IsGreenOnly'] = x.TrackStatus.eq('1')
    # TrackStatus strings contain all status codes encountered during a lap.
    x['HasVSC'] = x.TrackStatus.str.contains('[67]', regex=True)
    x['HasSafetyCar'] = x.TrackStatus.str.contains('4', regex=False)
    x['HasYellow'] = x.TrackStatus.str.contains('2', regex=False)
    accurate = x.IsAccurate.eq(True)
    deleted = x.Deleted.eq(True)
    generated = x.FastF1Generated.eq(True)
    x['EligibleForPace'] = (accurate & x.IsGreenOnly & ~x.IsPitInLap & ~x.IsPitOutLap
                           & ~x.IsFirstLap & ~deleted & ~generated & x.LapTimeSeconds.gt(0))
    reasons = []
    for _, row in x.iterrows():
        labels = []
        if row.IsFirstLap: labels.append('first_lap')
        if row.IsPitInLap: labels.append('pit_in')
        if row.IsPitOutLap: labels.append('pit_out')
        if not row.IsGreenOnly: labels.append('track_status_not_green_only')
        if not bool(row.IsAccurate): labels.append('fastf1_accuracy_flag')
        if row.Deleted is True or row.Deleted == True: labels.append('deleted_lap')
        if row.FastF1Generated == True: labels.append('generated_lap')
        if pd.isna(row.LapTimeSeconds) or row.LapTimeSeconds <= 0: labels.append('missing_or_nonpositive_time')
        reasons.append('|'.join(labels))
    x['PaceExclusionReasons'] = reasons
    return x


def pit_visits(x: pd.DataFrame) -> pd.DataFrame:
    """Pair each recorded entry with the next exit for the same driver."""
    visits = []
    for driver, group in x.groupby('Driver'):
        pending = None
        events = []
        for _, row in group.iterrows():
            for kind, field in [('entry', 'PitInTimeSeconds'), ('exit', 'PitOutTimeSeconds')]:
                if pd.notna(row[field]): events.append((float(row[field]), kind, row))
        for time, kind, row in sorted(events, key=lambda item: item[0]):
            if kind == 'entry':
                if pending is not None: raise ValueError(f'Unmatched consecutive entries for {driver}')
                pending = (time, row)
            elif pending is not None:
                start, entry = pending
                if time <= start: raise ValueError('Nonpositive pit-lane elapsed time')
                visits.append({'Driver': driver, 'Team': row.Team, 'EntryLap': int(entry.LapNumber),
                    'ExitLap': int(row.LapNumber), 'EntrySeconds': start, 'ExitSeconds': time,
                    'PitLaneElapsedSeconds': time-start, 'EntryTrackStatus': entry.TrackStatus,
                    'ExitTrackStatus': row.TrackStatus})
                pending = None
        if pending is not None: raise ValueError(f'Unmatched final pit entry for {driver}')
    return pd.DataFrame(visits)


def validate(x: pd.DataFrame, field: pd.DataFrame, visits: pd.DataFrame) -> None:
    """Check identifiers, timing calculations and source/derived consistency."""
    if len(x) != len(field.loc[field.Team.isin(TEAMS)]): raise ValueError('Source rows lost')
    if x.LapTimeSeconds.le(0).any(): raise ValueError('Nonpositive lap duration')
    if not x.groupby('Driver').LapNumber.apply(lambda s: s.is_monotonic_increasing).all():
        raise ValueError('Lap order is inconsistent')
    eligible = x.loc[x.EligibleForPace]
    sector_sum = eligible[[f'Sector{i}TimeSeconds' for i in [1,2,3]]].sum(axis=1, min_count=3)
    if not np.allclose(sector_sum, eligible.LapTimeSeconds, atol=.003, rtol=0):
        raise ValueError('Eligible sector totals disagree with lap durations')
    if len(visits) != int(x.IsPitInLap.sum()) or len(visits) != int(x.IsPitOutLap.sum()):
        raise ValueError('Pit entry/exit pairing coverage mismatch')


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--from-snapshot', action='store_true', help='Reprocess the local raw download without network access')
    parser.add_argument('--access-date', default=None, help='Recorded retrieval date YYYY-MM-DD, when known')
    args = parser.parse_args()
    raw = ROOT/'data/raw/austria-2026'
    out = ROOT/'data/processed/austria-2026'
    raw.mkdir(parents=True, exist_ok=True); out.mkdir(parents=True, exist_ok=True)
    if args.from_snapshot:
        field = pd.read_csv(raw/'laps.csv', dtype={'DriverNumber':str,'TrackStatus':str})
        for name in TIME_FIELDS: field[name] = pd.to_timedelta(field[name], errors='raise')
        provenance = json.loads((raw/'provenance.json').read_text())
    else:
        cache = ROOT/'.fastf1-cache'; cache.mkdir(exist_ok=True)
        fastf1.Cache.enable_cache(str(cache))
        session = fastf1.get_session(2026, 'Austria', 'R')
        session.load(telemetry=False, weather=True, messages=True)
        field = pd.DataFrame(session.laps)
        field.to_csv(raw/'laps.csv', index=False)
        session.track_status.to_csv(raw/'track_status.csv', index=False)
        session.race_control_messages.to_csv(raw/'race_control_messages.csv', index=False)
        session.weather_data.to_csv(raw/'weather.csv', index=False)
        session.results.to_csv(raw/'results.csv', index=False)
        provenance = {'event':'Austrian Grand Prix', 'year':2026,'session':'Race',
            'race_date':'2026-06-28','access_date':args.access_date or pd.Timestamp.now(tz='UTC').date().isoformat(),
            'fastf1_version':fastf1.__version__,'pandas_version':pd.__version__,
            'source':'FastF1 session data accessed via get_session(2026, Austria, R)',
            'timing_url':'https://livetiming.formula1.com/static/',
            'reference':'https://docs.fastf1.dev/core.html',
            'official_result':'https://www.formula1.com/en/results/2026/races/1288/austria/race-result',
            'telemetry_downloaded':False}
        (raw/'provenance.json').write_text(json.dumps(provenance,indent=2)+'\n')
    x = prepare(field)
    visits = pit_visits(x)
    validate(x, field, visits)
    # Same completed lap for every driver, compared with the full-field earliest completion.
    # This is a lap-boundary interval, not an instantaneous/live race gap.
    field_times = field.assign(TimeSeconds=field.Time.dt.total_seconds())
    earliest = field_times.groupby('LapNumber').TimeSeconds.min()
    x['GapToEarliestLapCompletionSeconds'] = x.TimeSeconds-x.LapNumber.map(earliest)
    if x.GapToEarliestLapCompletionSeconds.lt(-.003).any(): raise ValueError('Negative reference gap')
    columns = ['Driver','DriverNumber','Team','LapNumber','Stint','Compound','TyreLife','FreshTyre',
               'Position','TrackStatus','IsAccurate','FastF1Generated','Deleted']
    columns += [name+'Seconds' for name in TIME_FIELDS]
    columns += ['IsPitInLap','IsPitOutLap','IsFirstLap','IsGreenOnly','HasVSC','HasSafetyCar',
                'HasYellow','EligibleForPace','PaceExclusionReasons','GapToEarliestLapCompletionSeconds']
    x[columns].to_csv(out/'selected_laps.csv',index=False,float_format='%.6f')
    x.loc[x.EligibleForPace,columns].to_csv(out/'pace_laps.csv',index=False,float_format='%.6f')
    x.loc[~x.IsAccurate.eq(True),columns].to_csv(out/'flagged_laps.csv',index=False,float_format='%.6f')
    visits.to_csv(out/'pit_visits.csv',index=False,float_format='%.6f')
    stints = x.groupby(['Team','Driver','Stint','Compound'],dropna=False).agg(
        FirstLap=('LapNumber','min'),LastLap=('LapNumber','max'),RecordedLaps=('LapNumber','size'),
        PaceEligibleLaps=('EligibleForPace','sum'),FirstRecordedTyreAge=('TyreLife','first'),
        LastRecordedTyreAge=('TyreLife','last')).reset_index()
    stints.to_csv(out/'stints.csv',index=False)
    flagged = ~x.IsAccurate.eq(True)
    first_only = flagged & x.IsFirstLap & ~x.IsPitInLap & ~x.IsPitOutLap & x.IsGreenOnly
    pit = flagged & (x.IsPitInLap | x.IsPitOutLap)
    interrupted = flagged & ~pit & ~first_only & ~x.IsGreenOnly
    other = flagged & ~pit & ~first_only & ~interrupted
    summary = {'provenance':provenance, 'field_rows':len(field),'selected_rows':len(x),
        'drivers':x.groupby(['Team','Driver']).agg(RecordedLaps=('LapNumber','size'),
          PaceEligibleLaps=('EligibleForPace','sum'),Stints=('Stint','nunique')).reset_index().to_dict('records'),
        'core_missing':x[CORE].isna().sum().astype(int).to_dict(),
        'sector_missing':x[[f'Sector{i}Time' for i in [1,2,3]]].isna().sum().astype(int).to_dict(),
        'duplicate_driver_laps':int(x.duplicated(['Driver','LapNumber']).sum()),
        'accuracy_flagged':int(flagged.sum()),'pace_eligible':int(x.EligibleForPace.sum()),
        'pace_excluded':int((~x.EligibleForPace).sum()),'pit_visits':len(visits),
        'flagged_exclusive_categories':{'pit_laps':int(pit.sum()),'first_laps':int(first_only.sum()),
          'other_status_affected_laps':int(interrupted.sum()),'unexplained':int(other.sum())},
        'green_only_laps':int(x.IsGreenOnly.sum()),'vsc_affected_laps':int(x.HasVSC.sum()),
        'yellow_affected_laps':int(x.HasYellow.sum()),'safety_car_affected_laps':int(x.HasSafetyCar.sum()),
        'deleted_laps':int(x.Deleted.eq(True).sum()),'generated_laps':int(x.FastF1Generated.eq(True).sum()),
        'track_status_counts':x.TrackStatus.value_counts().astype(int).to_dict(),
        'compound_counts':x.Compound.value_counts().astype(int).to_dict(),
        'lap_time_range_seconds':[float(x.LapTimeSeconds.min()),float(x.LapTimeSeconds.max())],
        'pit_lane_elapsed_range_seconds':[float(visits.PitLaneElapsedSeconds.min()),float(visits.PitLaneElapsedSeconds.max())],
        'checks_passed':['source rows retained','unique driver-lap keys','positive lap durations',
          'sector totals within 3ms for eligible laps','all pit entries/exits paired','nonnegative lap-boundary gaps'],
        'raw_laps_sha256':hashlib.sha256((raw/'laps.csv').read_bytes()).hexdigest()}
    (out/'audit_summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps(summary,indent=2))


if __name__ == '__main__':
    main()
