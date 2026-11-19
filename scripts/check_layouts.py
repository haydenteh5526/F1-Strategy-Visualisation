"""Check every dashboard view at several window widths for clipped chart text and sideways scrolling.

Starts the Streamlit story app, opens each view with ``?chart=N`` (and view 2 again with "Matched race windows" selected)
in headless Chromium, waits for its chart to draw and checks that:
- a chart was actually inspected (a view whose chart never drew, or is empty, fails);
- the page and each chart do not scroll sideways;
- every piece of chart text lies inside its drawing;
- every badge's label stays inside its pill, and the pit view shows at least three badges.

Usage: python scripts/check_layouts.py [--widths 420 700 1000 1500] [--json results.json]
Needs: pip install playwright, then python -m playwright install chromium (or a system Chrome).
"""
from __future__ import annotations

import argparse
import json
import socket
import subprocess
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
TOLERANCE = 1   # Pixels of anti-aliasing allowed at an edge.

CHART_CHECK = """([selector, tol]) => {
  // Every chart drawing inside the given containers: text inside its drawing, badge labels inside their pills.
  const out = {charts: 0, texts: 0, badges: 0, sideways: false, clipped: [], badgeOverflow: []};
  for (const host of document.querySelectorAll(selector)) {
    if (host.scrollWidth > host.clientWidth + tol) out.sideways = true;
    for (const svg of host.querySelectorAll('svg')) {
      const box = svg.getBoundingClientRect();
      const texts = [...svg.querySelectorAll('text')].filter(t => t.textContent.trim());
      if (!box.width || !box.height || texts.length < 5) continue;   // Icons and empty drawings are not charts.
      out.charts += 1;
      for (const t of texts) {
        const r = t.getBoundingClientRect();
        if (!r.width) continue;
        out.texts += 1;
        if (r.left < box.left - tol || r.right > box.right + tol || r.top < box.top - tol || r.bottom > box.bottom + tol)
          out.clipped.push(t.textContent.trim().slice(0, 60));
      }
      // A badge is drawn as a filled rounded rectangle immediately followed by its label (replay.js pill()).
      for (const pill of svg.querySelectorAll('rect[rx]')) {
        const label = pill.nextElementSibling;
        if (+pill.getAttribute('rx') <= 0 || pill.getAttribute('fill') === 'none' || !label || label.tagName !== 'text') continue;
        if (label.getAttribute('text-anchor') !== 'middle' || label.getAttribute('class') !== 'label') continue;   // Pill labels are centred; a driver chip's name sits beside it.
        out.badges += 1;
        const p = pill.getBoundingClientRect(), l = label.getBoundingClientRect();
        if (l.left < p.left - tol || l.right > p.right + tol || l.top < p.top - tol || l.bottom > p.bottom + tol)
          out.badgeOverflow.push(label.textContent.trim().slice(0, 60));
      }
    }
  }
  return out;
}"""


def free_port() -> int:
    with socket.socket() as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]


def wait_for(url: str, seconds: float = 60) -> None:
    import urllib.request
    end = time.time() + seconds
    while time.time() < end:
        try:
            urllib.request.urlopen(url, timeout=2)
            return
        except OSError:
            time.sleep(0.5)
    raise RuntimeError(f'Streamlit did not start at {url}')


# (view number, label, pace comparison to select or None). View 2's matched chart is drawn on the main page, not in a frame.
CASES = [(1, '1', None), (2, '2', None), (2, '2 matched', 'Matched race windows'), (3, '3', None), (4, '4', None),
         (5, '5', None), (6, '6', None)]
MIN_BADGES = {'4': 3}   # The pit view always shows a badge for each VSC-flagged visit (three with all teams selected).


def inspect(page) -> dict:
    """Run the chart check in the main page's Vega charts and in every frame's body; merge the results."""
    total = {'charts': 0, 'texts': 0, 'badges': 0, 'framesSideways': 0, 'clipped': [], 'badges_overflow': []}
    targets = [(page.main_frame, '[data-testid="stVegaLiteChart"]')] + [(f, 'body') for f in page.frames[1:]]
    for frame, selector in targets:
        try:
            r = frame.evaluate(CHART_CHECK, [selector, TOLERANCE])
        except Exception:
            continue   # A frame that navigated away or is still loading; the chart count below catches a missing chart.
        total['charts'] += r['charts']
        total['texts'] += r['texts']
        total['badges'] += r['badges']
        total['framesSideways'] += r['sideways']
        total['clipped'] += r['clipped']
        total['badges_overflow'] += r['badgeOverflow']
    return total


def check(widths: list[int], height: int = 900, settle_ms: int = 1500, timeout_s: float = 45) -> list[dict]:
    port = free_port()
    server = subprocess.Popen([sys.executable, '-m', 'streamlit', 'run', str(ROOT/'app/story.py'), '--server.headless', 'true',
                               '--server.port', str(port), '--browser.gatherUsageStats', 'false'],
                              cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    results = []
    try:
        base = f'http://127.0.0.1:{port}'
        wait_for(base)
        with sync_playwright() as p:
            try:
                browser = p.chromium.launch()
            except Exception:
                browser = p.chromium.launch(channel='chrome')
            for width in widths:
                page = browser.new_page(viewport={'width': width, 'height': height}, reduced_motion='reduce')
                for view, label, comparison in CASES:
                    page.goto(f'{base}/?chart={view}', wait_until='networkidle')
                    if comparison:
                        page.get_by_text(comparison, exact=True).click()
                    # Wait until a real chart has drawn (not just a helper frame), then let it re-measure after fonts load.
                    found, end = inspect(page), time.time() + timeout_s
                    while found['charts'] == 0 and time.time() < end:
                        page.wait_for_timeout(500)
                        found = inspect(page)
                    page.wait_for_timeout(settle_ms)
                    found = inspect(page)
                    found.update(width=width, view=label, pageSideways=page.evaluate(
                        'document.documentElement.scrollWidth > document.documentElement.clientWidth + 1'))
                    problems = []
                    if found['charts'] == 0:
                        problems.append('no chart could be inspected')
                    if found['badges'] < MIN_BADGES.get(label, 0):
                        problems.append(f"only {found['badges']} badges inspected, expected at least {MIN_BADGES[label]}")
                    if found['pageSideways']:
                        problems.append('page scrolls sideways')
                    if found['framesSideways']:
                        problems.append('a chart scrolls sideways')
                    problems += [f'clipped: {t}' for t in found['clipped']]
                    problems += [f'badge overflow: {t}' for t in found['badges_overflow']]
                    found['problems'] = problems
                    found['clean'] = not problems
                    results.append(found)
                page.close()
            browser.close()
    finally:
        server.terminate()
        server.wait(timeout=20)
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--widths', type=int, nargs='+', default=[420, 700, 1000, 1500])
    parser.add_argument('--json', type=Path)
    args = parser.parse_args()
    results = check(args.widths)
    for r in results:
        checked = f"{r['charts']} chart(s), {r['texts']} labels, {r['badges']} badges"
        print(f"{r['width']:>5} px  view {r['view']:<10} {checked:<38} {'clean' if r['clean'] else '; '.join(r['problems'])}")
    clean = sum(r['clean'] for r in results)
    print(f'{clean} of {len(results)} view/width combinations clean')
    if args.json:
        args.json.write_text(json.dumps(results, indent=2), encoding='utf-8')
    return 0 if clean == len(results) else 1


if __name__ == '__main__':
    sys.exit(main())
