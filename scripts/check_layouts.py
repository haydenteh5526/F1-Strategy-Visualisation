"""Check every dashboard view at several window widths for clipped chart text and sideways scrolling.

Starts the Streamlit story app, opens each view with ``?chart=N`` in headless Chromium and checks that:
- the page does not scroll sideways;
- no chart frame scrolls sideways;
- every piece of chart text lies inside its drawing;
- every pit-clock badge's text stays inside its pill.

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
VIEWS = 6
TOLERANCE = 1   # Pixels of anti-aliasing allowed at an edge.

FRAME_CHECK = """(tol) => {
  const out = {sideways: document.documentElement.scrollWidth > document.documentElement.clientWidth + tol, clipped: [], badges: []};
  for (const svg of document.querySelectorAll('svg')) {
    const box = svg.getBoundingClientRect();
    if (!box.width || !box.height) continue;
    for (const t of svg.querySelectorAll('text')) {
      const r = t.getBoundingClientRect();
      if (!t.textContent.trim() || !r.width) continue;
      if (r.left < box.left - tol || r.right > box.right + tol || r.top < box.top - tol || r.bottom > box.bottom + tol)
        out.clipped.push(t.textContent.trim().slice(0, 60));
    }
    for (const g of svg.querySelectorAll('g')) {     // A badge is a rounded rect with its label drawn on top.
      const pill = [...g.children].find(c => c.tagName === 'rect' && +c.getAttribute('rx') > 0);
      const label = [...g.children].find(c => c.tagName === 'text');
      if (!pill || !label) continue;
      const p = pill.getBoundingClientRect(), l = label.getBoundingClientRect();
      if (l.left < p.left - tol || l.right > p.right + tol) out.badges.push(label.textContent.trim().slice(0, 60));
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


def check(widths: list[int], height: int = 900) -> list[dict]:
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
                for view in range(1, VIEWS+1):
                    page.goto(f'{base}/?chart={view}', wait_until='networkidle')
                    page.wait_for_selector('iframe, [data-testid="stVegaLiteChart"]', state='attached', timeout=60000)
                    page.wait_for_timeout(2500)   # Let charts finish drawing and re-measure after web fonts load.
                    found = {'width': width, 'view': view, 'pageSideways': page.evaluate(
                        'document.documentElement.scrollWidth > document.documentElement.clientWidth + 1'),
                        'framesSideways': 0, 'clipped': [], 'badges': []}
                    for frame in page.frames[1:]:
                        try:
                            r = frame.evaluate(FRAME_CHECK, TOLERANCE)
                        except Exception:
                            continue
                        found['framesSideways'] += r['sideways']
                        found['clipped'] += r['clipped']
                        found['badges'] += r['badges']
                    found['clean'] = not (found['pageSideways'] or found['framesSideways'] or found['clipped'] or found['badges'])
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
        problems = [k for k in ('pageSideways', 'framesSideways') if r[k]] + [f'clipped: {t}' for t in r['clipped']] \
            + [f'badge overflow: {t}' for t in r['badges']]
        print(f"{r['width']:>5} px  view {r['view']}  {'clean' if r['clean'] else '; '.join(problems)}")
    clean = sum(r['clean'] for r in results)
    print(f'{clean} of {len(results)} view/width combinations clean')
    if args.json:
        args.json.write_text(json.dumps(results, indent=2), encoding='utf-8')
    return 0 if clean == len(results) else 1


if __name__ == '__main__':
    sys.exit(main())
