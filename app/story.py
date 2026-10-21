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


def pit_clock_table(visits: list[dict], teams: pd.Series) -> pd.DataFrame:
    """All pit visits with how each relates to the VSC clock; flagged laps and real overlap are different questions."""
    table = pd.DataFrame(visits)
    return pd.DataFrame({
        'Driver': table.driver, 'Team': table.driver.map(teams), 'Entry lap': table.entryLap,
        'Pit-lane time (s)': table.elapsed.round(1),
        'VSC flag on a pit lap': table.whole.map({True: 'Yes', False: 'No'}),
        'Overlaps VSC (s)': table.overlap.round(1),
        'Within 1 s of a VSC boundary': table.near.map({True: 'Yes', False: 'No'}),
    }).sort_values(['Entry lap', 'Driver'])


def overview_slide() -> None:
    # Our own HTML built from the prepared data, so it is safe to run as an iframe.
    st.iframe(replay.html(laps, 'timeline', mode, 52*laps.Driver.nunique()+80), height=52*laps.Driver.nunique()+90)
    st.caption('Each bar is one stint, starting with its tyre: S (Soft), M (Medium) or H (Hard). '
               'Gaps between bars are pit stops, grey bands are Virtual Safety Car laps and the stripe shows the team. '
               'Stint length is observed use, not tyre wear.')
    st.markdown('##### Strategy by driver')
    st.dataframe(strategy_table(laps, stints), hide_index=True, width='stretch')


def pace_slide() -> None:
    st.write(f'Compares {len(pace)} normal racing laps. '
             'Lap 1, pit-stop laps, VSC and yellow-flag laps, and deleted laps are left out.')
    st.iframe(replay.html(laps, 'pace', mode, 56*laps.Driver.nunique()+80), height=56*laps.Driver.nunique()+90)
    st.caption("The bar covers the middle half of each driver's normal racing laps, the dot or triangle marks their typical lap "
               'and the count is the number of laps behind it. Lower times are faster; a shorter bar means more consistent pace, '
               'not a better strategy. Fuel load, traffic and conditions are not controlled.')


def tyre_slide() -> None:
    st.write('Tyre age counts laps on a set, not wear. Cars also get lighter as fuel burns, '
             'so slower or faster laps are not caused by tyres alone.')
    panel_rows = -(-laps.Driver.nunique()//2)
    st.iframe(replay.html(laps, 'tyres', mode, 190*panel_rows+90), height=190*panel_rows+100)
    st.caption('Each dot is one normal racing lap, coloured by tyre and labelled with its stint and lap count. '
               'Lines are not drawn across the laps that are left out. Sparse stints may not support a trend.')


def pit_slide() -> None:
    st.info('**Provisional main message:** interpreting pit-stop timing requires the recorded event clock. A VSC flag on a '
            'pit-entry or pit-exit lap does not by itself show that the pit visit happened during a Virtual Safety Car period.',
            icon=':material/flag:')
    visits_clock = replay.pit_data(list(laps.Driver.unique()))
    if not visits_clock:
        st.warning('The pit/VSC exploration files in docs/pit-vsc-exploration are needed for this view.')
        return
    flagged = sum(v['whole'] for v in visits_clock)
    overlapping = [v for v in visits_clock if v['overlap'] > 0]
    st.write(f'Of the {len(visits_clock)} pit visits shown, {flagged} have a VSC flag on the entry or exit lap, '
             f'but {len(overlapping)} overlap a VSC in the recorded timestamps.')
    n = laps.Driver.nunique()
    st.iframe(replay.html(laps, 'pitclock', mode, 200+48*n), height=210+48*n)
    st.caption('Each bar is a pit visit from pit-lane entry to exit on the session clock, set against the deployed and ending phases '
               'of each VSC. A visit within 1 second of a boundary is marked as a near-boundary case; that rule is a caution, not a '
               'measured accuracy. Pit-lane time is the whole trip through the pit lane, not the stationary stop or the time lost.')
    st.markdown('##### Pit visits and the VSC clock')
    st.dataframe(pit_clock_table(visits_clock, laps.drop_duplicates('Driver').set_index('Driver').Team),
                 hide_index=True, width='stretch')


def event_slide() -> None:
    vsc = laps.loc[laps.HasVSC, 'LapNumber']
    st.write(f'VSC periods affected laps {lap_ranges(vsc)}. These laps are left out of pace comparisons but belong in the event '
             'explanation, so every non-pit affected lap is kept here.' if len(vsc) else 'No VSC laps for the selected teams.')
    st.iframe(replay.html(laps, 'event', mode, 800), height=810)
    st.caption('Points sit at observed lap completions on the session clock, with no interpolation between laps. The interval is '
               'the seconds behind the first car of the whole field to complete that lap, a same-lap comparison and not a live gap. '
               'Changes across these windows include pit activity and other racing, so they do not isolate the effect of the VSC.')


def positions_slide() -> None:
    st.write('Extra context: where each driver ran lap by lap, with the pit stops marked.')
    st.iframe(replay.html(laps, 'positions', mode, 420), height=430)
    st.caption('Positions are recorded at the end of each lap; the lines join those points and the cars only move along the lap '
               'axis. Dots mark the lap each driver entered the pits. Team-mates share a colour, one solid and one dashed.')


SLIDES = {'1. Which tyre sequences did the drivers use?': overview_slide,
          '2. How do lap times and consistency compare in normal racing?': pace_slide,
          '3. How does lap time vary with tyre age?': tyre_slide,
          '4. Which pit visits overlap a VSC?': pit_slide,
          '5. What do the laps around each VSC show?': event_slide,
          'Extra: positions through the race': positions_slide}


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
