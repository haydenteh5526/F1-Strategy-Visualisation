"""Prototype of the fan-facing story interface. Run with: streamlit run app/story.py"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit as st

import charts

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT/'data/processed/austria-2026'
TEAMS = charts.TEAMS
# Terms the audience brief asks us to explain on first use.
GLOSSARY = {
    'Stint': 'The laps a driver completes on one set of tyres, between the start, pit stops and the finish.',
    'Compound': 'The type of tyre: Soft, Medium or Hard.',
    'Tyre age': 'How many laps a set of tyres has done. It counts laps; it does not measure wear.',
    'Virtual Safety Car (VSC)': 'Every driver must slow to a set pace and cannot overtake while an incident is cleared. '
                                'VSC laps are slower, so they are not compared with normal racing laps.',
    'Pit-lane time': 'Time from entering to leaving the pit lane. It includes driving through the pit lane, '
                     'not just the time the car is stationary.',
    'Lap-boundary interval': 'How long after the leader a driver finished the same lap. '
                             'It is measured once per lap at the finish line, not live.',
    'Normal racing lap': 'A lap used for pace comparisons: not lap 1, not a pit-stop lap, no VSC or yellow flag, '
                         'and not deleted or flagged by the timing data.',
}


@st.cache_data
def load() -> dict:
    status = {'TrackStatus': str, 'EntryTrackStatus': str, 'ExitTrackStatus': str}
    read = lambda name: pd.read_csv(DATA/name, dtype=status)
    return {'laps': read('selected_laps.csv'), 'stints': read('stints.csv'), 'visits': read('pit_visits.csv'),
            'summary': json.loads((DATA/'audit_summary.json').read_text())}


def lap_ranges(laps: pd.Series) -> str:
    """Collapse lap numbers into readable ranges, e.g. 24–26, 52–53."""
    laps = sorted(int(lap) for lap in laps.unique())
    ranges, start = [], None
    for lap, following in zip(laps, laps[1:]+[None]):
        start = lap if start is None else start
        if following != lap+1:
            ranges.append(f'{start}' if start == lap else f'{start}–{lap}')
            start = None
    return ', '.join(ranges)


def strategy_table(laps: pd.DataFrame, stints: pd.DataFrame) -> pd.DataFrame:
    used = laps.loc[~laps.FreshTyre].groupby(['Driver', 'Stint']).size().index
    rows = []
    for (team, driver), group in stints.sort_values('FirstLap').groupby(['Team', 'Driver'], sort=False):
        steps = [f"{row.Compound.title()}{' (used)' if (driver, row.Stint) in used else ''} "
                 f'{int(row.FirstLap)}–{int(row.LastLap)}' for row in group.itertuples()]
        final = laps.loc[laps.Driver.eq(driver)].sort_values('LapNumber').iloc[-1]
        rows.append({'Team': team, 'Driver': driver, 'Tyres (laps)': ' → '.join(steps),
                     'Pit stops': len(group)-1, f'Position after lap {int(final.LapNumber)}': int(final.Position)})
    order = {team: i for i, team in enumerate(TEAMS)}
    return pd.DataFrame(rows).sort_values(['Team', 'Driver'], key=lambda s: s.map(order) if s.name == 'Team' else s)


def pit_table(visits: pd.DataFrame) -> pd.DataFrame:
    flagged = lambda code: any(c in code for c in '267')
    return pd.DataFrame({
        'Driver': visits.Driver, 'Team': visits.Team, 'In-lap': visits.EntryLap,
        'Pit-lane time (s)': visits.PitLaneElapsedSeconds.round(1),
        'VSC or yellow on in/out-lap': [('Yes' if flagged(a) or flagged(b) else 'No')
                                        for a, b in zip(visits.EntryTrackStatus, visits.ExitTrackStatus)]
    }).sort_values(['In-lap', 'Driver'])


def roys_part() -> None:
    st.badge("Roy's part: chart and analysis", icon=':material/bar_chart:', color='blue')


st.set_page_config(page_title='F1 Strategy Visualisation', layout='wide')
data = load()
provenance = data['summary']['provenance']
mode = 'dark' if st.context.theme.type == 'dark' else 'light'

st.title('Pace, tyres and pit stops at the 2026 Austrian Grand Prix')
st.caption('Both drivers from Red Bull Racing, Mercedes and Ferrari. '
           f"Data: FastF1 {provenance['fastf1_version']}, accessed {provenance['access_date']}. "
           "Charts are Roy's part; these are prototypes for him to refine.")

teams = st.multiselect('Teams', TEAMS, default=TEAMS)
laps = data['laps'].loc[data['laps'].Team.isin(teams)]
stints = data['stints'].loc[data['stints'].Team.isin(teams)]
visits = data['visits'].loc[data['visits'].Team.isin(teams)]
if not teams:
    st.warning('Select at least one team.')
    st.stop()
pace = laps.loc[laps.EligibleForPace]

st.header('The race at a glance')
roys_part()
st.altair_chart(charts.stint_timeline(stints, laps), width='stretch')
st.caption('Each bar is one stint, labelled S (Soft), M (Medium) or H (Hard). '
           'Gaps between bars are pit stops; grey bands are Virtual Safety Car laps.')
with st.expander('Strategy details'):
    st.dataframe(strategy_table(laps, stints), hide_index=True, width='stretch')
with st.expander('What do these terms mean?'):
    for term, meaning in GLOSSARY.items():
        st.markdown(f'**{term}**: {meaning}')

st.header('1. Who was fastest in normal racing?')
st.write(f'Compares {len(pace)} normal racing laps. '
         'Lap 1, pit-stop laps, VSC and yellow-flag laps, and deleted laps are left out.')
roys_part()
st.altair_chart(charts.pace_chart(pace, mode), width='stretch')
st.caption("The bar covers the middle half of each driver's normal racing laps and the dot marks their typical lap. "
           'A shorter bar means more consistent pace.')

st.header('2. How did lap times change as tyres aged?')
st.write('Tyre age counts laps on a set, not wear. Cars also get lighter as fuel burns, '
         'so slower or faster laps are not caused by tyres alone.')
roys_part()
st.altair_chart(charts.tyre_age_chart(pace))
st.caption('Each line is one stint, labelled by tyre. Only normal racing laps are shown.')

st.header('3. What happened around the pit stops?')
st.write('Pit-lane time covers the whole trip through the pit lane, not just the stationary stop.')
roys_part()
st.altair_chart(charts.position_chart(laps, visits, mode), width='stretch')
st.caption('Dots mark the lap each driver entered the pits. Team-mates share a colour, '
           'one solid and one dashed; labels on the right name each driver.')
with st.expander('Pit stop details'):
    st.dataframe(pit_table(visits), hide_index=True, width='stretch')

st.header('4. How did the Virtual Safety Car change things?')
vsc = laps.loc[laps.HasVSC, 'LapNumber']
st.write(f'VSC periods affected laps {lap_ranges(vsc)}. These laps are left out of pace comparisons '
         'but still matter for pit-stop timing.' if len(vsc) else 'No VSC laps for the selected teams.')
roys_part()
st.altair_chart(charts.vsc_chart(laps, mode), width='stretch')
st.caption('Lap 1 and pit-stop laps are left out, so the jumps inside the grey bands show the VSC slowdown.')

st.divider()
st.caption('Lap times also depend on fuel load, traffic and conditions, so these views do not prove '
           'what caused a result or which strategy was best. '
           f"Official result: {provenance['official_result']}")
