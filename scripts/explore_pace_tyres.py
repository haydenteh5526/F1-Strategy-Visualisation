"""Exploration for issues #5 (pace) and #6 (tyres): summary numbers and figures, without network access."""
from __future__ import annotations

import json
from pathlib import Path
import sys

import altair as alt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'app'))
sys.path.insert(0, str(ROOT/'scripts'))
import charts  # noqa: E402
from export_figures import static  # noqa: E402

DATA = ROOT/'data/processed/austria-2026'
RAW_LAPS = ROOT/'data/raw/austria-2026/laps.csv'
FIGURES = ROOT/'figures/austria-2026/exploration'
SUMMARY = ROOT/'docs/exploration/pace_tyres_summary.json'
# Race windows in which all six drivers were on the same compound; summarise() checks this.
WINDOWS = {'Medium, laps 2–11': (2, 11, 'MEDIUM'), 'Hard, laps 44–59': (44, 59, 'HARD')}
CLOSE_SECONDS = 1.0  # A lap starting this close behind another car is treated as possibly in traffic.
MIN_TREND_LAPS = 8


def gap_to_car_ahead(pace: pd.DataFrame, raw_laps: pd.DataFrame) -> pd.Series:
    """Seconds since any other car last crossed the line when each lap started (a traffic proxy)."""
    crossings = raw_laps.assign(Crossing=pd.to_timedelta(raw_laps.Time).dt.total_seconds()).dropna(subset=['Crossing'])
    times, drivers = crossings.Crossing.to_numpy(), crossings.Driver.to_numpy()

    def gap(row):
        earlier = (times < row.LapStartTimeSeconds-1e-6) & (drivers != row.Driver)
        return row.LapStartTimeSeconds-times[earlier].max() if earlier.any() else np.nan
    return pace.apply(gap, axis=1)


def medians(frame: pd.DataFrame) -> dict:
    times = frame.groupby('Driver').LapTimeSeconds
    return {driver: {'laps': int(n), 'median_seconds': round(float(m), 3)}
            for (driver, n), m in zip(times.size().items(), times.median())}


def same_compound_pairs(pace: pd.DataFrame) -> list[tuple[str, str, pd.DataFrame, pd.DataFrame]]:
    """Drivers who used the same compound in two stints, as (driver, compound, earlier, later)."""
    pairs = []
    for (driver, compound), group in pace.groupby(['Driver', 'Compound']):
        stints = [g for _, g in group.groupby('Stint')]
        if len(stints) == 2:
            pairs.append((driver, compound, *stints))
    return pairs


def summarise(laps: pd.DataFrame, raw_laps: pd.DataFrame | None = None) -> dict:
    pace = laps.loc[laps.EligibleForPace]
    whole = medians(pace)
    for driver, times in pace.groupby('Driver').LapTimeSeconds:
        whole[driver]['middle_half_seconds'] = round(float(times.quantile(.75)-times.quantile(.25)), 3)
    windows = {}
    for name, (first, last, compound) in WINDOWS.items():
        if not laps.loc[laps.LapNumber.between(first, last), 'Compound'].eq(compound).all():
            raise ValueError(f'{name} does not have every driver on {compound}')
        windows[name] = medians(pace.loc[pace.LapNumber.between(first, last)])
    stints = []
    for (driver, stint), group in laps.groupby(['Driver', 'Stint']):
        eligible = group.loc[group.EligibleForPace]
        reasons = group.loc[~group.EligibleForPace, 'PaceExclusionReasons'].str.split('|').explode().value_counts()
        trend = np.polyfit(eligible.TyreLife, eligible.LapTimeSeconds, 1)[0] if len(eligible) >= MIN_TREND_LAPS else None
        stints.append({'driver': driver, 'stint': int(stint), 'compound': group.Compound.iloc[0],
                       'laps': f'{int(group.LapNumber.min())}–{int(group.LapNumber.max())}',
                       'recorded_laps': len(group), 'eligible_laps': len(eligible),
                       'fresh_set': bool(group.FreshTyre.iloc[0]), 'first_tyre_age': int(group.TyreLife.min()),
                       'exclusion_reasons': {k: int(v) for k, v in reasons.items()},
                       'trend_seconds_per_tyre_lap': None if trend is None else round(float(trend), 3)})
    phase = []
    for driver, compound, earlier, later in same_compound_pairs(pace):
        ages = sorted(set(earlier.TyreLife) & set(later.TyreLife))
        a = earlier.loc[earlier.TyreLife.isin(ages), 'LapTimeSeconds'].median()
        b = later.loc[later.TyreLife.isin(ages), 'LapTimeSeconds'].median()
        phase.append({'driver': driver, 'compound': compound, 'stints': [int(earlier.Stint.iloc[0]), int(later.Stint.iloc[0])],
                      'shared_tyre_ages': [int(min(ages)), int(max(ages))], 'shared_age_count': len(ages),
                      'earlier_median_seconds': round(float(a), 3), 'later_median_seconds': round(float(b), 3),
                      'later_minus_earlier_seconds': round(float(b-a), 3)})
    traffic = {'available': False}
    if raw_laps is not None:
        close = gap_to_car_ahead(pace, raw_laps).lt(CLOSE_SECONDS)
        traffic = {'available': True, 'close_seconds': CLOSE_SECONDS,
                   'share_of_laps_close': {d: round(float(v), 3) for d, v in close.groupby(pace.Driver).mean().items()},
                   'medians_without_close_laps': medians(pace.loc[~close])}
    return {'source': 'data/processed/austria-2026/selected_laps.csv (pace-eligible laps)',
            'whole_race': whole, 'same_compound_windows': windows, 'stints': stints,
            'same_compound_race_phase': phase, 'traffic': traffic,
            'limitations': 'Descriptive only. Fuel load, track evolution, traffic and tyre age overlap; '
                           'none of these numbers isolates a cause.'}


def pace_by_lap(pace: pd.DataFrame) -> alt.FacetChart:
    order = charts.driver_order(pace)
    data = pace.assign(Panel=pace.Driver+' · '+pace.Team)
    panels = sorted(data.Panel.unique(), key=lambda p: order.index(p.split(' · ')[0]))
    base = alt.Chart().encode(
        x=alt.X('LapNumber:Q', title='Lap', scale=alt.Scale(domain=[1, 71], nice=False)),
        y=alt.Y('LapTimeSeconds:Q', title='Lap time (s)', scale=alt.Scale(zero=False)),
        color=charts.compound_color(), detail='Stint:N',
        tooltip=['Driver', alt.Tooltip('LapNumber', title='Lap'), alt.Tooltip('Compound', title='Tyre'),
                 alt.Tooltip('LapTimeSeconds', title='Lap time (s)', format='.3f')])
    return alt.layer(base.mark_line(strokeWidth=2), base.mark_circle(size=36), data=data).properties(
        width=300, height=150).facet(facet=alt.Facet('Panel:N', sort=panels, title=None,
                                                     header=alt.Header(labelFontWeight='bold')), columns=2)


def window_chart(summary: dict, laps: pd.DataFrame) -> alt.FacetChart:
    teams = laps.drop_duplicates('Driver').set_index('Driver').Team
    rows = [{'Window': name, 'Driver': d, 'Team': teams[d], 'Median': v['median_seconds'], 'Laps': v['laps'],
             'Label': f"{v['median_seconds']:.2f} s"}
            for name, drivers in summary['same_compound_windows'].items() for d, v in drivers.items()]
    data = pd.DataFrame(rows)
    y = alt.Y('Driver:N', sort=charts.driver_order(data), title=None, axis=alt.Axis(labelFontWeight='bold', ticks=False, domain=False))
    base = alt.Chart().encode(y=y, x=alt.X('Median:Q', title='Typical lap (s)', scale=alt.Scale(zero=False, padding=30)))
    dots = base.mark_point(filled=True, size=150, opacity=1, stroke=charts.SURFACE['light'], strokeWidth=2).encode(
        color=charts.team_color(list(data.Team.unique()), 'light'), tooltip=['Driver', 'Team', 'Window', 'Median', 'Laps'])
    labels = base.mark_text(align='left', dx=10, fontSize=11).encode(text='Label:N')
    return alt.layer(dots, labels, data=data).properties(width=300, height=220).facet(
        column=alt.Column('Window:N', sort=list(WINDOWS), title=None, header=alt.Header(labelFontWeight='bold', labelFontSize=12)))


def race_phase_chart(pace: pd.DataFrame) -> alt.FacetChart:
    frames = []
    for driver, compound, earlier, later in same_compound_pairs(pace):
        for stint, phase in [(earlier, 'Earlier stint'), (later, 'Later stint')]:
            first, last = int(stint.LapNumber.min()), int(stint.LapNumber.max())
            frames.append(stint.assign(Phase=phase, Panel=f'{driver} · {compound.title()}', Span=f'{phase} ({first}–{last})'))
    data = pd.concat(frames)
    base = alt.Chart().encode(
        x=alt.X('TyreLife:Q', title='Tyre age (laps)'),
        y=alt.Y('LapTimeSeconds:Q', title='Lap time (s)', scale=alt.Scale(zero=False)), detail='Phase:N')
    lines = base.mark_line(strokeWidth=2).encode(
        color=charts.compound_color(),
        strokeDash=alt.StrokeDash('Phase:N', scale=alt.Scale(domain=['Earlier stint', 'Later stint'], range=[[5, 3], [1, 0]]),
                                  legend=alt.Legend(title=None, orient='top')),
        tooltip=['Driver', 'Span', alt.Tooltip('TyreLife', title='Tyre age (laps)'),
                 alt.Tooltip('LapTimeSeconds', title='Lap time (s)', format='.3f')])
    return alt.layer(lines, data=data).properties(width=300, height=150).facet(
        facet=alt.Facet('Panel:N', title=None, header=alt.Header(labelFontWeight='bold')), columns=2)


def pace_boxplot(pace: pd.DataFrame) -> alt.Chart:
    """Alternative to the range chart: the full spread, including slow outliers."""
    return alt.Chart(pace).mark_boxplot(extent=1.5, size=16, ticks=False, rule={'stroke': charts.VSC_FILL},
                                        median={'stroke': charts.SURFACE['light'], 'strokeWidth': 2}).encode(
        x=alt.X('LapTimeSeconds:Q', title='Lap time (s)', scale=alt.Scale(zero=False)),
        y=alt.Y('Driver:N', sort=charts.driver_order(pace), title=None, axis=alt.Axis(labelFontWeight='bold')),
        color=charts.team_color(list(pace.Team.unique()), 'light')).properties(height=240)


def relative_tyre_age_chart(pace: pd.DataFrame) -> alt.FacetChart:
    """Alternative to absolute lap times: each lap compared with the first three eligible laps of its stint."""
    start = pace.sort_values('LapNumber').groupby(['Driver', 'Stint']).LapTimeSeconds.transform(lambda s: s.iloc[:3].median())
    data = pace.assign(Relative=pace.LapTimeSeconds-start, Panel=pace.Driver+' · '+pace.Team)
    order = charts.driver_order(pace)
    panels = sorted(data.Panel.unique(), key=lambda p: order.index(p.split(' · ')[0]))
    base = alt.Chart().encode(
        x=alt.X('TyreLife:Q', title='Tyre age (laps)'),
        y=alt.Y('Relative:Q', title='Seconds slower than stint start'), color=charts.compound_color(), detail='Stint:N')
    zero = alt.Chart().mark_rule(color=charts.VSC_FILL, strokeDash=[2, 2]).encode(y=alt.datum(0))
    return alt.layer(zero, base.mark_line(strokeWidth=2), data=data).properties(width=300, height=150).facet(
        facet=alt.Facet('Panel:N', sort=panels, title=None, header=alt.Header(labelFontWeight='bold')), columns=2)


def figures(laps: pd.DataFrame, summary: dict) -> dict:
    pace = laps.loc[laps.EligibleForPace]
    return {
        'pace-by-lap': static(pace_by_lap(pace), 'Lap time through the race on normal racing laps'),
        'pace-same-compound-windows': static(window_chart(summary, laps), 'Typical lap when all six drivers were on the same tyre'),
        'tyre-race-phase': static(race_phase_chart(pace), 'Same tyre type, earlier and later stint'),
        'alternative-pace-boxplot': static(pace_boxplot(pace), 'Alternative: full spread of normal racing laps'),
        'alternative-relative-tyre-age': static(relative_tyre_age_chart(pace), 'Alternative: lap time relative to the start of each stint'),
    }


def main() -> None:
    laps = charts.load_data(DATA)['laps']
    raw = pd.read_csv(RAW_LAPS, dtype={'DriverNumber': str}) if RAW_LAPS.exists() else None
    summary = summarise(laps, raw)
    SUMMARY.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY.write_text(json.dumps(summary, indent=2, ensure_ascii=False)+'\n', encoding='utf-8')
    FIGURES.mkdir(parents=True, exist_ok=True)
    for name, chart in figures(laps, summary).items():
        chart.save(str(FIGURES/f'{name}.png'), scale_factor=2)
        print(f'saved figures/austria-2026/exploration/{name}.png')
    if raw is None:
        print('Raw laps not found: the traffic check is marked unavailable.')


if __name__ == '__main__':
    main()
