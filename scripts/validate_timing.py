"""Reproduce issue #4 checks from the retained snapshot, without network access."""
from pathlib import Path
import hashlib
import itertools
import json

import numpy as np
import pandas as pd

from prepare_race import ROOT, TEAMS, lap_boundary_intervals


def main():
    raw = ROOT/'data/raw/austria-2026'
    out = ROOT/'docs/timing-validation'
    official = json.loads((out/'official_finish_reference.json').read_text())
    summary = json.loads((ROOT/'data/processed/austria-2026/audit_summary.json').read_text())
    digest = hashlib.sha256((raw/'laps.csv').read_bytes()).hexdigest()
    if digest != summary['raw_laps_sha256']:
        raise ValueError('Raw snapshot differs from the committed audit')
    field = pd.read_csv(raw/'laps.csv',dtype={'DriverNumber':str,'TrackStatus':str})
    field['Time'] = pd.to_timedelta(field.Time)
    field['LapTime'] = pd.to_timedelta(field.LapTime)
    selected = field.loc[field.Team.isin(TEAMS)].sort_values(['Driver','LapNumber']).copy()
    selected['Seconds'] = selected.Time.dt.total_seconds()
    selected['Duration'] = selected.LapTime.dt.total_seconds()
    selected['CumulativeLapSeconds'] = selected.groupby('Driver').Duration.cumsum()
    selected['OriginSeconds'] = selected.Seconds-selected.CumulativeLapSeconds
    intervals = lap_boundary_intervals(field,selected)
    baseline = selected.Seconds-selected.LapNumber.map(field.groupby('LapNumber').Time.min().dt.total_seconds())
    delta = float((intervals-baseline).abs().max())
    if delta > .003: raise ValueError('Excluding driver 77 changes the reference')
    # Different arithmetic path: sum durations, then compare every selected pair.
    pairs = []
    for a,b in itertools.combinations(sorted(selected.Driver.unique()),2):
        left = selected[selected.Driver.eq(a)].set_index('LapNumber')
        right = selected[selected.Driver.eq(b)].set_index('LapNumber')
        if not left.index.equals(right.index): raise ValueError('Selected drivers have unequal lap coverage')
        error = (left.Seconds-right.Seconds)-(left.CumulativeLapSeconds-right.CumulativeLapSeconds)
        pairs.append({'drivers':[a,b],'laps':len(error),'maximum_error_seconds':float(error.abs().max())})
    if any(p['maximum_error_seconds']>.003 for p in pairs):
        raise ValueError('Timestamp and cumulative-duration intervals disagree')
    last = selected.groupby('Driver').tail(1).set_index('Driver')
    winner = official['winner']
    finish = []
    for driver,expected in official['selected_drivers'].items():
        row = last.loc[driver]
        actual = float(row.Seconds-last.loc[winner,'Seconds'])
        error = actual-expected['gap_seconds']
        if abs(error)>.003 or row.Position!=expected['position'] or row.LapNumber!=expected['laps']:
            raise ValueError(f'Official finishing comparison failed for {driver}')
        finish.append({'driver':driver,'position':int(row.Position),'lap':int(row.LapNumber),
                       'gap_seconds':round(actual,6),'official_gap_seconds':expected['gap_seconds'],
                       'error_seconds':round(error,9)})
    winner_time = float(selected.loc[selected.Driver.eq(winner),'Duration'].sum())
    if abs(winner_time-official['winner_race_seconds'])>.003:
        raise ValueError('Winner cumulative duration disagrees with published race time')
    status_file = raw/'session_status.csv'
    status_evidence = {'available':False}
    if status_file.exists():
        status = pd.read_csv(status_file)
        finished = pd.to_timedelta(status.loc[status.Status.eq('Finished'),'Time']).dt.total_seconds()
        started = pd.to_timedelta(status.loc[status.Status.eq('Started'),'Time']).dt.total_seconds()
        status_evidence = {'available':True,'finished_seconds':float(finished.iloc[0]),
            'winner_completion_seconds':float(last.loc[winner,'Seconds']),
            'finish_message_delay_seconds':round(float(finished.iloc[0]-last.loc[winner,'Seconds']),6),
            'started_seconds':float(started.iloc[0]),
            'cumulative_duration_origin_seconds':round(float(selected.OriginSeconds.median()),6),
            'start_origin_difference_seconds':round(float(selected.OriginSeconds.median()-started.iloc[0]),6)}
    if not np.isfinite(intervals).all(): raise ValueError('Non-finite gaps')
    report = {'raw_laps_sha256':digest,'selected_laps_checked':len(selected),
        'excluded_reference_driver':'77','reference_change_seconds':round(delta,9),
        'reference_drivers':field.loc[field.groupby('LapNumber').Time.idxmin()].Driver.value_counts().to_dict(),
        'pairwise_checks':pairs,'official_finish_checks':finish,
        'winner_cumulative_seconds':round(winner_time,6),'session_status_evidence':status_evidence,
        'scope':'Supports same-lap completion intervals, not instantaneous gaps or causal strategy effects.',
        'limitation':'Cumulative checks share the retained timing source; official comparisons independently cover the finish only.'}
    (out/'validation_summary.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))


if __name__=='__main__':
    main()
