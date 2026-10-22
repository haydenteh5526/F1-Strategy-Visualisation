"""Save the story charts as PNG images for slides and the static version of the story."""
from __future__ import annotations

from pathlib import Path
import sys
import textwrap

import altair as alt

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'app'))
import charts  # noqa: E402

DATA = ROOT/'data/processed/austria-2026'
OUT = ROOT/'figures/austria-2026'
INK, GRID = '#31333f', '#e6eaf1'
# Units and filtering context printed under each title, so an image still makes sense on its own.
NORMAL = 'Normal racing laps only: no lap 1, pit-stop, VSC or yellow-flag laps, and no deleted or flagged laps.'
NOTES = {
    'stint-timeline': 'Bars are stints on one set of tyres (S soft, M medium, H hard); gaps are pit stops; grey bands are VSC laps. Axis in laps.',
    'pace': NORMAL + ' Times in seconds; dot = median, bar = middle half of laps.',
    'pace-matched': 'Only eligible normal-racing laps are paired. Tyre ages, fuel and traffic remain uncontrolled. Diamond = fewer than 5 pairs; empty = no pairs.',
    'tyre-age': NORMAL + ' Tyre age counts laps on a set, not wear; fuel and traffic are not controlled.',
    'positions': 'Position after each lap (1 = leading); dots mark the lap a driver entered the pits; solid and dashed lines are team-mates; grey bands are VSC laps.',
    'vsc': 'Lap times in seconds; grey bands are laps with a VSC flag. Slower laps here are not used in pace comparisons.',
}


def figures(data: dict) -> dict[str, alt.TopLevelMixin]:
    laps, stints, visits = data['laps'], data['stints'], data['visits']
    pace = laps.loc[laps.EligibleForPace]
    summary = charts.matched_pace(laps)
    matched = alt.vconcat(*[
        alt.hconcat(*[
            charts.matched_pace_chart(summary.loc[summary.Window.eq(window) & summary.Compound.eq(compound)],
                                      legend=False, pair_domain=['HAD − VER', 'ANT − RUS', 'HAM − LEC']).properties(
                                          width=320, title=f'Laps {window} · {compound.title()}')
            for compound in ['MEDIUM', 'HARD']])
        for window in ['1–20', '21–40', '41–60', '61–71']])
    titled = {
        'stint-timeline': (charts.stint_timeline(stints, laps), 'Tyre stints by driver'),
        'pace': (charts.pace_chart(pace, 'light'), 'Typical lap and middle half of normal racing laps'),
        'pace-matched': (matched, 'Matched race windows: median paired difference A − B (s); negative = A faster'),
        'tyre-age': (charts.tyre_age_chart(pace), 'Lap time against tyre age on normal racing laps'),
        'positions': (charts.position_chart(laps, visits, 'light'), 'Position by lap, with pit stops'),
        'vsc': (charts.vsc_chart(laps, 'light'), 'Lap times around Virtual Safety Car periods'),
    }
    source = f"Source: FastF1 {data['summary']['provenance']['fastf1_version']}, Austria 2026 race timing (retained snapshot)."
    return {name: static(chart, title, [source, *textwrap.wrap(NOTES[name], 105)]) for name, (chart, title) in titled.items()}


def static(chart: alt.TopLevelMixin, title: str, notes: list[str]) -> alt.TopLevelMixin:
    """Fixed light styling so exported images look the same on every machine."""
    if not isinstance(chart, (alt.FacetChart, alt.VConcatChart)):
        chart = chart.properties(width=760)
    return chart.properties(title=alt.Title(title, anchor='start', fontSize=15, color=INK, subtitle=notes, subtitleColor=INK)).configure(
        background='#ffffff', font='Arial').configure_view(stroke=None).configure_axis(
        labelColor=INK, titleColor=INK, gridColor=GRID, domainColor=GRID, tickColor=GRID).configure_legend(
        labelColor=INK, titleColor=INK).configure_header(labelColor=INK).configure_text(color=INK)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for name, chart in figures(charts.load_data(DATA)).items():
        chart.save(str(OUT/f'{name}.png'), scale_factor=2)
        print(f'saved figures/austria-2026/{name}.png')


if __name__ == '__main__':
    main()
