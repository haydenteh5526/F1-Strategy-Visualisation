"""Motorsport-style banner, fact cards and page styling for the story interface (no official F1 marks)."""
from __future__ import annotations

from html import escape
from urllib.parse import quote

RED = '#e10600'
KICKER = '#ff6b63'  # A lighter red for small caps labels: the brand red is below 4.5:1 on the dark panels.
LIGHTS_OUT = 2.4  # Seconds until the start lights go out and the car launches.
REVEAL = 2.4  # Seconds for a chart to race in from left to right.

# Drawn in the stylesheet as background images because Streamlit strips inline SVG from HTML.
def car_svg(color: str) -> str:
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="-130 0 330 50">
  <defs><linearGradient id="trail" x1="0" x2="1">
    <stop offset="0" stop-color="{color}" stop-opacity="0"/><stop offset="1" stop-color="{color}" stop-opacity=".55"/>
  </linearGradient></defs>
  <rect x="-125" y="23" width="140" height="5" rx="2" fill="url(#trail)"/>
  <path d="M8 31 L38 27 L66 19 L104 16 L118 9 L132 9 L136 17 L168 21 L186 27 L190 32 L8 34 Z" fill="{color}"/>
  <path d="M100 16 Q112 6 126 11" stroke="#f0efec" stroke-width="2.5" fill="none"/>
  <rect x="4" y="8" width="18" height="4" rx="1" fill="#f0efec"/><rect x="12" y="10" width="3" height="20" fill="#f0efec"/>
  <path d="M176 33 L198 33 L198 37 L174 37 Z" fill="#f0efec"/>
  <circle cx="40" cy="36" r="11" fill="#0b0b0b"/><circle cx="40" cy="36" r="4" fill="#5a5a64"/>
  <circle cx="160" cy="37" r="10" fill="#0b0b0b"/><circle cx="160" cy="37" r="3.5" fill="#5a5a64"/>
</svg>'''


# A staggered starting grid: two lanes, each car further back so they chase without overlapping.
# Chasers use the validated dark-mode team colours from charts.py.
CARS = [(RED, -270, 6), ('#3987e5', -430, 42), ('#199e70', -600, 6), ('#d95926', -760, 42)]
CAR_RULES = '\n'.join(
    f'.f1-hero .car-{i} {{ left: {left}px; bottom: {bottom}px; '
    f'background-image: url("data:image/svg+xml,{quote(car_svg(color))}"); }}'
    for i, (color, left, bottom) in enumerate(CARS))

STYLE = f'''<style>
@import url('https://fonts.googleapis.com/css2?family=Titillium+Web:wght@400;600;700;900&display=swap');
@property --n {{ syntax: '<integer>'; inherits: false; initial-value: 0; }}

.f1-hero {{ position: relative; overflow: hidden; border-radius: 14px; padding: 26px 30px 100px;
  background: linear-gradient(115deg, #15151e 0%, #1f1f2b 55%, #3a0b0c 100%);
  border-bottom: 4px solid {RED}; font-family: 'Titillium Web', system-ui, sans-serif; color: #f0efec; }}
.f1-hero::after {{ content: ''; position: absolute; inset: 0 0 0 auto; width: 220px; opacity: .1;
  background: conic-gradient(#fff 25%, transparent 0 50%, #fff 0 75%, transparent 0) 0 0 / 22px 22px;
  -webkit-mask: linear-gradient(90deg, transparent, #000); mask: linear-gradient(90deg, transparent, #000); }}
.f1-hero .lights {{ display: flex; gap: 10px; margin-bottom: 16px; }}
.f1-hero .light {{ width: 20px; height: 20px; border-radius: 50%; background: #34343e;
  box-shadow: inset 0 0 0 2px #0008; animation: light-on .12s var(--on) forwards, light-out .15s {LIGHTS_OUT}s forwards; }}
.f1-hero .kicker {{ font-size: 13px; font-weight: 700; letter-spacing: .18em; text-transform: uppercase; color: {KICKER};
  animation: rise .6s ease-out .1s both; }}
.f1-hero h1 {{ font-family: inherit; font-size: clamp(30px, 4.4vw, 52px); font-weight: 900; line-height: 1.05;
  margin: 4px 0 6px; padding: 0; font-style: italic; text-transform: uppercase; animation: rise .6s ease-out .25s both; }}
.f1-hero .sub {{ font-size: 17px; color: #c3c2b7; animation: rise .6s ease-out .4s both; }}
.f1-hero .speed span {{ position: absolute; height: 2px; border-radius: 2px; opacity: 0;
  background: linear-gradient(90deg, transparent, #f0efec, transparent);
  animation: streak 1.1s linear {LIGHTS_OUT+.3}s infinite; }}
.f1-hero .car {{ position: absolute; width: 260px; height: 40px; background: no-repeat center / contain;
  animation: launch 1.9s cubic-bezier(.6, 0, .9, .4) {LIGHTS_OUT}s forwards; }}
{CAR_RULES}
.f1-hero .dust span {{ position: absolute; left: 60px; bottom: 12px; width: 26px; height: 26px; border-radius: 50%;
  background: radial-gradient(circle, #c3c2b799, transparent 70%); opacity: 0;
  animation: puff 1.3s ease-out var(--d) forwards; }}

.f1-facts {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 12px;
  font-family: 'Titillium Web', system-ui, sans-serif; }}
.f1-fact {{ background: #1f1f2b; border-left: 4px solid {RED}; border-radius: 8px; padding: 12px 16px;
  animation: rise .5s ease-out var(--delay) both; }}
.f1-fact .label {{ font-size: 12px; letter-spacing: .12em; text-transform: uppercase; color: #c3c2b7; }}
.f1-fact .value {{ font-size: 34px; font-weight: 900; font-style: italic; color: #f0efec; line-height: 1.1; }}
.f1-fact .count {{ --n: var(--target); counter-reset: n var(--n); animation: count 1.4s ease-out var(--delay) both; }}
.f1-fact .count::after {{ content: counter(n); }}

.st-key-scroll-keeper {{ display: none; }}
.f1-takeaway {{ margin: 6px 0 14px; padding: 16px 20px; border-left: 6px solid {RED}; border-radius: 6px;
  background: linear-gradient(90deg, #2a1416, #1f1f2b 60%); font-family: 'Titillium Web', system-ui, sans-serif; color: #f0efec;
  animation: rise .5s ease-out both; }}
.f1-takeaway .kicker {{ font-size: 12px; font-weight: 700; letter-spacing: .2em; color: {KICKER}; text-transform: uppercase; }}
.f1-takeaway .big {{ font-size: clamp(19px, 2.2vw, 26px); font-weight: 700; line-height: 1.3; margin-top: 4px; }}
.f1-guide {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 12px; margin-bottom: 14px;
  font-family: 'Titillium Web', system-ui, sans-serif; color: #f0efec; }}
.f1-guide > div {{ background: #1b1b25; border-radius: 6px; padding: 12px 16px; }}
.f1-guide h3 {{ margin: 0 0 6px; padding: 0; border: 0; font-size: 12px; letter-spacing: .16em; text-transform: uppercase; color: #c3c2b7; }}
.f1-guide ul {{ margin: 0; padding-left: 18px; font-size: 15px; line-height: 1.5; }}
.f1-guide li b {{ color: #fff; }}
.f1-flag {{ height: 10px; border-radius: 3px; margin: 8px 0;
  background: conic-gradient(#f0efec 25%, #15151e 0 50%, #f0efec 0 75%, #15151e 0) 0 0 / 10px 10px; opacity: .5; }}

.stMainBlockContainer h2, .stMainBlockContainer h3 {{ font-family: 'Titillium Web', system-ui, sans-serif;
  font-weight: 700; border-left: 4px solid {RED}; padding-left: 10px; }}
.stMainBlockContainer [data-testid="stVerticalBlockBorderWrapper"] {{ border-top: 3px solid {RED}; }}
.stMainBlockContainer [data-testid="stElementContainer"] {{ animation: rise .5s ease-out both; }}

.st-key-chart-frame {{ border-top: 3px solid {RED} !important; overflow: hidden;
  background: repeating-linear-gradient(45deg, #1a1a23 0 7px, #17171f 7px 14px) !important; }}
.st-key-chart-frame h2, .st-key-chart-frame h3 {{ font-family: 'Titillium Web', system-ui, sans-serif; font-style: italic; text-transform: uppercase;
  letter-spacing: .02em; border-left: none; padding-left: 0; }}
.st-key-previous button, .st-key-next button {{ width: 46px; height: 46px; border-radius: 50%; border: none;
  background: {RED}; color: #fff; box-shadow: 0 0 0 0 {RED}00; transition: transform .15s, box-shadow .2s; }}
.st-key-previous button:hover, .st-key-next button:hover, .st-key-previous button:focus, .st-key-next button:focus {{
  transform: scale(1.1); box-shadow: 0 0 18px {RED}; background: {RED} !important; color: #fff !important; }}
.st-key-previous button:active, .st-key-next button:active {{ transform: scale(.94); }}
.st-key-previous button:focus-visible, .st-key-next button:focus-visible, .st-key-chart-frame iframe:focus-visible,
.st-key-chart-frame a:focus-visible, .st-key-chart-frame input:focus-visible, .st-key-chart-frame select:focus-visible {{ outline: 3px solid #ffffff; outline-offset: 3px; }}
.f1-progress {{ display: flex; align-items: center; gap: 14px; font-family: 'Titillium Web', system-ui, sans-serif; }}
.f1-progress .kicker {{ font-size: 12px; font-weight: 700; letter-spacing: .18em; color: {KICKER}; text-transform: uppercase; }}
.f1-progress .segs {{ display: flex; gap: 5px; }}
.f1-progress .seg {{ width: 34px; height: 5px; border-radius: 3px; background: #34343e; transform: skewX(-20deg); }}
.f1-progress .seg.done {{ background: #6a1a1c; }}
.f1-progress .seg.on {{ background: {RED}; box-shadow: 0 0 8px {RED}; }}
[class*="st-key-slide-"] {{ position: relative; }}
[class*="st-key-slide-"][class$="-next"], [class*="st-key-slide-"][class*="-next "] {{ animation: slide-next .6s cubic-bezier(.2, .8, .2, 1) both; }}
[class*="st-key-slide-"][class$="-previous"], [class*="st-key-slide-"][class*="-previous "] {{ animation: slide-previous .6s cubic-bezier(.2, .8, .2, 1) both; }}
[class*="st-key-slide-"]::before {{ content: ''; position: absolute; top: 46%; left: -45%; width: 45%; height: 3px; z-index: 5;
  pointer-events: none; background: linear-gradient(90deg, transparent, {RED}, #fff, transparent); animation: sweep .55s ease-out both; }}
@keyframes slide-next {{ from {{ opacity: 0; transform: translateX(70px) skewX(-6deg); filter: blur(8px); }} to {{ opacity: 1; transform: none; filter: none; }} }}
@keyframes slide-previous {{ from {{ opacity: 0; transform: translateX(-70px) skewX(6deg); filter: blur(8px); }} to {{ opacity: 1; transform: none; filter: none; }} }}
@keyframes sweep {{ from {{ left: -45%; opacity: 1; }} to {{ left: 110%; opacity: 0; }} }}

/* Charts "race" in: marks are revealed left to right behind a timing line with a car at its front. */
[class*="st-key-slide-"] [data-testid="stVegaLiteChart"] {{ position: relative; }}
[class*="st-key-slide-"] svg.marks g.role-mark {{ animation: race-reveal {REVEAL}s cubic-bezier(.5, 0, .25, 1) .3s both; }}
[class*="st-key-slide-"] svg.marks g.role-mark.mark-text {{ animation: fade-in .6s ease-out {REVEAL}s both; }}
[class*="st-key-slide-"] [data-testid="stVegaLiteChart"]::after {{ content: ''; position: absolute; top: 6%; bottom: 16%; width: 3px;
  border-radius: 2px; background: linear-gradient(transparent, {RED}, transparent); box-shadow: 0 0 14px {RED};
  pointer-events: none; z-index: 3; animation: scan-line {REVEAL}s cubic-bezier(.5, 0, .25, 1) .3s both; }}
[class*="st-key-slide-"] [data-testid="stVegaLiteChart"]::before {{ content: ''; position: absolute; top: 1%; width: 120px; height: 18px;
  background: url("data:image/svg+xml,{quote(car_svg(RED))}") no-repeat center / contain;
  pointer-events: none; z-index: 3; animation: scan-car {REVEAL}s cubic-bezier(.5, 0, .25, 1) .3s both; }}
@keyframes race-reveal {{ from {{ clip-path: inset(0 95% 0 0) view-box; }} to {{ clip-path: inset(0 0 0 0) view-box; }} }}
@keyframes fade-in {{ from {{ opacity: 0; }} to {{ opacity: 1; }} }}
@keyframes scan-line {{ 0% {{ left: 5%; opacity: 0; }} 8%, 88% {{ opacity: 1; }} 100% {{ left: 99%; opacity: 0; }} }}
@keyframes scan-car {{ 0% {{ left: calc(5% - 112px); opacity: 0; }} 8%, 88% {{ opacity: 1; }} 100% {{ left: calc(99% - 112px); opacity: 0; }} }}

@keyframes light-on {{ to {{ background: {RED}; box-shadow: 0 0 14px {RED}, inset 0 0 0 2px #0004; }} }}
@keyframes light-out {{ to {{ background: #34343e; box-shadow: inset 0 0 0 2px #0008; }} }}
@keyframes rise {{ from {{ opacity: 0; transform: translateY(14px); }} to {{ opacity: 1; transform: none; }} }}
@keyframes launch {{ to {{ transform: translateX(calc(100vw + 1100px)); }} }}
@keyframes streak {{ 0% {{ opacity: 0; transform: translateX(110%); }} 15% {{ opacity: .35; }}
  100% {{ opacity: 0; transform: translateX(-260%); }} }}
@keyframes puff {{ 0% {{ opacity: .8; transform: scale(.3); }} 100% {{ opacity: 0; transform: translate(-60px, -18px) scale(3); }} }}
@keyframes count {{ from {{ --n: 0; }} }}

@media (prefers-reduced-motion: reduce) {{
  .f1-hero *, .f1-fact, .f1-fact .count, .stMainBlockContainer [data-testid="stElementContainer"],
  [class*="st-key-slide-"], [class*="st-key-slide-"]::before, [class*="st-key-slide-"] svg.marks g.role-mark {{ animation: none !important; }}
  [class*="st-key-slide-"] [data-testid="stVegaLiteChart"]::before, [class*="st-key-slide-"] [data-testid="stVegaLiteChart"]::after {{ display: none; }}
  .f1-hero .car, .f1-hero .speed, .f1-hero .dust {{ display: none; }}
}}
</style>'''


def hero(kicker: str, title: str, subtitle: str) -> str:
    lights = ''.join(f'<span class="light" style="--on:{.3+.4*i:.1f}s"></span>' for i in range(5))
    speed = ''.join(f'<span style="top:{top}%;right:0;width:{width}%;animation-delay:{LIGHTS_OUT+.3+delay}s"></span>'
                    for top, width, delay in [(22, 40, 0), (48, 55, .35), (70, 35, .7), (86, 50, .2)])
    dust = ''.join(f'<span style="--d:{LIGHTS_OUT+delay}s;left:{left}px"></span>'
                   for left, delay in [(40, 0), (70, .08), (20, .16)])
    return (f'<div class="f1-hero" role="img" aria-label="{escape(title)}">'
            f'<div class="lights" aria-hidden="true">{lights}</div>'
            f'<div class="kicker">{escape(kicker)}</div><h1>{escape(title)}</h1><div class="sub">{escape(subtitle)}</div>'
            f'<div class="speed" aria-hidden="true">{speed}</div><div class="dust" aria-hidden="true">{dust}</div>'
            + ''.join(f'<div class="car car-{i}" aria-hidden="true"></div>' for i in range(len(CARS))) + '</div>')


def fact_cards(facts: list[tuple[str, str | int]]) -> str:
    """Numbers count up from zero; text values just slide in."""
    cards = []
    for i, (label, value) in enumerate(facts):
        delay = f'{.5+.15*i:.2f}s'
        shown = (f'<span class="count" style="--target:{value}"></span>' if isinstance(value, int) else escape(value))
        cards.append(f'<div class="f1-fact" style="--delay:{delay}"><div class="label">{escape(label)}</div>'
                     f'<div class="value" data-value="{escape(str(value))}">{shown}</div></div>')
    return f'<div class="f1-facts">{"".join(cards)}</div>'



def slide_progress(index: int, names: list[str]) -> str:
    """Timing-bar style progress: one segment per chart, the current one lit."""
    segs = ''.join(f'<span class="seg{" on" if i == index else " done" if i < index else ""}" title="{escape(n)}"></span>'
                   for i, n in enumerate(names))
    return (f'<div class="f1-progress"><span class="kicker">Chart {index+1} / {len(names)}</span>'
            f'<div class="segs" aria-hidden="true">{segs}</div></div>')



# Runs in a hidden iframe because Streamlit strips scripts from page HTML; the iframe may reach the app page.
# A fresh visit starts at the top; a reload of the same tab returns to the last scroll position.
SCROLL_KEEPER = """<script>
(() => {
  const app = window.parent, KEY = 'f1-story-scroll';
  // The arrow buttons only hold an icon, so give them names a screen reader can announce.
  const label = () => { for (const [key, text] of [['previous', 'Previous chart'], ['next', 'Next chart']])
    app.document.querySelectorAll('.st-key-' + key + ' button').forEach(b => b.setAttribute('aria-label', text)); };
  label(); new app.MutationObserver(label).observe(app.document.body, {childList: true, subtree: true});
  const main = () => app.document.querySelector('[data-testid="stMain"]');
  const nav = app.performance.getEntriesByType('navigation')[0];
  const target = nav && nav.type === 'reload' ? Number(app.sessionStorage.getItem(KEY) || 0) : 0;
  app.history.scrollRestoration = 'manual';
  let touched = false;
  for (const e of ['wheel', 'touchstart', 'keydown', 'mousedown']) app.document.addEventListener(e, () => touched = true, {passive: true});
  const until = Date.now() + 8000, hold = setInterval(() => {  // Content keeps loading, so hold the position until it settles.
    const m = main();
    if (m && !touched && m.scrollHeight - m.clientHeight >= target - 2 && Math.abs(m.scrollTop - target) > 2) m.scrollTop = target;
    if (touched || Date.now() > until) clearInterval(hold);
  }, 50);
  let timer;
  (function save() {
    const m = main();
    if (!m) return setTimeout(save, 200);
    m.addEventListener('scroll', () => { clearTimeout(timer); timer = setTimeout(() => app.sessionStorage.setItem(KEY, m.scrollTop), 150); }, {passive: true});
  })();
})();
</script>"""


def guide(takeaway: str, read: list[str], notice: list[str]) -> str:
    """Plain-English box for a slide: the one-sentence takeaway, how to read the chart and what to notice."""
    items = lambda lines: ''.join(f'<li>{line}</li>' for line in lines)  # Lines may carry <b> tags; callers escape data.
    return (f'<div class="f1-takeaway"><div class="kicker">Key takeaway</div><div class="big">{takeaway}</div></div>'
            f'<div class="f1-guide"><div><h3>How to read this</h3><ul>{items(read)}</ul></div>'
            f'<div><h3>What to notice</h3><ul>{items(notice)}</ul></div></div>')


FLAG = '<div class="f1-flag" aria-hidden="true"></div>'
