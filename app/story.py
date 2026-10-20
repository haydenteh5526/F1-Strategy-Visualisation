"""Prototype of the fan-facing story interface. Run with: streamlit run app/story.py"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

import charts
import replay
import theme

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
    return charts.load_data(DATA)


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


def overview_slide() -> None:
    # Our own HTML built from the prepared data, so it is safe to run as an iframe.
    st.iframe(replay.html(laps, 'timeline', mode, 52*laps.Driver.nunique()+80), height=52*laps.Driver.nunique()+90)
    st.caption('Each bar is one stint, starting with its tyre: S (Soft), M (Medium) or H (Hard). '
               'Gaps between bars are pit stops, grey bands are Virtual Safety Car laps and the stripe shows the team.')
    st.markdown('##### Strategy by driver')
    st.dataframe(strategy_table(laps, stints), hide_index=True, width='stretch')


def pace_slide() -> None:
    st.write(f'Compares {len(pace)} normal racing laps. '
             'Lap 1, pit-stop laps, VSC and yellow-flag laps, and deleted laps are left out.')
    st.iframe(replay.html(laps, 'pace', mode, 56*laps.Driver.nunique()+80), height=56*laps.Driver.nunique()+90)
    st.caption("The bar covers the middle half of each driver's normal racing laps and the dot marks their typical lap. "
               'A shorter bar means more consistent pace.')


def tyre_slide() -> None:
    st.write('Tyre age counts laps on a set, not wear. Cars also get lighter as fuel burns, '
             'so slower or faster laps are not caused by tyres alone.')
    panel_rows = -(-laps.Driver.nunique()//2)
    st.iframe(replay.html(laps, 'tyres', mode, 190*panel_rows+90), height=190*panel_rows+100)
    st.caption('Each line is one stint, labelled by tyre. Only normal racing laps are shown.')


def pit_slide() -> None:
    st.write('Pit-lane time covers the whole trip through the pit lane, not just the stationary stop.')
    st.iframe(replay.html(laps, 'positions', mode, 420), height=430)
    st.caption('Dots mark the lap each driver entered the pits. Team-mates share a colour, '
               'one solid and one dashed; labels on the right name each driver.')
    st.markdown('##### Pit stops')
    st.dataframe(pit_table(visits), hide_index=True, width='stretch')


def vsc_slide() -> None:
    vsc = laps.loc[laps.HasVSC, 'LapNumber']
    st.write(f'VSC periods affected laps {lap_ranges(vsc)}. These laps are left out of pace comparisons '
             'but still matter for pit-stop timing.' if len(vsc) else 'No VSC laps for the selected teams.')
    st.iframe(replay.html(laps, 'vsc', mode, 420), height=430)
    st.caption('Each car drops a dot for every lap except lap 1 and pit-stop laps. The yellow strips cover the laps flagged as '
               'Virtual Safety Car affected, and the label follows the recorded VSC times (deployed, then ending).')


SLIDES = {'The race at a glance': overview_slide,
          '1. Who was fastest in normal racing?': pace_slide,
          '2. How did lap times change as tyres aged?': tyre_slide,
          '3. What happened around the pit stops?': pit_slide,
          '4. How did the Virtual Safety Car change things?': vsc_slide}


def move(step: int) -> None:
    st.session_state.slide = (st.session_state.slide+step) % len(SLIDES)
    st.session_state.direction = 'next' if step > 0 else 'previous'
    st.query_params['chart'] = str(st.session_state.slide+1)  # Keeps the same chart after a reload.


st.set_page_config(page_title='F1 Strategy Visualisation', layout='wide')
data = load()
provenance = data['summary']['provenance']
# The app is configured dark; the browser's own theme is not reliable on the first run.
mode = 'dark' if st.get_option('theme.base') == 'dark' or st.context.theme.type == 'dark' else 'light'
if 'slide' not in st.session_state:
    chart = st.query_params.get('chart', '1')
    st.session_state.slide = (int(chart)-1) % len(SLIDES) if chart.isdigit() and int(chart) > 0 else 0
st.session_state.setdefault('direction', 'next')

race_date = pd.Timestamp(provenance['race_date'])
st.markdown(theme.STYLE, unsafe_allow_html=True)
with st.container(key='scroll-keeper'):
    st.iframe(theme.SCROLL_KEEPER, height=1)
st.html(theme.hero('Red Bull Ring · ' + f'{race_date.day} {race_date:%B %Y}', '2026 Austrian Grand Prix',
                   'Pace, tyres and pit stops for both drivers from Red Bull Racing, Mercedes and Ferrari'))
st.caption(
           f"Data: FastF1 {provenance['fastf1_version']}, accessed {provenance['access_date']}.")

teams = st.multiselect('Teams', TEAMS, default=TEAMS)
laps = data['laps'].loc[data['laps'].Team.isin(teams)]
stints = data['stints'].loc[data['stints'].Team.isin(teams)]
visits = data['visits'].loc[data['visits'].Team.isin(teams)]
if not teams:
    st.warning('Select at least one team.')
    st.stop()
pace = laps.loc[laps.EligibleForPace]

st.html(theme.fact_cards([('Race laps', int(data['laps'].LapNumber.max())),
                           ('Drivers compared', int(laps.Driver.nunique())),
                           ('Pit stops, selected teams', len(visits)),
                           ('Virtual Safety Car periods', len(charts.vsc_bands(data['laps'])))]))

with st.container(border=True, key='chart-frame'):
    left, middle, right = st.columns([1, 14, 1], vertical_alignment='center')
    left.button(':material/chevron_left:', key='previous', help='Previous chart', on_click=move, args=(-1,))
    right.button(':material/chevron_right:', key='next', help='Next chart', on_click=move, args=(1,))
    title = list(SLIDES)[st.session_state.slide]
    middle.html(theme.slide_progress(st.session_state.slide, list(SLIDES)))
    middle.subheader(title)
    # A new key per slide and direction remounts the content, which replays the slide-in animation.
    with st.container(key=f'slide-{st.session_state.slide}-{st.session_state.direction}'):
        SLIDES[title]()

st.subheader('Key terms')
for term, meaning in GLOSSARY.items():
    st.markdown(f'**{term}**: {meaning}')

st.html(theme.FLAG)
summary = data['summary']
st.subheader('About the data')
st.markdown(f"""
- **Source:** FastF1 {provenance['fastf1_version']} race timing, accessed {provenance['access_date']}. No telemetry is used.
- **Laps:** {summary['selected_rows']} laps for the six drivers; {summary['pace_eligible']} count as normal racing laps.
- **Normal racing laps** leave out lap 1, pit-stop laps, VSC and yellow-flag laps, deleted laps and {summary['accuracy_flagged']} laps that FastF1 flags as possibly inaccurate. No laps are deleted from the data.
- **Official result:** [Formula 1 race result]({provenance['official_result']}).
""")

st.subheader('Limits')
st.markdown("""
- Lap times also depend on fuel load, traffic, track conditions and tyre age, so these views do not prove what caused a result.
- Gaps are measured once per lap at the finish line, not live.
- Pit-lane time is the whole trip through the pit lane, not the stationary stop or the time lost by stopping.
- This is one race and six drivers; it does not show which strategy was best.
""")
