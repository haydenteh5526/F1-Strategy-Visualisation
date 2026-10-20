"""Save the story charts as PNG images for slides and the static version of the story."""
from __future__ import annotations

from pathlib import Path
import sys

import altair as alt

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'app'))
import charts  # noqa: E402

DATA = ROOT/'data/processed/austria-2026'
OUT = ROOT/'figures/austria-2026'
INK, GRID = '#31333f', '#e6eaf1'


def figures(data: dict) -> dict[str, alt.TopLevelMixin]:
    laps, stints, visits = data['laps'], data['stints'], data['visits']
    pace = laps.loc[laps.EligibleForPace]
    titled = {
        'stint-timeline': (charts.stint_timeline(stints, laps), 'Tyre stints by driver'),
        'pace': (charts.pace_chart(pace, 'light'), 'Typical lap and middle half of normal racing laps'),
        'tyre-age': (charts.tyre_age_chart(pace), 'Lap time against tyre age on normal racing laps'),
        'positions': (charts.position_chart(laps, visits, 'light'), 'Position by lap, with pit stops'),
        'vsc': (charts.vsc_chart(laps, 'light'), 'Lap times around Virtual Safety Car periods'),
    }
    return {name: static(chart, title) for name, (chart, title) in titled.items()}


def static(chart: alt.TopLevelMixin, title: str) -> alt.TopLevelMixin:
    """Fixed light styling so exported images look the same on every machine."""
    if not isinstance(chart, alt.FacetChart):
        chart = chart.properties(width=760)
    return chart.properties(title=alt.Title(title, anchor='start', fontSize=15, color=INK)).configure(
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
