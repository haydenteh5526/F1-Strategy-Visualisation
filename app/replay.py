"""Animated race replays: each driver's car drives its own data on the real lap clock (compressed)."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

import charts

DURATION_MS = 9000  # Whole race, compressed.
EXPLORATION = Path(__file__).resolve().parents[1]/'docs/pit-vsc-exploration'
# Recorded deployment, ending and all-clear times of each VSC, from the committed pit/VSC exploration.
VSC_CLOCK = EXPLORATION/'summary.json'
PIT_COMPARISONS = EXPLORATION/'pit_event_comparisons.csv'


def vsc_clock(path: Path = VSC_CLOCK) -> list[dict]:
    """Session-clock seconds for each VSC and its comparison laps; empty if the summary is missing, so nothing is guessed."""
    if not path.exists():
        return []
    return [{'name': w['event'], 'start': w['start_seconds'], 'ending': w['ending_seconds'], 'clear': w['clear_seconds'],
             'before': w['comparison_before_lap'], 'after': w['comparison_after_lap']}
            for w in json.loads(path.read_text(encoding='utf-8'))['windows']]


def pit_data(drivers: list[str], path: Path = PIT_COMPARISONS) -> list[dict]:
    """Every pit visit with its recorded span and how it relates to the VSC clock, for the selected drivers."""
    if not path.exists():
        return []
    table = pd.read_csv(path)
    table = table.loc[table.Driver.isin(drivers)]
    return [{'driver': r.Driver, 'entryLap': int(r.EntryLap), 'entry': float(r.EntrySeconds), 'exit': float(r.ExitSeconds),
             'elapsed': float(r.PitLaneElapsedSeconds), 'whole': bool(r.WholeLapHasVSC), 'overlap': float(r.VSCOverlapSeconds),
             'near': bool(r.WithinOneSecondOfBoundary), 'nearest': float(r.NearestVSCBoundarySeconds)}
            for r in table.itertuples()]


def event_data(laps: pd.DataFrame, order: list[str], clock: list[dict]) -> list[dict]:
    """Lap completions around each VSC, on the session clock (seconds from deployment), plus drivers lacking a non-pit sample."""
    events = []
    for c in clock:
        window = laps.loc[laps.LapNumber.between(c['before'], c['after'])]
        series, notes = [], []
        for driver in order:
            rows = window.loc[window.Driver.eq(driver)].sort_values('LapNumber')
            series.append({'code': driver, 'points': [
                {'lap': int(r.LapNumber), 'x': float(r.TimeSeconds)-c['start'], 'pos': int(r.Position),
                 'gap': float(r.GapToEarliestLapCompletionSeconds),
                 'time': None if (r.IsFirstLap or r.IsPitInLap or r.IsPitOutLap) else float(r.LapTimeSeconds),
                 'vscLap': bool(r.HasVSC)} for r in rows.itertuples()]})
            affected = rows.loc[rows.HasVSC]
            if len(affected) and affected[~(affected.IsFirstLap | affected.IsPitInLap | affected.IsPitOutLap)].empty:
                notes.append(f"{driver} has no non-pit lap-time observation in {c['name']}: the laps affected are pit laps.")
        events.append({**c, 'series': series, 'notes': notes,
                       'ending_x': c['ending']-c['start'], 'clear_x': c['clear']-c['start']})
    return events


def race_data(laps: pd.DataFrame, mode: str) -> dict:
    """Per-driver lap clock from the prepared laps: each lap starts when the previous one ends."""
    order = charts.driver_order(laps)
    palette = dict(zip(charts.TEAMS, charts.TEAM_COLORS[mode]))
    drivers = []
    for i, driver in enumerate(order):
        rows = laps.loc[laps.Driver.eq(driver)].sort_values('LapNumber')
        starts = rows.TimeSeconds.shift(1).fillna(rows.LapStartTimeSeconds)
        drivers.append({
            'code': driver, 'team': rows.Team.iloc[0], 'color': palette[rows.Team.iloc[0]], 'dashed': i % 2 == 1,
            'laps': [{'lap': int(r.LapNumber), 'start': float(s), 'end': float(r.TimeSeconds), 'pos': int(r.Position),
                      'compound': r.Compound, 'stint': int(r.Stint), 'pitIn': bool(r.IsPitInLap), 'fresh': bool(r.FreshTyre),
                      'time': float(r.LapTimeSeconds), 'age': int(r.TyreLife), 'normal': bool(r.EligibleForPace)}
                     for r, s in zip(rows.itertuples(), starts)]})
    bands = charts.vsc_bands(laps)
    summary = charts.pace_summary(laps.loc[laps.EligibleForPace]).set_index('Driver')
    pace = [{'code': d['code'], 'color': d['color'], 'dashed': d['dashed'], 'low': float(summary.Low[d['code']]),
             'high': float(summary.High[d['code']]), 'typical': float(summary.Typical[d['code']]),
             'n': int(summary.Laps[d['code']])} for d in drivers]
    clock = vsc_clock()
    t0 = min(d['laps'][0]['start'] for d in drivers)
    return {'drivers': drivers, 'pace': pace, 'vsc': [[int(b.Start)-1, int(b.End)] for b in bands.itertuples()],
            'clock': clock, 'events': event_data(laps, order, clock), 'pits': pit_data(order),
            'finish': int(laps.LapNumber.max()), 'duration': DURATION_MS,
            't0': t0, 't1': max(d['laps'][-1]['end'] for d in drivers),
            'tyres': dict(zip(charts.COMPOUNDS, charts.COMPOUND_COLORS)),
            'ink': charts.INK[mode], 'muted': '#898781', 'grid': '#2c2c38' if mode == 'dark' else '#e6eaf1',
            'surface': charts.SURFACE[mode], 'vscColor': '#eda100'}


def html(laps: pd.DataFrame, kind: str, mode: str, height: int) -> str:
    """kind is 'timeline', 'pace', 'tyres', 'pitclock', 'event' or 'positions'."""
    return (TEMPLATE.replace('%DATA%', json.dumps(race_data(laps, mode)))
            .replace('%KIND%', kind).replace('%HEIGHT%', str(height))
            .replace('%PANELS%', 'panels' if kind in ('pitclock', 'event') else ''))


TEMPLATE = r'''<!doctype html><html><head><meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Titillium+Web:wght@400;700;900&display=swap" rel="stylesheet">
<style>
  html, body { margin: 0; background: transparent; font-family: 'Titillium Web', system-ui, sans-serif; }
  #wrap { position: relative; }
  svg { display: block; width: 100%; height: %HEIGHT%px; }
  #replay { position: absolute; left: 6px; top: 4px; border: none; border-radius: 16px; padding: 4px 12px;
    background: #e10600; color: #fff; font: 700 12px 'Titillium Web', sans-serif; letter-spacing: .08em; cursor: pointer; }
  #replay:hover { box-shadow: 0 0 12px #e10600; }
  body.panels #replay { top: auto; left: auto; bottom: 4px; right: 6px; }
  .label { font-size: 12px; font-weight: 700; }
  .axis { font-size: 11px; }
  .counter { font-size: 18px; font-weight: 900; font-style: italic; letter-spacing: .04em; }
</style></head>
<body class="%PANELS%"><div id="wrap"><svg id="chart" role="img" aria-label="Race replay"></svg><button id="replay" type="button">&#8635; REPLAY</button></div>
<script>
const D = %DATA%, KIND = '%KIND%', H = %HEIGHT%;
const svg = document.getElementById('chart');
const CAR = '<symbol id="car" viewBox="0 0 200 50"><path d="M8 31 L38 27 L66 19 L104 16 L118 9 L132 9 L136 17 L168 21 L186 27 L190 32 L8 34 Z" fill="currentColor"/>'
  + '<path d="M100 16 Q112 6 126 11" stroke="#f0efec" stroke-width="5" fill="none"/><rect x="4" y="8" width="18" height="5" fill="#f0efec"/>'
  + '<rect x="12" y="10" width="4" height="20" fill="#f0efec"/><path d="M176 33 L198 33 L198 38 L174 38 Z" fill="#f0efec"/>'
  + '<circle cx="40" cy="36" r="12" fill="#0b0b0b"/><circle cx="160" cy="37" r="11" fill="#0b0b0b"/></symbol>';
const esc = s => String(s).replace(/[&<>"]/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;'}[c]));

function progress(d, t) {
  const L = d.laps;
  if (t <= L[0].start) return 0;
  for (const l of L) if (t < l.end) return l.lap - 1 + (t - l.start) / (l.end - l.start);
  return L[L.length - 1].lap;
}
function posAt(d, p) {  // Positions are recorded at lap completion: hold the last recorded one, never blend between laps.
  const L = d.laps, done = Math.floor(p);
  return L[Math.min(Math.max(done, 1), L.length) - 1].pos;
}
function car(x, y, color, title) {
  return `<g transform="translate(${x - 58},${y - 8})" style="color:${color}"><title>${esc(title)}</title>`
       + `<use href="#car" width="62" height="16"/></g>`;
}

function lapFrame(t) {
  const W = svg.clientWidth || 900, finish = D.finish;
  const M = KIND === 'timeline' ? {l: 78, r: 24, t: 34, b: 34} : {l: 48, r: 54, t: 34, b: 34};
  const xs = lap => M.l + lap / (finish + .6) * (W - M.l - M.r);
  const plotB = H - M.b;
  const ps = D.drivers.map(d => progress(d, t));
  const leaderLap = Math.min(finish, Math.floor(Math.max(...ps)) + 1);
  let s = `<defs>${CAR}</defs>`;
  for (let lap = 0; lap <= finish; lap += 5)
    s += `<line x1="${xs(lap)}" x2="${xs(lap)}" y1="${M.t}" y2="${plotB}" stroke="${D.grid}"/>`
       + `<text class="axis" x="${xs(lap)}" y="${plotB + 16}" fill="${D.ink}" text-anchor="middle">${lap}</text>`;
  s += `<text class="axis" x="${(M.l + W - M.r) / 2}" y="${H - 2}" fill="${D.ink}" text-anchor="middle" font-weight="700">Lap</text>`;
  for (const [a, b] of D.vsc)
    s += `<rect x="${xs(a)}" y="${M.t}" width="${xs(b) - xs(a)}" height="${plotB - M.t}" fill="${D.muted}" opacity=".16"/>`
       + `<text class="axis" x="${xs(a) + 3}" y="${M.t + 12}" fill="${D.muted}">VSC</text>`;
  s += `<line x1="${xs(finish)}" x2="${xs(finish)}" y1="${M.t}" y2="${plotB}" stroke="${D.ink}" stroke-dasharray="3 3" opacity=".6"/>`
     + `<text class="axis" x="${xs(finish) - 4}" y="${plotB - 6}" fill="${D.ink}" text-anchor="end" font-weight="700">FINISH</text>`
     + `<text class="counter" x="${W - M.r}" y="20" fill="${D.ink}" text-anchor="end">LAP ${leaderLap} / ${finish}</text>`;

  if (KIND === 'timeline') {
    const row = (plotB - M.t) / D.drivers.length;
    D.drivers.forEach((d, i) => {
      const y = M.t + row * (i + .5), p = ps[i];
      s += `<rect x="${M.l - 26}" y="${y - 8}" width="8" height="16" rx="2" fill="${d.color}"/>`
         + `<text class="label" x="${M.l - 32}" y="${y + 4}" fill="${D.ink}" text-anchor="end">${d.code}</text>`;
      const stints = {};
      for (const l of d.laps) (stints[l.stint] = stints[l.stint] || []).push(l);
      for (const laps of Object.values(stints)) {
        const first = laps[0].lap, last = laps[laps.length - 1].lap;
        if (p <= first - 1) continue;
        const x0 = xs(first - 1 + .2), x1 = xs(Math.min(p, last - .2));
        const c = D.tyres[laps[0].compound], name = laps[0].compound[0] + laps[0].compound.slice(1).toLowerCase();
        if (x1 > x0) s += `<rect x="${x0}" y="${y - 8}" width="${x1 - x0}" height="16" rx="6" fill="${c}">`
          + `<title>${d.code} · ${name}${laps[0].fresh ? '' : ' (used)'} · laps ${first}–${last}</title></rect>`;
        if (p > first - 1 + .5)
          s += `<circle cx="${xs(first - 1 + 1.3)}" cy="${y}" r="8" fill="${D.surface}" stroke="${c}" stroke-width="2.5"/>`
             + `<text x="${xs(first - 1 + 1.3)}" y="${y + 3.5}" fill="${D.ink}" font-size="10" font-weight="700" text-anchor="middle">${laps[0].compound[0]}</text>`;
      }
      if (p < finish) s += car(xs(p), y - 16, d.color, `${d.code} · lap ${Math.ceil(p) || 1}`);
    });
  } else if (KIND === 'positions') {
    const maxPos = Math.max(...D.drivers.flatMap(d => d.laps.map(l => l.pos)));
    const ys = pos => M.t + (pos - 1) / Math.max(1, maxPos - 1) * (plotB - M.t);
    for (let pos = 1; pos <= maxPos; pos++)
      s += `<text class="axis" x="${M.l - 8}" y="${ys(pos) + 4}" fill="${D.ink}" text-anchor="end">${pos}</text>`;
    s += `<text class="axis" x="12" y="${(M.t + plotB) / 2}" fill="${D.ink}" font-weight="700" transform="rotate(-90 12 ${(M.t + plotB) / 2})" text-anchor="middle">Position</text>`;
    D.drivers.forEach((d, i) => {
      const p = ps[i], pts = [[0, d.laps[0].pos]];
      for (const l of d.laps) if (l.lap <= p) pts.push([l.lap, l.pos]);
      pts.push([p, posAt(d, p)]);
      s += `<polyline points="${pts.map(([l, q]) => `${xs(l)},${ys(q)}`).join(' ')}" fill="none" stroke="${d.color}" stroke-width="2.5"`
         + `${d.dashed ? ' stroke-dasharray="6 4"' : ''}/>`;
      for (const l of d.laps) if (l.pitIn && l.lap <= p)
        s += `<circle cx="${xs(l.lap)}" cy="${ys(l.pos)}" r="5" fill="${d.color}" stroke="${D.surface}" stroke-width="2"><title>${d.code} pit stop, lap ${l.lap}</title></circle>`;
      const [x, y] = [xs(p), ys(posAt(d, p))];
      if (p < finish) s += car(x, y, d.color, `${d.code} · P${Math.round(posAt(d, p))}`)
        + `<text class="label" x="${x + 6}" y="${y + 4}" fill="${D.ink}">${d.code}</text>`;
      else s += `<text class="label" x="${xs(finish) + 6}" y="${y + 4}" fill="${D.ink}">${d.code}</text>`;
    });
  }
  svg.innerHTML = s;
}

function mark(x, y, color, triangle, title) {  // Team colour plus a shape per team-mate keeps drivers apart.
  const shape = triangle ? `<path d="M${x} ${y - 6} L${x + 5.5} ${y + 4} L${x - 5.5} ${y + 4} Z"`
                         : `<circle cx="${x}" cy="${y}" r="4.6"`;
  return `${shape} fill="${color}" stroke="${D.surface}" stroke-width="1"><title>${esc(title)}</title>${triangle ? '</path>' : '</circle>'}`;
}
function bigMark(x, y, color, triangle, title) {
  const shape = triangle ? `<path d="M${x} ${y - 10} L${x + 9.5} ${y + 7} L${x - 9.5} ${y + 7} Z"` : `<circle cx="${x}" cy="${y}" r="8"`;
  return `${shape} fill="${color}" stroke="${D.surface}" stroke-width="2"><title>${esc(title)}</title>${triangle ? '</path>' : '</circle>'}`;
}
function legend(x, y) {
  return D.drivers.map((d, i) => mark(x + i * 70, y - 4, d.color, d.dashed, d.code)
    + `<text class="label" x="${x + i * 70 + 10}" y="${y}" fill="${D.ink}">${d.code}</text>`).join('');
}
function yTitle(text, top, bottom) {
  const mid = (top + bottom) / 2;
  return `<text class="axis" x="12" y="${mid}" fill="${D.ink}" font-weight="700" transform="rotate(-90 12 ${mid})" text-anchor="middle">${text}</text>`;
}
function counter(W, right) {
  const ps = D.drivers.map(d => d.p), lap = Math.min(D.finish, Math.floor(Math.max(...ps)) + 1);
  return `<text class="counter" x="${W - right}" y="20" fill="${D.ink}" text-anchor="end">LAP ${lap} / ${D.finish}</text>`;
}

function paceFrame(k) {  // Each car lays down its driver's middle-half bar; the typical-lap dot pops in as it passes.
  const W = svg.clientWidth || 900, M = {l: 78, r: 150, t: 40, b: 40}, plotB = H - M.b, P = D.pace;
  const lo = Math.min(...P.map(q => q.low)) - .3, hi = Math.max(...P.map(q => q.high)) + .3;
  const xs = v => M.l + (v - lo) / (hi - lo) * (W - M.l - M.r), row = (plotB - M.t) / P.length;
  let s = `<defs>${CAR}</defs>`;
  for (let v = Math.ceil(lo * 2) / 2; v <= hi; v += .5)
    s += `<line x1="${xs(v)}" x2="${xs(v)}" y1="${M.t}" y2="${plotB}" stroke="${D.grid}"/>`
       + `<text class="axis" x="${xs(v)}" y="${plotB + 16}" fill="${D.ink}" text-anchor="middle">${v.toFixed(1)}</text>`;
  s += `<text class="axis" x="${(M.l + W - M.r) / 2}" y="${H - 2}" fill="${D.ink}" text-anchor="middle" font-weight="700">Lap time (s)</text>`;
  P.forEach((q, i) => {
    const y = M.t + row * (i + .5), travel = Math.min(1, Math.max(0, k * 1.3 - i * .05));
    const carX = xs(lo) + travel * (xs(q.high) - xs(lo));
    s += mark(M.l - 62, y, q.color, q.dashed, q.code) + `<text class="label" x="${M.l - 10}" y="${y + 4}" fill="${D.ink}" text-anchor="end">${q.code}</text>`;
    if (carX > xs(q.low))
      s += `<rect x="${xs(q.low)}" y="${y - 5}" width="${Math.min(carX, xs(q.high)) - xs(q.low)}" height="10" rx="5" fill="${q.color}" opacity=".4"/>`;
    if (carX >= xs(q.typical))
      s += bigMark(xs(q.typical), y, q.color, q.dashed, `${q.code} typical lap ${q.typical.toFixed(3)} s from ${q.n} laps`);
    s += travel < 1 ? car(carX, y, q.color, q.code)
                    : `<text class="label" x="${xs(q.high) + 10}" y="${y + 4}" fill="${D.ink}">${q.typical.toFixed(2)} s · ${q.n} laps</text>`;
  });
  svg.innerHTML = s;
}

function tyreFrame(t) {  // One panel per driver: the car draws each stint as its tyres age, on the race clock.
  const W = svg.clientWidth || 900, cols = 2, rows = Math.ceil(D.drivers.length / cols), gap = 30;
  const M = {l: 58, r: 26, t: 34, b: 40}, pw = (W - M.l - M.r - gap) / cols, ph = (H - M.t - M.b - gap * (rows - 1)) / rows;
  const normal = D.drivers.map(d => d.laps.filter(l => l.normal)), all = normal.flat();
  const lo = Math.floor(Math.min(...all.map(l => l.time))), hi = Math.ceil(Math.max(...all.map(l => l.time)));
  const maxAge = Math.max(...all.map(l => l.age)) + 2;
  D.drivers.forEach(d => d.p = progress(d, t));
  let s = `<defs>${CAR}</defs>` + counter(W, M.r) + yTitle('Lap time (s)', M.t, H - M.b)
        + `<text class="axis" x="${(M.l + W - M.r) / 2}" y="${H - 2}" fill="${D.ink}" text-anchor="middle" font-weight="700">Tyre age (laps)</text>`;
  D.drivers.forEach((d, i) => {
    const ox = M.l + (i % cols) * (pw + gap), oy = M.t + Math.floor(i / cols) * (ph + gap), top = oy + 20, bottom = oy + ph;
    const xs = a => ox + a / maxAge * pw, ys = v => bottom - (v - lo) / (hi - lo) * (bottom - top);
    s += `<text class="label" x="${ox}" y="${oy + 10}" fill="${D.ink}">${d.code} · ${esc(d.team)} · ${normal[i].length} laps</text>`;
    for (let v = lo; v <= hi; v++)
      s += `<line x1="${ox}" x2="${ox + pw}" y1="${ys(v)}" y2="${ys(v)}" stroke="${D.grid}"/>`
         + (i % cols === 0 ? `<text class="axis" x="${ox - 6}" y="${ys(v) + 4}" fill="${D.ink}" text-anchor="end">${v}</text>` : '');
    if (Math.floor(i / cols) === rows - 1)
      for (let a = 0; a < maxAge; a += 5) s += `<text class="axis" x="${xs(a)}" y="${bottom + 14}" fill="${D.ink}" text-anchor="middle">${a}</text>`;
    const seen = normal[i].filter(l => l.lap <= d.p), stints = {};
    for (const l of seen) (stints[l.stint] = stints[l.stint] || []).push(l);
    for (const [stint, laps] of Object.entries(stints)) {
      const c = D.tyres[laps[0].compound];
      for (const l of laps) s += `<circle cx="${xs(l.age)}" cy="${ys(l.time)}" r="3.2" fill="${c}"><title>${d.code} stint ${stint}, tyre age ${l.age}: ${l.time.toFixed(3)} s</title></circle>`;
      const lastLap = Math.max(...d.laps.filter(l => l.stint == stint).map(l => l.lap)), end = laps[laps.length - 1];
      if (d.p >= lastLap) s += `<text class="label" x="${xs(end.age) + 7}" y="${ys(end.time) + 4 + (Number(stint) % 2 ? 0 : 12)}" fill="${D.ink}">${laps[0].compound[0]} · ${normal[i].filter(l => l.stint == stint).length} laps</text>`;
    }
    const last = seen[seen.length - 1];
    if (last && d.p < D.finish) s += car(xs(last.age) + 4, ys(last.time), d.color, `${d.code} · tyre age ${last.age}`);
  });
  svg.innerHTML = s;
}

const median = a => { const v = [...a].sort((x, y) => x - y), m = v.length >> 1; return v.length % 2 ? v[m] : (v[m - 1] + v[m]) / 2; };
const sweep = t => Math.min(1, Math.max(0, (t - D.t0) / (D.t1 - D.t0)));
const teamOf = code => D.drivers.find(d => d.code === code);
function niceStep(span) { const raw = span / 5, p = 10 ** Math.floor(Math.log10(raw)); return [1, 2, 5, 10].map(m => m * p).find(v => v >= raw); }
function missing(text) { svg.innerHTML = `<text x="20" y="40" fill="${D.ink}" class="label">${esc(text)}</text>`; }
function phases(c, xs, top, bottom, labels) {  // Deployed and ending phases of one VSC, on seconds from deployment.
  const e = c.ending_x, k = c.clear_x;
  let s = `<rect x="${xs(0)}" y="${top}" width="${xs(e) - xs(0)}" height="${bottom - top}" fill="${D.vscColor}" opacity=".16"/>`
        + `<rect x="${xs(e)}" y="${top}" width="${xs(k) - xs(e)}" height="${bottom - top}" fill="${D.vscColor}" opacity=".07"/>`;
  for (const [x, name, dy] of [[0, 'DEPLOYED', 4], [e, 'ENDING', 16], [k, 'CLEAR', 4]]) {
    s += `<line x1="${xs(x)}" x2="${xs(x)}" y1="${top}" y2="${bottom}" stroke="${D.vscColor}" stroke-dasharray="4 3"/>`;
    if (labels) s += `<text class="axis" x="${xs(x) + 3}" y="${top - dy}" fill="${D.vscColor}" font-weight="700">${name}</text>`;
  }
  return s;
}

function badge(v) {  // A stop's relation to the VSC, as words, colour and a symbol.
  if (v.overlap > 0) return {text: `✔ IN THE PIT LANE DURING THE VSC · ${v.overlap.toFixed(1)} s`, fill: '#e10600', ink: '#ffffff'};
  if (v.near) return {text: `⚠ ${v.nearest.toFixed(3)} s FROM THE VSC · TOO CLOSE TO CALL`, fill: D.vscColor, ink: '#15151e'};
  if (v.whole) return {text: 'flagged lap · stop was outside the VSC', fill: '#5a5a64', ink: '#ffffff'};
  return null;
}

function pitFrame(t) {  // Pit-lane spans against the recorded VSC clock; cars drive each span as the clock sweeps.
  const k = sweep(t), W = svg.clientWidth || 900, ev = D.events, n = D.drivers.length;
  if (!ev.length || !D.pits.length) return missing('Needs the pit/VSC exploration files in docs/pit-vsc-exploration (merged in #14).');
  const M = {l: 78, r: 26, t: 52}, gap = 40, row = 30, lo = -100, his = ev.map(e => e.clear_x + 40);
  const spans = his.map(h => h - lo), unit = (W - M.l - M.r - gap * (ev.length - 1)) / spans.reduce((a, b) => a + b, 0);
  const bottom = M.t + row * n;
  let s = `<defs>${CAR}</defs>`;
  D.drivers.forEach((d, i) => {
    const y = M.t + row * (i + .5);
    s += mark(14, y, d.color, d.dashed, d.code) + `<text class="label" x="${M.l - 10}" y="${y + 4}" fill="${D.ink}" text-anchor="end">${d.code}</text>`
       + `<line x1="${M.l}" x2="${W - M.r}" y1="${y}" y2="${y}" stroke="${D.grid}"/>`;
  });
  let ox = M.l;
  ev.forEach((c, j) => {
    const hi = his[j], xs = v => ox + (v - lo) * unit, cx = lo + k * (hi - lo);
    s += `<text class="label" x="${ox}" y="${M.t - 30}" fill="${D.ink}">${c.name} (cars must slow down) · pit-lane entry to exit</text>` + phases(c, xs, M.t, bottom, true);
    for (let v = Math.ceil(lo / 50) * 50; v <= hi; v += 50)
      s += `<text class="axis" x="${xs(v)}" y="${bottom + 16}" fill="${D.ink}" text-anchor="middle">${v}</text>`;
    s += `<text class="axis" x="${ox + (hi - lo) * unit / 2}" y="${bottom + 32}" fill="${D.ink}" text-anchor="middle" font-weight="700">Seconds from VSC deployment</text>`
       + (k < 1 ? `<line x1="${xs(cx)}" x2="${xs(cx)}" y1="${M.t}" y2="${bottom}" stroke="${D.ink}" opacity=".5"/>` : '');
    D.drivers.forEach((d, i) => {  // Say so when a driver made no pit stop here, so an empty row is not read as missing data.
      if (D.pits.some(v => v.driver === d.code && v.exit - c.start >= lo && v.entry - c.start <= hi)) return;
      s += `<text class="axis" x="${xs(lo) + 8}" y="${M.t + row * (i + .5) + 4}" fill="${D.ink}" opacity=".4" font-style="italic">no pit stop in this window</text>`;
    });
    D.pits.forEach(v => {
      const e0 = v.entry - c.start, e1 = v.exit - c.start, d = teamOf(v.driver), i = D.drivers.indexOf(d);
      if (e1 < lo || e0 > hi || e0 > cx) return;
      const y = M.t + row * (i + .5), x0 = xs(e0), x1 = xs(Math.min(e1, cx));
      s += `<rect x="${x0}" y="${y - 6}" width="${Math.max(x1 - x0, 3)}" height="12" rx="6" fill="${d.color}"><title>${v.driver} lap ${v.entryLap}: pit lane ${v.entry.toFixed(1)}–${v.exit.toFixed(1)} s on the session clock (${v.elapsed.toFixed(1)} s)</title></rect>`;
      if (cx < e1) s += car(xs(cx), y - 12, d.color, `${v.driver} · pit lane`);
      else {
        const b = badge(v);
        if (b) {
          const w = b.text.length * 6.3 + 20, panelEnd = ox + (hi - lo) * unit, right = xs(e1) + 12 + w > panelEnd && x0 - 12 - w >= ox, bx = right ? x0 - 12 - w : x1 + 12;
          s += `<rect x="${x0 - 4}" y="${y - 10}" width="${x1 - x0 + 8}" height="20" rx="10" fill="none" stroke="${b.fill}" stroke-width="2.5"/>`
             + `<rect x="${bx}" y="${y - 11}" width="${w}" height="22" rx="11" fill="${b.fill}"/>`
             + `<text class="label" x="${bx + w / 2}" y="${y + 4}" fill="${b.ink}" text-anchor="middle" font-size="11">${b.text}</text>`;
        }
      }
    });
    ox += (hi - lo) * unit + gap;
  });
  // Overview: all visits on the whole-race clock, so each VSC stays in context.
  const oTop = bottom + 78, oW = W - M.l - M.r, oMin = (D.t1 - D.t0) / 60, ovx = m => M.l + m / oMin * oW, oRow = 18, oBottom = oTop + oRow * n;
  s += `<text class="label" x="${M.l}" y="${oTop - 18}" fill="${D.ink}">All ${D.pits.length} pit visits across the race: the ringed ones had a VSC flag on their lap</text>`;
  ev.forEach(c => { const a = ovx((c.start - D.t0) / 60), b = ovx((c.clear - D.t0) / 60);
    s += `<rect x="${a}" y="${oTop}" width="${Math.max(b - a, 3)}" height="${oBottom - oTop}" fill="${D.vscColor}" opacity=".25"/>`
       + `<text class="axis" x="${a}" y="${oTop - 4}" fill="${D.vscColor}" font-weight="700">${c.name}</text>`; });
  D.drivers.forEach((d, i) => { const y = oTop + oRow * (i + .5);
    s += `<text class="axis" x="${M.l - 10}" y="${y + 4}" fill="${D.ink}" text-anchor="end">${d.code}</text><line x1="${M.l}" x2="${W - M.r}" y1="${y}" y2="${y}" stroke="${D.grid}"/>`; });
  D.pits.forEach(v => {
    const m = (v.entry - D.t0) / 60, d = teamOf(v.driver), y = oTop + oRow * (D.drivers.indexOf(d) + .5);
    const b = badge(v);
    if (m <= k * oMin) s += `<rect x="${ovx(m)}" y="${y - 6}" width="${Math.max(7, ovx(v.elapsed / 60) - ovx(0))}" height="12" rx="4" fill="${d.color}" opacity="${b ? 1 : .6}" stroke="${b ? b.fill : 'none'}" stroke-width="${b ? 2.5 : 0}"><title>${v.driver} lap ${v.entryLap}: ${v.elapsed.toFixed(1)} s in pit lane</title></rect>`;
  });
  for (let m = 0; m <= oMin; m += 20) s += `<text class="axis" x="${ovx(m)}" y="${oBottom + 16}" fill="${D.ink}" text-anchor="middle">${m}</text>`;
  s += `<text class="axis" x="${M.l + oW / 2}" y="${oBottom + 32}" fill="${D.ink}" text-anchor="middle" font-weight="700">Minutes from the first lap start</text>`
     + (k < 1 ? `<line x1="${ovx(k * oMin)}" x2="${ovx(k * oMin)}" y1="${oTop}" y2="${oBottom}" stroke="${D.ink}" opacity=".5"/>` : '');
  svg.innerHTML = s;
}

function eventFrame(t) {  // Lap time, position and same-lap interval around each VSC, at observed lap completions only.
  const k = sweep(t), W = svg.clientWidth || 900, ev = D.events, n = D.drivers.length;
  if (!ev.length) return missing('Needs the pit/VSC exploration files in docs/pit-vsc-exploration (merged in #14).');
  const notes = ev.flatMap(e => e.notes), M = {l: 70, r: 20, t: 62}, gap = 46, rowGap = 28, noteH = 18 * notes.length + 8;
  const pw = (W - M.l - M.r - gap * (ev.length - 1)) / ev.length, ph = (H - M.t - 40 - noteH - rowGap * 2) / 3;
  const allPts = ev.flatMap(e => e.series.flatMap(q => q.points));
  const times = allPts.filter(p => p.time !== null).map(p => p.time), timeLo = Math.floor(Math.min(...times)) - 1, timeHi = Math.ceil(Math.max(...times)) + 1;
  const maxPos = Math.max(...allPts.map(p => p.pos)), maxGap = Math.ceil(Math.max(...allPts.map(p => p.gap)) / 10) * 10;
  const rows = [{title: 'Lap time (s)', f: p => p.time, skipPit: true, lo: timeLo, hi: timeHi, step: 5},
                {title: 'Position', f: p => p.pos, lo: 1, hi: maxPos, flip: true, step: maxPos <= 8 ? 1 : 2},
                {title: 'Interval to first finisher (s)', f: p => p.gap, lo: 0, hi: maxGap, flip: true, step: 10}];
  let s = `<defs>${CAR}</defs>` + legend(W - n * 70 - 10, 14);
  rows.forEach((rw, ri) => {
    const top = M.t + ri * (ph + rowGap), bottom = top + ph;
    s += `<text class="axis" x="14" y="${(top + bottom) / 2}" fill="${D.ink}" font-weight="700" transform="rotate(-90 14 ${(top + bottom) / 2})" text-anchor="middle">${rw.title}</text>`;
    ev.forEach((e, j) => {
      const ox = M.l + j * (pw + gap), xv = e.series.flatMap(q => q.points.map(p => p.x));
      const xlo = Math.min(...xv) - 12, xhi = Math.max(...xv) + 12, xs = v => ox + (v - xlo) / (xhi - xlo) * pw, cx = xlo + k * (xhi - xlo);
      let lo = rw.lo, hi = rw.hi;
      if (lo === undefined) { const vals = e.series.flatMap(q => q.points.map(rw.f)).filter(v => v !== null); lo = Math.floor(Math.min(...vals)) - 1; hi = Math.ceil(Math.max(...vals)) + 1; }
      const ys = v => rw.flip ? top + (v - lo) / (hi - lo) * (bottom - top) : bottom - (v - lo) / (hi - lo) * (bottom - top);
      if (ri === 0) s += `<text class="label" x="${ox}" y="30" fill="${D.ink}">${e.name} (cars must slow down) · laps ${e.before}–${e.after}</text>`;
      s += phases(e, xs, top, bottom, ri === 0);
      const step = rw.step || (hi - lo > 15 ? 5 : 1);
      for (let v = ri === 0 ? Math.ceil(lo / step) * step : rw.lo !== undefined ? lo : Math.ceil(lo / step) * step; v <= hi; v += step)
        s += `<line x1="${ox}" x2="${ox + pw}" y1="${ys(v)}" y2="${ys(v)}" stroke="${D.grid}"/><text class="axis" x="${ox - 6}" y="${ys(v) + 4}" fill="${D.ink}" text-anchor="end">${v}</text>`;
      if (ri === 2) { const xstep = niceStep(xhi - xlo);
        for (let v = Math.ceil(xlo / xstep) * xstep; v <= xhi; v += xstep) s += `<text class="axis" x="${xs(v)}" y="${bottom + 16}" fill="${D.ink}" text-anchor="middle">${v}</text>`;
        s += `<text class="axis" x="${ox + pw / 2}" y="${bottom + 32}" fill="${D.ink}" text-anchor="middle" font-weight="700">Seconds from VSC deployment (session clock)</text>`; }
      if (ri === 0) {
        const normal = median(e.series.flatMap(q => q.points.filter(p => p.time !== null && !p.vscLap).map(p => p.time)));
        s += `<line x1="${ox}" x2="${ox + pw}" y1="${ys(normal)}" y2="${ys(normal)}" stroke="${D.ink}" stroke-dasharray="5 4" opacity=".55"/>`
           + `<line x1="${ox + 8}" x2="${ox + 30}" y1="${top + 12}" y2="${top + 12}" stroke="${D.ink}" stroke-dasharray="5 4"/>`
           + `<text class="axis" x="${ox + 36}" y="${top + 16}" fill="${D.ink}" font-weight="700">a normal lap ≈ ${normal.toFixed(0)} s</text>`;
        const slow = e.series.flatMap(q => q.points.filter(p => p.time !== null).map(p => ({...p, code: q.code}))).sort((a, b) => b.time - a.time)[0];
        if (slow && slow.x <= cx) {
          const text = `slowest lap: ${slow.code} lap ${slow.lap}, ${slow.time.toFixed(1)} s`, w = text.length * 6.3 + 18, left = xs(slow.x) + 16 + w > ox + pw;
          s += `<circle cx="${xs(slow.x)}" cy="${ys(slow.time)}" r="9" fill="none" stroke="${D.vscColor}" stroke-width="2.5"/>`
             + `<rect x="${left ? xs(slow.x) - 14 - w : xs(slow.x) + 14}" y="${ys(slow.time) - 11}" width="${w}" height="22" rx="11" fill="${D.vscColor}"/>`
             + `<text class="label" x="${(left ? xs(slow.x) - 14 - w : xs(slow.x) + 14) + w / 2}" y="${ys(slow.time) + 4}" fill="#15151e" text-anchor="middle" font-size="11">${text}</text>`;
        }
      }
      if (k < 1) s += `<line x1="${xs(cx)}" x2="${xs(cx)}" y1="${top}" y2="${bottom}" stroke="${D.ink}" opacity=".5"/>`;
      e.series.forEach((q, qi) => {
        const d = D.drivers[qi], shown = q.points.filter(p => p.x <= cx && !(rw.skipPit && p.time === null));
        for (const p of shown) s += mark(xs(p.x), ys(rw.f(p)), d.color, d.dashed,
          `${q.code} lap ${p.lap}: ` + (ri === 0 ? `${p.time.toFixed(3)} s` : ri === 1 ? `P${p.pos}` : `${p.gap.toFixed(3)} s behind the first finisher of that lap`));
        const last = shown[shown.length - 1];
        if (ri === 0 && last && k < 1) s += car(xs(last.x), ys(last.time), d.color, `${q.code} · lap ${last.lap}`);
      });
    });
  });
  notes.forEach((text, i) => { s += `<text class="axis" x="${M.l}" y="${H - noteH + 16 + 18 * i}" fill="${D.ink}">${esc(text)}</text>`; });
  svg.innerHTML = s;
}

function frame(t) {
  if (KIND === 'pitclock') return pitFrame(t);
  if (KIND === 'event') return eventFrame(t);
  if (KIND === 'pace') return paceFrame(Math.min(1, 3 * (t - D.t0) / (D.t1 - D.t0)));
  if (KIND === 'tyres') return tyreFrame(t);
  lapFrame(t);
}

let start = null;
const reduced = matchMedia('(prefers-reduced-motion: reduce)').matches;
function tick(now) {
  if (start === null) start = now;
  const k = Math.min(1, Math.max(0, (now - start - 400) / D.duration));
  frame(D.t0 + k * (D.t1 - D.t0));
  if (k < 1) requestAnimationFrame(tick);
}
function play() { start = null; reduced ? frame(D.t1) : requestAnimationFrame(tick); }
document.getElementById('replay').onclick = play;
addEventListener('resize', () => { if (reduced) frame(D.t1); });
play();
</script></body></html>'''
