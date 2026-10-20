"""Animated race replays: each driver's car drives its own data on the real lap clock (compressed)."""
from __future__ import annotations

import json

import pandas as pd

import charts

DURATION_MS = 9000  # Whole race, compressed.


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
                      'time': float(r.LapTimeSeconds), 'age': int(r.TyreLife), 'normal': bool(r.EligibleForPace),
                      'pitOrStart': bool(r.IsFirstLap or r.IsPitInLap or r.IsPitOutLap), 'vscLap': bool(r.HasVSC)}
                     for r, s in zip(rows.itertuples(), starts)]})
    bands = charts.vsc_bands(laps)
    summary = charts.pace_summary(laps.loc[laps.EligibleForPace]).set_index('Driver')
    pace = [{'code': d['code'], 'color': d['color'], 'low': float(summary.Low[d['code']]), 'high': float(summary.High[d['code']]),
             'typical': float(summary.Typical[d['code']])} for d in drivers]
    return {'drivers': drivers, 'pace': pace, 'vsc': [[int(b.Start)-1, int(b.End)] for b in bands.itertuples()],
            'finish': int(laps.LapNumber.max()), 'duration': DURATION_MS,
            't0': min(d['laps'][0]['start'] for d in drivers), 't1': max(d['laps'][-1]['end'] for d in drivers),
            'tyres': dict(zip(charts.COMPOUNDS, charts.COMPOUND_COLORS)),
            'ink': charts.INK[mode], 'muted': '#898781', 'grid': '#2c2c38' if mode == 'dark' else '#e6eaf1',
            'surface': charts.SURFACE[mode], 'vscColor': '#eda100'}


def html(laps: pd.DataFrame, kind: str, mode: str, height: int) -> str:
    """kind is 'timeline', 'positions', 'pace', 'tyres' or 'vsc'."""
    return (TEMPLATE.replace('%DATA%', json.dumps(race_data(laps, mode)))
            .replace('%KIND%', kind).replace('%HEIGHT%', str(height)))


TEMPLATE = r'''<!doctype html><html><head><meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Titillium+Web:wght@400;700;900&display=swap" rel="stylesheet">
<style>
  html, body { margin: 0; background: transparent; font-family: 'Titillium Web', system-ui, sans-serif; }
  #wrap { position: relative; }
  svg { display: block; width: 100%; height: %HEIGHT%px; }
  #replay { position: absolute; left: 6px; top: 4px; border: none; border-radius: 16px; padding: 4px 12px;
    background: #e10600; color: #fff; font: 700 12px 'Titillium Web', sans-serif; letter-spacing: .08em; cursor: pointer; }
  #replay:hover { box-shadow: 0 0 12px #e10600; }
  .label { font-size: 12px; font-weight: 700; }
  .axis { font-size: 11px; }
  .counter { font-size: 18px; font-weight: 900; font-style: italic; letter-spacing: .04em; }
</style></head><body>
<div id="wrap"><svg id="chart" role="img" aria-label="Race replay"></svg><button id="replay" type="button">&#8635; REPLAY</button></div>
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
function posAt(d, p) {  // Position while driving lap ceil(p): blend the last completed lap into the next.
  const L = d.laps, done = Math.floor(p);
  if (done < 1) return L[0].pos;
  if (done >= L.length) return L[L.length - 1].pos;
  return L[done - 1].pos + (L[done].pos - L[done - 1].pos) * (p - done);
}
function car(x, y, color, title) {
  return `<g transform="translate(${x - 58},${y - 8})" style="color:${color}"><title>${esc(title)}</title>`
       + `<use href="#car" width="62" height="16"/></g>`;
}

function lapFrame(t) {
  const W = svg.clientWidth || 900, finish = D.finish;
  const M = KIND === 'timeline' ? {l: 78, r: 24, t: 34, b: 34} : {l: 48, r: 54, t: KIND === 'vsc' ? 62 : 34, b: 34};
  const xs = lap => M.l + lap / (finish + .6) * (W - M.l - M.r);
  const plotB = H - M.b;
  const ps = D.drivers.map(d => progress(d, t));
  const leaderLap = Math.min(finish, Math.floor(Math.max(...ps)) + 1);
  let s = `<defs>${CAR}</defs>`;
  for (let lap = 0; lap <= finish; lap += 5)
    s += `<line x1="${xs(lap)}" x2="${xs(lap)}" y1="${M.t}" y2="${plotB}" stroke="${D.grid}"/>`
       + `<text class="axis" x="${xs(lap)}" y="${plotB + 16}" fill="${D.ink}" text-anchor="middle">${lap}</text>`;
  s += `<text class="axis" x="${(M.l + W - M.r) / 2}" y="${H - 2}" fill="${D.ink}" text-anchor="middle" font-weight="700">Lap</text>`;
  if (KIND !== 'vsc') for (const [a, b] of D.vsc)  // The VSC chart draws its own yellow markers.
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
  } else if (KIND === 'vsc') {
    // Every lap except lap 1 and pit laps, so the VSC slowdown stays visible against normal racing.
    const pts = D.drivers.map(d => d.laps.filter(l => !l.pitOrStart));
    const all = pts.flat().map(l => l.time), lo = Math.floor(Math.min(...all)) - 1, hi = Math.ceil(Math.max(...all)) + 1;
    const ys = v => plotB - (v - lo) / (hi - lo) * (plotB - M.t), step = hi - lo > 15 ? 5 : 1;
    for (let v = Math.ceil(lo / step) * step; v <= hi; v += step)
      s += `<line x1="${M.l}" x2="${W - M.r}" y1="${ys(v)}" y2="${ys(v)}" stroke="${D.grid}"/>`
         + `<text class="axis" x="${M.l - 8}" y="${ys(v) + 4}" fill="${D.ink}" text-anchor="end">${v}</text>`;
    for (const [a, b] of D.vsc) {  // Yellow VSC strip that lights up while the leader is in the period.
      const active = leaderLap > a && leaderLap <= b && leaderLap < finish;
      s += `<rect x="${xs(a)}" y="${M.t}" width="${xs(b) - xs(a)}" height="${plotB - M.t}" fill="${D.vscColor}" opacity="${active ? .14 : .06}"/>`
         + `<rect x="${xs(a)}" y="${M.t - 10}" width="${xs(b) - xs(a)}" height="6" rx="3" fill="${D.vscColor}" opacity="${active ? 1 : .55}"/>`
         + `<text class="label" x="${xs(a)}" y="${M.t - 15}" fill="${D.vscColor}">${active ? 'VSC DEPLOYED' : 'VSC'}</text>`;
    }
    s += yTitle('Lap time (s)', M.t, plotB) + legend(120, 20);
    D.drivers.forEach((d, i) => {
      const p = ps[i], seen = pts[i].filter(l => l.lap <= p);
      for (const l of seen) s += mark(xs(l.lap), ys(l.time), d.color, d.dashed, `${d.code} lap ${l.lap}: ${l.time.toFixed(3)} s`);
      const last = seen[seen.length - 1];
      if (last && p < finish) s += car(xs(p), ys(last.time), d.color, `${d.code} · lap ${Math.ceil(p)}`);
    });
  }
  svg.innerHTML = s;
}

function mark(x, y, color, triangle, title) {  // Team colour plus a shape per team-mate keeps drivers apart.
  const shape = triangle ? `<path d="M${x} ${y - 6} L${x + 5.5} ${y + 4} L${x - 5.5} ${y + 4} Z"`
                         : `<circle cx="${x}" cy="${y}" r="4.6"`;
  return `${shape} fill="${color}" stroke="${D.surface}" stroke-width="1"><title>${esc(title)}</title>${triangle ? '</path>' : '</circle>'}`;
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
  const W = svg.clientWidth || 900, M = {l: 60, r: 90, t: 40, b: 40}, plotB = H - M.b, P = D.pace;
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
    s += `<text class="label" x="${M.l - 10}" y="${y + 4}" fill="${D.ink}" text-anchor="end">${q.code}</text>`;
    if (carX > xs(q.low))
      s += `<rect x="${xs(q.low)}" y="${y - 5}" width="${Math.min(carX, xs(q.high)) - xs(q.low)}" height="10" rx="5" fill="${q.color}" opacity=".4"/>`;
    if (carX >= xs(q.typical))
      s += `<circle cx="${xs(q.typical)}" cy="${y}" r="8" fill="${q.color}" stroke="${D.surface}" stroke-width="2"><title>${q.code} typical lap ${q.typical.toFixed(3)} s</title></circle>`;
    s += travel < 1 ? car(carX, y, q.color, q.code)
                    : `<text class="label" x="${xs(q.high) + 10}" y="${y + 4}" fill="${D.ink}">${q.typical.toFixed(2)} s</text>`;
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
    s += `<text class="label" x="${ox}" y="${oy + 10}" fill="${D.ink}">${d.code} · ${esc(d.team)}</text>`;
    for (let v = lo; v <= hi; v++)
      s += `<line x1="${ox}" x2="${ox + pw}" y1="${ys(v)}" y2="${ys(v)}" stroke="${D.grid}"/>`
         + (i % cols === 0 ? `<text class="axis" x="${ox - 6}" y="${ys(v) + 4}" fill="${D.ink}" text-anchor="end">${v}</text>` : '');
    if (Math.floor(i / cols) === rows - 1)
      for (let a = 0; a < maxAge; a += 5) s += `<text class="axis" x="${xs(a)}" y="${bottom + 14}" fill="${D.ink}" text-anchor="middle">${a}</text>`;
    const seen = normal[i].filter(l => l.lap <= d.p), stints = {};
    for (const l of seen) (stints[l.stint] = stints[l.stint] || []).push(l);
    for (const [stint, laps] of Object.entries(stints)) {
      const c = D.tyres[laps[0].compound];
      s += `<polyline points="${laps.map(l => `${xs(l.age)},${ys(l.time)}`).join(' ')}" fill="none" stroke="${c}" stroke-width="2.2"/>`;
      const lastLap = Math.max(...d.laps.filter(l => l.stint == stint).map(l => l.lap)), end = laps[laps.length - 1];
      if (d.p >= lastLap) s += `<text class="label" x="${xs(end.age) + 5}" y="${ys(end.time) + 4}" fill="${D.ink}">${laps[0].compound[0]}</text>`;
    }
    const last = seen[seen.length - 1];
    if (last && d.p < D.finish) s += car(xs(last.age) + 4, ys(last.time), d.color, `${d.code} · tyre age ${last.age}`);
  });
  svg.innerHTML = s;
}

function frame(t) {
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
