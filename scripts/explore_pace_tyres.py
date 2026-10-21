"""Offline descriptive exploration for issues #5 and #6; no causal strategy model."""
from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT/'data/processed/austria-2026'
OUTPUT = ROOT/'docs/pace-tyre-exploration'
DRIVERS = ['HAD', 'VER', 'ANT', 'RUS', 'HAM', 'LEC']
COLORS = ['#2a78d6', '#2a78d6', '#17865f', '#17865f', '#c44c24', '#c44c24']
TYRES = {'SOFT': '#cc3838', 'MEDIUM': '#ad7700', 'HARD': '#666666'}


def analyse(laps: pd.DataFrame) -> dict[str, pd.DataFrame]:
    if laps.duplicated(['Driver', 'LapNumber']).any():
        raise ValueError('Duplicate driver/lap records')
    if set(laps.Driver) != set(DRIVERS):
        raise ValueError('Expected the six Austria drivers')
    if not pd.api.types.is_bool_dtype(laps.EligibleForPace):
        raise ValueError('Eligibility must be boolean')
    pace = laps.loc[laps.EligibleForPace].copy()
    if not np.isfinite(pace[['LapTimeSeconds', 'TyreLife', 'LapNumber']]).all().all():
        raise ValueError('Non-finite analysis values')
    summary = pace.groupby(['Team', 'Driver']).agg(
        EligibleLaps=('LapNumber', 'size'), MedianSeconds=('LapTimeSeconds', 'median'),
        Q1Seconds=('LapTimeSeconds', lambda s: s.quantile(.25)),
        Q3Seconds=('LapTimeSeconds', lambda s: s.quantile(.75))).reset_index()
    # Retain drivers with no eligible observations and report their zero sample size.
    summary = laps[['Team', 'Driver']].drop_duplicates().sort_values(['Team', 'Driver']).merge(
        summary, on=['Team', 'Driver'], how='left', validate='one_to_one')
    summary['EligibleLaps'] = summary.EligibleLaps.fillna(0).astype(int)
    summary['IQRSeconds'] = summary.Q3Seconds-summary.Q1Seconds
    summary['RecordedLaps'] = summary.Driver.map(laps.groupby('Driver').size())
    summary['ExcludedLaps'] = summary.RecordedLaps-summary.EligibleLaps

    # Exact same lap, same compound, both eligible. Windows fixed before inspecting results.
    # This controls race lap and compound, but not tyre age, fuel, traffic or car differences.
    matched = []
    for team, team_laps in laps.groupby('Team'):
        a, b = sorted(team_laps.Driver.unique())
        rows = pace.loc[pace.Team.eq(team)]
        pair = rows.loc[rows.Driver.eq(a)].merge(rows.loc[rows.Driver.eq(b)],
            on=['LapNumber', 'Compound'], suffixes=('A', 'B'), validate='one_to_one')
        for r in pair.itertuples():
            matched.append({'Team': team, 'DriverA': a, 'DriverB': b,
                'LapNumber': int(r.LapNumber), 'Compound': r.Compound,
                'Window': f'{1+20*((int(r.LapNumber)-1)//20)}–{min(71,20*(1+(int(r.LapNumber)-1)//20))}',
                'DifferenceSecondsAminusB': r.LapTimeSecondsA-r.LapTimeSecondsB,
                'TyreAgeA': r.TyreLifeA, 'TyreAgeB': r.TyreLifeB,
                'StintA': r.StintA, 'StintB': r.StintB})
    matched = pd.DataFrame(matched, columns=[
        'Team', 'DriverA', 'DriverB', 'LapNumber', 'Compound', 'Window',
        'DifferenceSecondsAminusB', 'TyreAgeA', 'TyreAgeB', 'StintA', 'StintB'])
    windows = matched.groupby(['Team', 'DriverA', 'DriverB', 'Window', 'Compound'], sort=False).agg(
        MatchedLaps=('LapNumber', 'size'),
        MedianDifferenceSecondsAminusB=('DifferenceSecondsAminusB', 'median'),
        MinimumTyreAgeDifference=('TyreAgeA', lambda s: (s-matched.loc[s.index, 'TyreAgeB']).min()),
        MaximumTyreAgeDifference=('TyreAgeA', lambda s: (s-matched.loc[s.index, 'TyreAgeB']).max())).reset_index()

    stints = []
    for (team, driver, stint, compound), rows in laps.groupby(['Team', 'Driver', 'Stint', 'Compound']):
        rows = rows.sort_values('LapNumber')
        eligible = rows.loc[rows.EligibleForPace]
        slope = np.nan
        if len(eligible) >= 5 and eligible.TyreLife.nunique() > 1:
            slope = np.polyfit(eligible.TyreLife, eligible.LapTimeSeconds, 1)[0]
        stints.append({'Team': team, 'Driver': driver, 'Stint': int(stint), 'Compound': compound,
            'FirstLap': int(rows.LapNumber.min()), 'LastLap': int(rows.LapNumber.max()),
            'RecordedLaps': len(rows), 'EligibleLaps': len(eligible),
            'FreshTyreAtStart': bool(rows.FreshTyre.iloc[0]),
            'FirstRecordedTyreAge': rows.TyreLife.iloc[0],
            'LastRecordedTyreAge': rows.TyreLife.iloc[-1],
            'DescriptiveSecondsPerTyreLap': slope})
    return {'pace_summary': summary, 'matched_laps': matched, 'matched_windows': windows,
            'stint_summary': pd.DataFrame(stints)}


def figures(laps: pd.DataFrame, tables: dict) -> dict:
    pace = laps.loc[laps.EligibleForPace]
    fig, axes = plt.subplots(3, 1, figsize=(12, 9), sharex=True, sharey=True, layout='constrained')
    for i, (ax, pair) in enumerate(zip(axes, [DRIVERS[:2], DRIVERS[2:4], DRIVERS[4:]])):
        for j, driver in enumerate(pair):
            rows = pace.loc[pace.Driver.eq(driver)]
            ax.scatter(rows.LapNumber, rows.LapTimeSeconds, s=19, marker=['o', '^'][j],
                       color=COLORS[2*i], label=f'{driver} (n={len(rows)})', alpha=.8)
        for lo, hi in [(23.5, 26.5), (51.5, 53.5)]:
            ax.axvspan(lo, hi, color='#777777', alpha=.13)
        ax.set_ylabel('Lap time (s)'); ax.legend(ncol=2); ax.grid(alpha=.2)
    axes[-1].set_xlabel('Race lap · shaded bands = VSC-affected laps (excluded)')
    fig.suptitle('Normal-racing pace by race lap · points only; excluded laps are not bridged')

    distribution, ax = plt.subplots(figsize=(11, 5), layout='constrained')
    groups = [pace.loc[pace.Driver.eq(d), 'LapTimeSeconds'] for d in DRIVERS]
    ax.boxplot(groups, tick_labels=[f'{d}\nn={len(g)}' for d, g in zip(DRIVERS, groups)],
               showfliers=True, whis=(0, 100))
    ax.set_ylabel('Lap time (s)'); ax.grid(axis='y', alpha=.2)
    ax.set_title('Whole-race eligible distributions · box = middle 50%; whiskers = min/max\nDescriptive context: compounds, tyre ages and race phases differ')

    tyres, axes = plt.subplots(3, 2, figsize=(13, 10), sharex=True, sharey=True, layout='constrained')
    for ax, driver in zip(axes.flat, DRIVERS):
        for row in tables['stint_summary'].loc[lambda t: t.Driver.eq(driver)].itertuples():
            points = pace.loc[pace.Driver.eq(driver) & pace.Stint.eq(row.Stint)]
            label = f'{row.Compound[0]} stint {row.Stint}: {row.EligibleLaps}/{row.RecordedLaps}'
            if not row.FreshTyreAtStart:
                label += ' (used)'
            ax.scatter(points.TyreLife, points.LapTimeSeconds, color=TYRES[row.Compound],
                       marker=['o', '^', 's', 'D'][int(row.Stint-1) % 4], s=20, label=label)
        ax.set_title(driver); ax.grid(alpha=.2); ax.legend(fontsize=8)
        ax.set_xlabel('Recorded tyre age (laps)'); ax.set_ylabel('Lap time (s)')
    tyres.suptitle('Tyre age within individual stints · legend counts = eligible / recorded laps\nPoints only: tyre age and race lap increase together; these are not wear estimates')
    return {'pace_by_lap': fig, 'pace_distribution': distribution, 'tyre_age': tyres}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-dir', type=Path, default=DATA)
    parser.add_argument('--output-dir', type=Path, default=OUTPUT)
    args = parser.parse_args()
    laps = pd.read_csv(args.data_dir/'selected_laps.csv', dtype={'TrackStatus': str})
    tables = analyse(laps)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for name, frame in tables.items():
        frame.to_csv(args.output_dir/f'{name}.csv', index=False, float_format='%.6f')
    for name, fig in figures(laps, tables).items():
        fig.get_layout_engine().set(rect=(0, .035, 1, .965))
        fig.text(.02, .012, 'Source: retained FastF1 3.8.3 snapshot, accessed 2026-10-08 · S/M/H = Soft/Medium/Hard · see README for limits', fontsize=8)
        fig.savefig(args.output_dir/f'{name}.png', dpi=160)
        plt.close(fig)
    print(f'Wrote four tables and three figures to {args.output_dir}')


if __name__ == '__main__':
    main()
