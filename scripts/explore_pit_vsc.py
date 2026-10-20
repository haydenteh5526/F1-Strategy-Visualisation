"""Reproduce pit/VSC exploration offline from the retained Austria 2026 snapshot."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT/'data/raw/austria-2026'
PREPARED = ROOT/'data/processed/austria-2026'
REPORT = ROOT/'docs/pit-vsc-exploration'
FIGURES = ROOT/'figures/austria-2026/pit-vsc'
ORDER = ['HAD', 'VER', 'ANT', 'RUS', 'HAM', 'LEC']
COLORS = dict(zip(ORDER, ['#276bb0', '#276bb0', '#00866b', '#00866b', '#c84d20', '#c84d20']))
MARKERS = dict(zip(ORDER, ['o', '^', 'o', '^', 'o', '^']))
GAP = 'GapToEarliestLapCompletionSeconds'


def overlap_seconds(start, end, window_start, window_end):
    """Half-open intervals: touching a boundary alone is not an overlap."""
    return max(0.0, min(end, window_end)-max(start, window_start))


def vsc_windows(status):
    """Keep deployed (6) and ending (7) separate; end the restriction at green (1)."""
    times = pd.to_timedelta(status.Time, errors='raise').dt.total_seconds()
    if not np.isfinite(times).all() or times.diff().dropna().le(0).any():
        raise ValueError('Track-status timestamps must be finite and strictly increasing')
    windows, active = [], None
    for time, code in zip(times, status.Status.astype(str)):
        if code == '6':
            if active is not None:
                raise ValueError('Repeated deployment before the previous VSC ended')
            active = {'event': f'VSC {len(windows)+1}', 'start_seconds': float(time)}
        elif code == '7':
            if active is None or 'ending_seconds' in active:
                raise ValueError('VSC ending without one preceding deployment')
            active['ending_seconds'] = float(time)
        elif active is not None:
            if code != '1' or 'ending_seconds' not in active:
                raise ValueError('Expected ending then green after VSC deployment')
            active['clear_seconds'] = float(time)
            active['deployed_seconds'] = round(active['ending_seconds']-active['start_seconds'], 6)
            active['restriction_seconds'] = round(time-active['start_seconds'], 6)
            windows.append(active)
            active = None
    if active is not None:
        raise ValueError('Unclosed VSC window: a green timestamp is required')
    if not windows:
        raise ValueError('No VSC events in this snapshot')
    return windows


def align_messages(windows, messages):
    """Pair transitions by order; use UTC only as a second-resolution cross-check."""
    matched, offsets = [], []
    for label, column in [('VSC DEPLOYED', 'start_seconds'), ('VSC ENDING', 'ending_seconds')]:
        rows = messages.loc[messages.Message.eq(label)].copy()
        dates = pd.to_datetime(rows.Time, utc=True, errors='raise')
        if len(rows) != len(windows) or dates.isna().any() or not dates.is_monotonic_increasing:
            raise ValueError('Race-control transition count or order does not match track status')
        for event, row, timestamp in zip(windows, rows.itertuples(), dates):
            offset = timestamp.value/1e9-event[column]
            offsets.append(offset)
            matched.append({'event': event['event'], 'transition': label,
                            'session_seconds': event[column], 'message_utc': timestamp.isoformat(),
                            'message_lap': int(row.Lap), 'offset': offset})
    median = float(np.median(offsets))
    for row in matched:
        row['residual_seconds'] = round(row.pop('offset')-median, 6)
    residual = max(abs(row['residual_seconds']) for row in matched)
    if residual > 1:
        raise ValueError('Race-control UTC and track-status clocks disagree by more than one second')
    return {'method': 'Ordered DEPLOYED/ENDING pairs; median UTC-minus-session offset. '
                      'This is an approximate message-clock check, not independent timing validation.',
            'maximum_residual_seconds': residual,
            'offset_spread_seconds': round(max(offsets)-min(offsets), 6), 'transitions': matched}


def status_at(time, status):
    times = pd.to_timedelta(status.Time).dt.total_seconds()
    previous = status.loc[times.le(time)]
    if previous.empty:
        raise ValueError('Missing track status before a pit timestamp')
    return str(previous.iloc[-1].Status)


def lap_time_plot_rows(laps, event):
    """Retain normal, VSC and other affected non-pit laps in a stated time window."""
    return laps.loc[~(laps.IsFirstLap | laps.IsPitInLap | laps.IsPitOutLap)
                    & laps.TimeSeconds.between(event['start_seconds']-90, event['clear_seconds']+90)]


def analyse(laps, visits, status, messages):
    """Return reproducible observations, not estimated causal stop gains."""
    if laps.duplicated(['Driver', 'LapNumber']).any():
        raise ValueError('Duplicate driver-lap keys')
    for column in ['LapStartTimeSeconds', 'TimeSeconds', 'LapNumber', 'Position', GAP]:
        if not np.isfinite(laps[column]).all():
            raise ValueError(f'Missing/non-finite {column}')
    if laps.TimeSeconds.le(laps.LapStartTimeSeconds).any():
        raise ValueError('Nonpositive lap timestamp interval')
    if not np.isfinite(visits[['EntrySeconds', 'ExitSeconds']]).all().all() or visits.ExitSeconds.le(visits.EntrySeconds).any():
        raise ValueError('Invalid pit entry/exit timestamps')
    windows = vsc_windows(status)
    alignment = align_messages(windows, messages)
    lap_coverage = pd.Series(False, index=laps.index)
    comparisons = []
    by_key = laps.set_index(['Driver', 'LapNumber'])
    for event in windows:
        start, clear = event['start_seconds'], event['clear_seconds']
        hit = laps.LapStartTimeSeconds.lt(clear) & laps.TimeSeconds.gt(start)
        lap_coverage |= hit
        event['affected_laps_by_driver'] = {driver: [int(n) for n in group.LapNumber]
                                          for driver, group in laps.loc[hit].groupby('Driver')}
        plotted = lap_time_plot_rows(laps, event)
        event['nonpit_plot_samples'] = {
            driver: {'vsc': int(group.HasVSC.sum()), 'eligible_normal_pace': int(group.EligibleForPace.sum()),
                     'other': int((~group.HasVSC & ~group.EligibleForPace).sum())}
            for driver, group in plotted.groupby('Driver')}
        latest_before = laps.loc[laps.TimeSeconds.le(start)].groupby('Driver').LapNumber.max()
        earliest_after = laps.loc[laps.LapStartTimeSeconds.ge(clear)].groupby('Driver').LapNumber.min()
        if len(latest_before) != laps.Driver.nunique() or len(earliest_after) != laps.Driver.nunique():
            raise ValueError('Event lacks before/after coverage for every driver')
        # Use a common completed lap on each side; never mix drivers' different lap numbers.
        before, after = int(latest_before.min()), int(earliest_after.max())
        event['comparison_before_lap'], event['comparison_after_lap'] = before, after
        for driver in sorted(laps.Driver.unique()):
            a, b = by_key.loc[(driver, before)], by_key.loc[(driver, after)]
            if a.TimeSeconds > start or b.LapStartTimeSeconds < clear:
                raise ValueError('Comparison laps cross the event boundaries')
            comparisons.append({'Event': event['event'], 'Driver': driver,
                                'BeforeLap': before, 'AfterLap': after,
                                'BeforePosition': int(a.Position), 'AfterPosition': int(b.Position),
                                'BeforeIntervalSeconds': round(a[GAP], 6),
                                'AfterIntervalSeconds': round(b[GAP], 6),
                                'IntervalChangeSeconds': round(b[GAP]-a[GAP], 6)})
    if not lap_coverage.equals(laps.HasVSC):
        raise ValueError('Timestamp-overlap VSC coverage disagrees with the prepared lap flags')

    pit_rows = []
    boundaries = [e[key] for e in windows for key in ['start_seconds', 'ending_seconds', 'clear_seconds']]
    for row in visits.sort_values(['EntrySeconds', 'Driver']).itertuples():
        before_lap, after_lap = int(row.EntryLap)-1, int(row.ExitLap)
        if before_lap < 1:
            raise ValueError('Pit comparison needs a completed pre-entry lap')
        a, b = by_key.loc[(row.Driver, before_lap)], by_key.loc[(row.Driver, after_lap)]
        overlaps = {event['event']: overlap_seconds(row.EntrySeconds, row.ExitSeconds,
                    event['start_seconds'], event['clear_seconds']) for event in windows}
        overlaps = {event: round(value, 6) for event, value in overlaps.items() if value > 0}
        separation = min(abs(t-boundary) for t in [row.EntrySeconds, row.ExitSeconds] for boundary in boundaries)
        pit_rows.append({'Driver': row.Driver, 'Team': row.Team,
                        'EntryLap': int(row.EntryLap), 'ExitLap': int(row.ExitLap),
                        'EntrySeconds': row.EntrySeconds, 'ExitSeconds': row.ExitSeconds,
                        'PitLaneElapsedSeconds': row.PitLaneElapsedSeconds,
                        'EntryStatusCode': status_at(row.EntrySeconds, status),
                        'ExitStatusCode': status_at(row.ExitSeconds, status),
                        'WholeLapHasVSC': bool(any(c in str(row.EntryTrackStatus)+str(row.ExitTrackStatus) for c in '67')),
                        'TimestampOverlapsVSC': bool(overlaps), 'Events': '|'.join(overlaps),
                        'VSCOverlapSeconds': round(sum(overlaps.values()), 6),
                        'NearestVSCBoundarySeconds': round(separation, 6), 'WithinOneSecondOfBoundary': separation <= 1,
                        'BeforeLap': before_lap, 'AfterLap': after_lap,
                        'BeforePosition': int(a.Position), 'AfterPosition': int(b.Position),
                        'BeforeIntervalSeconds': round(a[GAP], 6), 'AfterIntervalSeconds': round(b[GAP], 6),
                        'IntervalChangeSeconds': round(b[GAP]-a[GAP], 6)})
    pits, events = pd.DataFrame(pit_rows), pd.DataFrame(comparisons)
    nonpit = lap_coverage & ~(laps.IsFirstLap | laps.IsPitInLap | laps.IsPitOutLap)
    summary = {'event': 'Austria 2026', 'selected_laps': len(laps), 'pit_visits': len(pits),
               'vsc_affected_laps': int(lap_coverage.sum()), 'nonpit_vsc_laps': int(nonpit.sum()),
               'nonpit_vsc_time_range_seconds': [float(laps.loc[nonpit].LapTimeSeconds.min()),
                                                 float(laps.loc[nonpit].LapTimeSeconds.max())],
               'whole_lap_vsc_flagged_visits': int(pits.WholeLapHasVSC.sum()),
               'timestamp_overlapping_visits': int(pits.TimestampOverlapsVSC.sum()),
               'boundary_sensitive_visits': int(pits.WithinOneSecondOfBoundary.sum()),
               'windows': windows, 'race_control_alignment': alignment,
               'scope': 'Descriptive timestamp overlaps and same-completed-lap intervals. '
                        'No instantaneous gaps, stationary service times or causal pit-stop gains.',
               'boundary_convention': '[start, end); code 7 remains restricted until code 1. '
                                      'Within 1 second of a transition is flagged for caution; this is a sensitivity rule, '
                                      'not a measured timing error bound.'}
    return summary, pits, events


def decorate_window(ax, event, origin=None):
    origin = event['start_seconds'] if origin is None else origin
    ax.axvspan(event['start_seconds']-origin, event['ending_seconds']-origin, color='#a2a7af', alpha=.24)
    ax.axvspan(event['ending_seconds']-origin, event['clear_seconds']-origin, color='#eda100', alpha=.22)
    for key in ['start_seconds', 'ending_seconds', 'clear_seconds']:
        ax.axvline(event[key]-origin, color='#657080', linewidth=.7, linestyle='--')


def finish_figure(fig, name, footer):
    fig.text(.02, .015, footer+'\nSource: retained FastF1 3.8.3 Austria 2026 snapshot; see docs/pit-vsc-exploration/.',
             fontsize=8, color='#414955', va='bottom')
    fig.savefig(FIGURES/f'{name}.png', dpi=160, facecolor='white')
    plt.close(fig)


def plot_figures(laps, visits, summary):
    """Three complementary views; VSC-affected observations are retained."""
    FIGURES.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({'font.size': 10, 'axes.spines.top': False, 'axes.spines.right': False})
    windows = summary['windows']
    fig, axes = plt.subplots(1, len(windows), figsize=(13, 5), squeeze=False)
    for ax, event in zip(axes[0], windows):
        start, clear = event['start_seconds'], event['clear_seconds']
        decorate_window(ax, event)
        for pit in visits.itertuples():
            if pit.ExitSeconds >= start-90 and pit.EntrySeconds <= clear+90:
                y = ORDER.index(pit.Driver)
                ax.plot([pit.EntrySeconds-start, pit.ExitSeconds-start], [y, y], color=COLORS[pit.Driver], lw=7,
                        solid_capstyle='butt')
                ax.scatter([pit.EntrySeconds-start, pit.ExitSeconds-start], [y, y], c=COLORS[pit.Driver], s=28, zorder=4)
                ax.annotate(f'entry lap {int(pit.EntryLap)}', (pit.ExitSeconds-start, y), xytext=(5, -15),
                            textcoords='offset points', fontsize=8)
        ax.set(yticks=range(len(ORDER)), yticklabels=ORDER, ylim=(5.6, -.6),
               xlim=(-90, clear-start+90), xlabel='Seconds from recorded VSC deployment',
               title=f"{event['event']}: pit-lane entry to exit")
        ax.grid(axis='y', alpha=.18)
    fig.suptitle('Selected drivers: Hamilton’s pit visit overlaps VSC 1', fontsize=14)
    fig.subplots_adjust(bottom=.22, top=.83, wspace=.16)
    finish_figure(fig, 'pit-status-windows',
                  'Grey = deployed; amber = ending until green. ANT exits 0.132 s before VSC 1: treat this near-boundary ordering cautiously.\n'
                  'Pit-lane spans include driving and service; they do not measure stationary time or causal time lost.')

    legend = [Line2D([], [], color=COLORS[d], marker=MARKERS[d], linestyle='None', label=d) for d in ORDER]
    fig, axes = plt.subplots(1, len(windows), figsize=(13, 5.5), sharey=True, squeeze=False)
    for ax, event in zip(axes[0], windows):
        start, clear = event['start_seconds'], event['clear_seconds']
        decorate_window(ax, event)
        full = lap_time_plot_rows(laps, event)
        for driver in ORDER:
            rows = full.loc[full.Driver.eq(driver)]
            ax.scatter(rows.TimeSeconds-start, rows.LapTimeSeconds, c=COLORS[driver], marker=MARKERS[driver],
                       s=38, edgecolors='white', linewidths=.4, zorder=3)
        ax.set(xlim=(-90, clear-start+90), ylim=(69, summary['nonpit_vsc_time_range_seconds'][1]+5),
               xlabel='Lap completion: seconds from recorded VSC deployment', title=event['event'])
        ax.grid(axis='y', alpha=.2)
    axes[0, 0].set_ylabel('Lap duration (s)')
    fig.legend(handles=legend, loc='upper center', ncol=6, bbox_to_anchor=(.5, .91))
    low, high = summary['nonpit_vsc_time_range_seconds']
    fig.suptitle(f'VSC-affected non-pit laps range from {low:.3f} to {high:.3f} seconds', fontsize=14)
    fig.subplots_adjust(bottom=.2, top=.8, wspace=.12)
    finish_figure(fig, 'vsc-lap-times',
                  'Lap 1 and pit in/out laps are excluded; VSC, ending and yellow-affected laps remain. Grey/amber mark status-clock windows.\n'
                  'A lap ending after a shaded window may still overlap it. Fuel, traffic and other conditions also affect lap duration.')

    fig, axes = plt.subplots(2, len(windows), figsize=(13, 8), squeeze=False)
    position_max = int(max(laps.loc[laps.TimeSeconds.between(e['start_seconds']-150, e['clear_seconds']+150),
                                   'Position'].max() for e in windows))
    for col, event in enumerate(windows):
        start, clear = event['start_seconds'], event['clear_seconds']
        for row, field in enumerate(['Position', GAP]):
            ax = axes[row, col]
            decorate_window(ax, event)
            for driver in ORDER:
                rows = laps.loc[laps.Driver.eq(driver) & laps.TimeSeconds.between(start-150, clear+150)]
                ax.scatter(rows.TimeSeconds-start, rows[field], c=COLORS[driver], marker=MARKERS[driver],
                           s=35, edgecolors='white', linewidths=.4, zorder=3)
            ax.set(xlim=(-150, clear-start+150), xlabel='Lap completion: seconds from recorded VSC deployment')
            ax.grid(axis='y', alpha=.2)
            if row == 0:
                ax.set(title=f"{event['event']} (table compares lap {event['comparison_before_lap']} to {event['comparison_after_lap']})",
                       ylim=(position_max+.5, .5), yticks=range(1, position_max+1))
            else:
                ax.set_ylim(bottom=-.5)
    axes[0, 0].set_ylabel('Position at lap completion')
    axes[1, 0].set_ylabel('Same-lap completion interval\nto first field finisher (s)')
    fig.legend(handles=legend, loc='upper center', ncol=6, bbox_to_anchor=(.5, .95))
    fig.suptitle('Positions and lap-boundary intervals around the two VSC windows', fontsize=14)
    fig.subplots_adjust(bottom=.16, top=.87, hspace=.37, wspace=.18)
    finish_figure(fig, 'positions-and-intervals',
                  'Each point is a measured lap boundary, not a live position or gap; points are deliberately not interpolated.\n'
                  'The first field finisher can change between laps. Before/after changes are descriptive and do not isolate the effect of a pit stop.')


def build_report():
    audit = json.loads((PREPARED/'audit_summary.json').read_text())
    if hashlib.sha256((RAW/'laps.csv').read_bytes()).hexdigest() != audit['raw_laps_sha256']:
        raise ValueError('Raw laps do not match the committed audit')
    laps = pd.read_csv(PREPARED/'selected_laps.csv', dtype={'TrackStatus': str})
    visits = pd.read_csv(PREPARED/'pit_visits.csv', dtype={'EntryTrackStatus': str, 'ExitTrackStatus': str})
    status = pd.read_csv(RAW/'track_status.csv', dtype={'Status': str})
    messages = pd.read_csv(RAW/'race_control_messages.csv')
    summary, pits, events = analyse(laps, visits, status, messages)
    inputs = [RAW/'laps.csv', RAW/'track_status.csv', RAW/'race_control_messages.csv',
              PREPARED/'selected_laps.csv', PREPARED/'pit_visits.csv']
    summary['input_hash_convention'] = 'Raw hashes use exact bytes; prepared CSV hashes normalize CRLF to LF for Git checkouts.'
    summary['input_sha256'] = {
        p.relative_to(ROOT).as_posix(): hashlib.sha256(
            p.read_bytes().replace(b'\r\n', b'\n') if p.parent == PREPARED else p.read_bytes()).hexdigest()
        for p in inputs}
    return laps, visits, summary, pits, events


def main():
    laps, visits, summary, pits, events = build_report()
    REPORT.mkdir(parents=True, exist_ok=True)
    (REPORT/'summary.json').write_text(json.dumps(summary, indent=2, allow_nan=False)+'\n')
    pits.to_csv(REPORT/'pit_event_comparisons.csv', index=False, float_format='%.6f')
    events.to_csv(REPORT/'event_lap_comparisons.csv', index=False, float_format='%.6f')
    plot_figures(laps, visits, summary)
    print(json.dumps({k: summary[k] for k in ['pit_visits', 'vsc_affected_laps', 'whole_lap_vsc_flagged_visits',
                                            'timestamp_overlapping_visits', 'boundary_sensitive_visits']}, indent=2))


if __name__ == '__main__':
    main()
