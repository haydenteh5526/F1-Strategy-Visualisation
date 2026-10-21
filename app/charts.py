"""Prototype Altair charts for the story interface, built from the prepared data."""
from __future__ import annotations

import json
from pathlib import Path

import altair as alt
import pandas as pd

TEAMS = ['Red Bull Racing', 'Mercedes', 'Ferrari']
# Validated categorical slots (blue, aqua, orange) chosen to echo each team's livery.
TEAM_COLORS = {'light': ['#2a78d6', '#1baf7a', '#eb6834'], 'dark': ['#3987e5', '#199e70', '#d95926']}
# F1 convention (red, yellow, white) stepped to stay readable; Hard is a neutral grey on purpose,
# so every tyre mark also carries its S/M/H letter.
COMPOUNDS = ['SOFT', 'MEDIUM', 'HARD']
COMPOUND_COLORS = ['#e34948', '#eda100', '#898781']
VSC_FILL = '#898781'
STATUS_COLUMNS = {'TrackStatus': str, 'EntryTrackStatus': str, 'ExitTrackStatus': str}
SURFACE = {'light': '#ffffff', 'dark': '#15151e'}
INK = {'light': '#31333f', 'dark': '#f0efec'}



def load_data(data_dir: Path) -> dict:
    """Read the prepared Austria 2026 files the charts use."""
    read = lambda name: pd.read_csv(data_dir/name, dtype=STATUS_COLUMNS)
    return {'laps': read('selected_laps.csv'), 'stints': read('stints.csv'), 'visits': read('pit_visits.csv'),
            'summary': json.loads((data_dir/'audit_summary.json').read_text())}


def driver_order(frame: pd.DataFrame) -> list[str]:
    pairs = frame[['Team', 'Driver']].drop_duplicates()
    return sorted(pairs.Driver, key=lambda d: (TEAMS.index(pairs.set_index('Driver').Team[d]), d))


def team_color(teams: list[str], mode: str) -> alt.Color:
    domain = [team for team in TEAMS if team in teams]
    palette = dict(zip(TEAMS, TEAM_COLORS[mode]))
    return alt.Color('Team:N', scale=alt.Scale(domain=domain, range=[palette[t] for t in domain]),
                     legend=alt.Legend(title=None, orient='top', symbolOpacity=1))


def compound_color() -> alt.Color:
    return alt.Color('Compound:N', scale=alt.Scale(domain=COMPOUNDS, range=COMPOUND_COLORS),
                     legend=alt.Legend(title='Tyre', orient='top', labelExpr='slice(datum.label, 0, 1) + lower(slice(datum.label, 1))'))


def driver_marks(frame: pd.DataFrame, mode: str) -> dict:
    """Team colour plus a shape per team-mate, sharing one driver legend, so drivers stay identifiable in print."""
    order = driver_order(frame)
    teams = frame.drop_duplicates('Driver').set_index('Driver').Team
    palette = dict(zip(TEAMS, TEAM_COLORS[mode]))
    legend = alt.Legend(title='Driver', orient='top')
    return {'color': alt.Color('Driver:N', scale=alt.Scale(domain=order, range=[palette[teams[d]] for d in order]), legend=legend),
            'shape': alt.Shape('Driver:N', scale=alt.Scale(domain=order, range=['circle', 'triangle-up']*len(TEAMS)),
                               legend=legend)}


def vsc_bands(laps: pd.DataFrame) -> pd.DataFrame:
    """Contiguous VSC-affected laps as [start, end] lap spans for shading."""
    numbers = sorted(int(n) for n in laps.loc[laps.HasVSC, 'LapNumber'].unique())
    bands = []
    for n in numbers:
        if bands and n == bands[-1]['End']+1:
            bands[-1]['End'] = n
        else:
            bands.append({'Start': n, 'End': n})
    return pd.DataFrame(bands, columns=['Start', 'End']).assign(Label='VSC')


def shade(bands: pd.DataFrame, label_y: int | None = 0) -> alt.LayerChart:
    """Grey bands behind VSC laps, labelled at pixel height label_y (None for no label)."""
    rect = alt.Chart(bands).mark_rect(color=VSC_FILL, opacity=.16).encode(
        x=alt.X('S:Q', title='Lap'), x2='End:Q').transform_calculate(S='datum.Start - 1')
    if label_y is None:
        return rect
    label = alt.Chart(bands).mark_text(align='left', baseline='top' if label_y == 0 else 'bottom', dx=3,
                                       dy=3 if label_y == 0 else -3, fontSize=11, color=VSC_FILL).encode(
        x=alt.X('S:Q', title='Lap'), y=alt.value(label_y), text='Label:N').transform_calculate(S='datum.Start - 1')
    return rect+label


def stint_timeline(stints: pd.DataFrame, laps: pd.DataFrame, mode: str = 'light') -> alt.LayerChart:
    """Broadcast-style stint chart: team stripe, tyre icon at each stint start, VSC bands and the finish line."""
    order = driver_order(stints)
    finish = int(laps.LapNumber.max())
    data = stints.assign(
        Start=stints.FirstLap-1+.2, End=stints.LastLap-.2, Icon=stints.FirstLap-1+1.4,
        Letter=stints.Compound.str[0], Laps=stints.FirstLap.astype(int).astype(str)+'–'+stints.LastLap.astype(int).astype(str),
        TyreAge=stints.FirstRecordedTyreAge.astype(int).astype(str)+' → '+stints.LastRecordedTyreAge.astype(int).astype(str))
    y = alt.Y('Driver:N', sort=order, title=None, scale=alt.Scale(paddingOuter=.8),
              axis=alt.Axis(labelFontWeight='bold', labelFontSize=12, labelPadding=10, ticks=False, domain=False))
    x = alt.X('Start:Q', title='Lap', scale=alt.Scale(domain=[-2.4, finish+1], nice=False),
              axis=alt.Axis(values=list(range(0, finish+1, 5))))
    tooltip = ['Driver', 'Team', alt.Tooltip('Compound', title='Tyre'), alt.Tooltip('Laps', title='Laps'),
               alt.Tooltip('TyreAge', title='Tyre age (laps)')]
    tyre = alt.Scale(domain=COMPOUNDS, range=COMPOUND_COLORS)
    stripe = alt.Chart(data.drop_duplicates('Driver')).mark_bar(height={'band': .62}, cornerRadius=2).encode(
        x=x, x2=alt.datum(-1.2), y=y, color=team_color(list(data.Team.unique()), mode).legend(None),
        tooltip=['Driver', 'Team']).transform_calculate(Start='-2')
    bars = alt.Chart(data).mark_bar(cornerRadius=4, height={'band': .62}).encode(
        x=x, x2='End:Q', y=y, color=compound_color(), tooltip=tooltip)
    icons = alt.Chart(data).mark_point(filled=True, size=260, opacity=1, fill=SURFACE[mode], strokeWidth=3).encode(
        x=alt.X('Icon:Q', title='Lap'), y=y, stroke=alt.Stroke('Compound:N', scale=tyre, legend=None), tooltip=tooltip)
    letters = alt.Chart(data).mark_text(fontSize=10, fontWeight='bold', color=INK[mode]).encode(
        x=alt.X('Icon:Q', title='Lap'), y=y, text='Letter:N', tooltip=tooltip)
    line = alt.Chart(pd.DataFrame({'Lap': [finish]})).mark_rule(strokeDash=[3, 3], color=INK[mode], opacity=.6).encode(
        x=alt.X('Lap:Q', title='Lap'))
    flag = alt.Chart(pd.DataFrame({'Lap': [finish], 'Label': ['FINISH']})).mark_text(
        align='right', baseline='top', dx=-4, dy=3, fontSize=10, fontWeight='bold', color=INK[mode]).encode(
        x=alt.X('Lap:Q', title='Lap'), y=alt.value(0), text='Label:N')
    return alt.layer(shade(vsc_bands(laps)), line, stripe, bars, icons, letters, flag).resolve_scale(
        color='independent').properties(height=40*len(order))


def pace_summary(pace: pd.DataFrame) -> pd.DataFrame:
    """Typical (median) lap and the middle half of each driver's normal racing laps."""
    if pace.empty:
        return pd.DataFrame(columns=['Team', 'Driver', 'Typical', 'Low', 'High', 'Laps', 'Label'])
    times = pace.groupby(['Team', 'Driver']).LapTimeSeconds
    return pd.DataFrame({'Typical': times.median(), 'Low': times.quantile(.25), 'High': times.quantile(.75),
                         'Laps': times.size()}).reset_index().assign(
        Label=lambda d: d.Typical.map('{:.2f} s'.format)+' · '+d.Laps.astype(str)+' laps')


def pace_chart(pace: pd.DataFrame, mode: str) -> alt.LayerChart:
    summary = pace_summary(pace)
    order = driver_order(summary)
    color = team_color(list(summary.Team.unique()), mode).legend(None)
    x = alt.X('Low:Q', title='Lap time (s)', axis=alt.Axis(tickCount=5, format='.1f'),
              scale=alt.Scale(domain=[summary.Low.min()-.3, summary.High.max()+.5], nice=False))
    y = alt.Y('Driver:N', sort=order, title=None,
              axis=alt.Axis(labelFontWeight='bold', ticks=False, domain=False, grid=False))
    tooltip = ['Driver', 'Team', alt.Tooltip('Typical', title='Typical lap (s)', format='.3f'),
               alt.Tooltip('Low', title='Middle half from (s)', format='.3f'),
               alt.Tooltip('High', title='Middle half to (s)', format='.3f'), alt.Tooltip('Laps', title='Laps')]
    base = alt.Chart(summary).encode(y=y, color=color, tooltip=tooltip)
    spread = base.mark_bar(height=10, cornerRadius=5, opacity=.35).encode(x=x, x2='High:Q')
    typical = alt.Chart(summary).mark_point(filled=True, size=190, opacity=1, stroke=SURFACE[mode], strokeWidth=2).encode(
        x=alt.X('Typical:Q', title='Lap time (s)'), y=y, tooltip=tooltip, **driver_marks(summary, mode))
    labels = alt.Chart(summary).mark_text(align='left', dx=8, fontSize=12, color=INK[mode]).encode(
        x=alt.X('High:Q', title='Lap time (s)'), y=y, text='Label:N')
    # The bars use a team colour scale and the marks a driver one, so the layers must not share a colour scale.
    return alt.layer(spread, typical, labels).resolve_scale(color='independent', shape='independent').properties(height=52*len(order))


def label_heights(pace: pd.DataFrame, clear: float = .45, reach: int = 9) -> pd.Series:
    """Height for each stint-end label, nudged up only where it would collide with another label in the same panel."""
    heights = pace.LapTimeSeconds.copy()
    for driver, rows in pace.groupby('Driver'):
        placed = []
        ends = rows.sort_values('TyreLife').groupby('Stint').tail(1).sort_values('LapTimeSeconds')
        for index, end in ends.iterrows():
            height = end.LapTimeSeconds
            while any(abs(height-h) < clear and abs(end.TyreLife-age) < reach for age, h in placed):
                height += .3
            placed.append((end.TyreLife, height))
            heights[index] = height
    return heights


def tyre_age_chart(pace: pd.DataFrame, mode: str = 'light') -> alt.FacetChart:
    """One point per normal racing lap, so no line crosses an excluded lap; panels and stint labels carry lap counts."""
    order = driver_order(pace)
    totals = pace.groupby('Driver').size()
    stint_laps = pace.groupby(['Driver', 'Stint']).LapNumber.transform('size')
    data = pace.assign(Panel=pace.Driver+' · '+pace.Team+' · '+pace.Driver.map(totals).astype(str)+' laps',
                       Letter=pace.Compound.str[0]+' · '+stint_laps.astype(str)+' laps',
                       LabelY=label_heights(pace))
    panels = sorted(data.Panel.unique(), key=lambda p: order.index(p.split(' · ')[0]))
    base = alt.Chart().encode(
        x=alt.X('TyreLife:Q', title='Tyre age (laps)'),
        y=alt.Y('LapTimeSeconds:Q', title='Lap time (s)', scale=alt.Scale(zero=False)),
        detail='Stint:N')
    points = base.mark_circle(size=38, opacity=.95).encode(color=compound_color(), tooltip=[
        'Driver', alt.Tooltip('Compound', title='Tyre'), alt.Tooltip('TyreLife', title='Tyre age (laps)'),
        alt.Tooltip('LapNumber', title='Lap'), alt.Tooltip('LapTimeSeconds', title='Lap time (s)', format='.3f')])
    ends = base.transform_window(Rank='rank()', sort=[alt.SortField('TyreLife', order='descending')],
                                 groupby=['Panel', 'Stint']).transform_filter('datum.Rank == 1')
    labels = ends.mark_text(align='left', dx=7, fontSize=11, fontWeight='bold', color=INK[mode]).encode(
        y=alt.Y('LabelY:Q', scale=alt.Scale(zero=False)), text='Letter:N')
    return alt.layer(points, labels, data=data).properties(width=250, height=150).facet(
        facet=alt.Facet('Panel:N', sort=panels, title=None, header=alt.Header(labelFontWeight='bold', labelFontSize=12)),
        columns=2).resolve_scale(x='shared', y='shared')


def position_chart(laps: pd.DataFrame, visits: pd.DataFrame, mode: str) -> alt.LayerChart:
    order = driver_order(laps)
    second = {d for d in order if order.index(d) % 2 == 1}
    data = laps.assign(Line=laps.Driver.map(lambda d: 'second' if d in second else 'first'))
    color = team_color(list(laps.Team.unique()), mode)
    y = alt.Y('Position:Q', title='Position', scale=alt.Scale(reverse=True, domain=[1, int(laps.Position.max())], nice=False),
              axis=alt.Axis(tickMinStep=1))
    x = alt.X('LapNumber:Q', title='Lap', scale=alt.Scale(domain=[1, int(laps.LapNumber.max())], nice=False))
    lines = alt.Chart(data).mark_line(strokeWidth=2).encode(
        x=x, y=y, color=color, detail='Driver:N',
        strokeDash=alt.StrokeDash('Line:N', scale=alt.Scale(domain=['first', 'second'], range=[[1, 0], [5, 3]]), legend=None))
    stops = data.merge(visits[['Driver', 'EntryLap']].astype({'EntryLap': float}), left_on=['Driver', 'LapNumber'], right_on=['Driver', 'EntryLap'])
    pits = alt.Chart(stops).mark_point(filled=True, size=70, stroke=SURFACE[mode], strokeWidth=2, opacity=1).encode(
        x=x, y=y, color=color, tooltip=['Driver', alt.Tooltip('LapNumber', title='Pit stop on lap'), 'Position'])
    hover = alt.Chart(data).mark_point(size=80, opacity=0).encode(
        x=x, y=y, tooltip=['Driver', 'Team', alt.Tooltip('LapNumber', title='Lap'), 'Position'])
    last = data.loc[data.LapNumber.eq(data.LapNumber.max())]
    labels = alt.Chart(last).mark_text(align='left', dx=6, fontSize=11, fontWeight='bold', color=INK[mode]).encode(
        x=x, y=y, text='Driver:N')
    return alt.layer(shade(vsc_bands(laps), label_y=300), lines, pits, hover, labels).properties(height=300)


def vsc_chart(laps: pd.DataFrame, mode: str) -> alt.LayerChart:
    # Lap 1 and pit laps are left out so the VSC effect is not mixed with standing starts or stops.
    data = laps.loc[~(laps.IsFirstLap | laps.IsPitInLap | laps.IsPitOutLap)].assign(
        Phase=lambda d: d.HasVSC.map({True: 'VSC lap', False: 'Other lap'}))
    dots = alt.Chart(data).mark_point(filled=True, size=70, opacity=.9, stroke=SURFACE[mode], strokeWidth=1).encode(
        x=alt.X('LapNumber:Q', title='Lap', scale=alt.Scale(domain=[1, int(laps.LapNumber.max())], nice=False)),
        y=alt.Y('LapTimeSeconds:Q', title='Lap time (s)', scale=alt.Scale(zero=False)),
        **driver_marks(data, mode),
        tooltip=['Driver', alt.Tooltip('LapNumber', title='Lap'), alt.Tooltip('LapTimeSeconds', title='Lap time (s)', format='.3f'),
                 alt.Tooltip('Phase', title='Lap type')])
    return alt.layer(shade(vsc_bands(laps)), dots).properties(height=260)
