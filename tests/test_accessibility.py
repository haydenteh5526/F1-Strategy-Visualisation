"""Accessibility and layout checks that run without a browser: colour contrast and text that would be clipped."""
from pathlib import Path
import re
import shutil
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'app'))
sys.path.insert(0, str(ROOT/'tests'))
import charts  # noqa: E402
import replay  # noqa: E402
import theme  # noqa: E402
from test_replay import evaluate, render  # noqa: E402


def luminance(hex_colour: str) -> float:
    channels = [int(hex_colour[i:i+2], 16)/255 for i in (1, 3, 5)]
    r, g, b = [c/12.92 if c <= .03928 else ((c+.055)/1.055)**2.4 for c in channels]
    return .2126*r+.7152*g+.0722*b


def contrast(a: str, b: str) -> float:
    high, low = sorted([luminance(a), luminance(b)], reverse=True)
    return (high+.05)/(low+.05)


def blend(foreground: str, background: str, alpha: float) -> str:
    f, g = [[int(h[i:i+2], 16) for i in (1, 3, 5)] for h in (foreground, background)]
    return '#%02x%02x%02x' % tuple(round(alpha*x+(1-alpha)*y) for x, y in zip(f, g))


PAGE, TAKEAWAY, FRAME = '#15151e', '#2a1416', '#1a1a23'   # Backgrounds the small text sits on (see theme.py).


class ContrastTests(unittest.TestCase):
    def test_small_text_meets_4_5_to_1(self):
        pairs = {'chart text': (charts.INK['dark'], PAGE), 'small red caps label': (theme.KICKER, PAGE),
                 'label on takeaway box': (theme.KICKER, TAKEAWAY), 'label on carbon frame': (theme.KICKER, FRAME),
                 'italic "no pit stop" note': (blend(charts.INK['dark'], PAGE, .7), PAGE), 'amber phase labels': ('#eda100', PAGE),
                 'white on red badge': ('#ffffff', '#e10600'), 'dark on amber badge': (PAGE, '#eda100'),
                 'white on grey badge': ('#ffffff', '#5a5a64'), 'light-mode chart text': (charts.INK['light'], charts.SURFACE['light'])}
        for name, (foreground, background) in pairs.items():
            with self.subTest(name):
                self.assertGreaterEqual(contrast(foreground, background), 4.5)

    def test_chart_marks_meet_3_to_1_on_both_surfaces(self):
        for mode in ('dark', 'light'):
            for colour in charts.TEAM_COLORS[mode]+charts.COMPOUND_COLORS:   # Every team colour and all three tyre colours.
                with self.subTest(mode=mode, colour=colour):
                    self.assertGreaterEqual(contrast(colour, charts.SURFACE[mode]), 3)

    def test_marks_keep_3_to_1_at_their_actual_opacity(self):
        """Composite each mark's colour over the surface at the opacity it is drawn with, not at full strength."""
        data = charts.load_data(ROOT/'data/processed/austria-2026')
        laps, stints, visits = data['laps'], data['stints'], data['visits']
        pace = laps[laps.EligibleForPace]

        def marks(node):
            if isinstance(node, dict):
                if isinstance(node.get('mark'), dict):
                    yield node['mark']
                for value in node.values():
                    yield from marks(value)
            elif isinstance(node, list):
                for value in node:
                    yield from marks(value)

        for mode in ('dark', 'light'):
            built = {'pace': charts.pace_chart(pace, mode), 'tyre age': charts.tyre_age_chart(pace, mode),
                     'vsc': charts.vsc_chart(laps, mode), 'stints': charts.stint_timeline(stints, laps, mode),
                     'positions': charts.position_chart(laps, visits, mode)}
            for name, chart in built.items():
                for mark in marks(chart.to_dict()):
                    kind, opacity = mark.get('type'), mark.get('opacity', 1)
                    if kind not in ('point', 'circle', 'bar', 'line') or opacity == 0:
                        continue   # Text, gridlines and shading are not data marks; opacity 0 is an invisible hover target.
                    if kind == 'bar' and mark.get('fillOpacity', 1) < 1:
                        self.assertGreaterEqual(mark.get('strokeWidth', 0), 1, (mode, name))   # A pale fill needs a solid edge.
                        self.assertEqual(mark.get('strokeOpacity', 1), 1, (mode, name))
                        continue
                    for colour in charts.TEAM_COLORS[mode]+charts.COMPOUND_COLORS:
                        with self.subTest(mode=mode, chart=name, colour=colour, opacity=opacity):
                            seen = blend(colour, charts.SURFACE[mode], opacity)
                            self.assertGreaterEqual(contrast(seen, charts.SURFACE[mode]), 3)


@unittest.skipUnless(shutil.which('node'), 'needs Node.js to run the replay script')
class ClippingTests(unittest.TestCase):
    """Estimate each text's extent and check it stays inside the drawing; a browser audit covers the exact fit."""
    SIZE = {'axis': 5.6, 'label': 6.9, 'counter': 10.5}

    @classmethod
    def setUpClass(cls):
        cls.laps = charts.load_data(ROOT/'data/processed/austria-2026')['laps']

    def clipped(self, drawn: str, width: int) -> list[str]:
        out = []
        for tag in re.findall(r'<text [^>]*>[^<]*</text>', drawn):
            if 'transform="rotate' in tag:
                continue
            x = float(re.search(r' x="([-\d.]+)"', tag).group(1))
            text = re.sub(r'<[^>]+>', '', tag)
            css, font = re.search(r'class="(\w+)"', tag), re.search(r'font-size="(\d+)"', tag)
            factor = float(font.group(1))*.62 if font else self.SIZE.get(css.group(1) if css else '', 6.5)
            size = len(text)*factor
            anchor = re.search(r'text-anchor="(\w+)"', tag)
            left, right = {'end': (x-size, x), 'middle': (x-size/2, x+size/2)}.get(anchor.group(1) if anchor else '', (x, x+size))
            if left < -2 or right > width+2:
                out.append(f'{text[:40]!r} spans {left:.0f} to {right:.0f}')
        return out

    def test_no_text_runs_off_the_drawing_on_any_view_at_common_widths(self):
        views = [('timeline', 400), ('pace', 400), ('tyres', 650), ('pitclock', 488), ('event', 800), ('positions', 420)]
        for width in (420, 700, 1240):
            for kind, height in views:
                with self.subTest(width=width, kind=kind):
                    page = replay.html(self.laps, kind, 'dark', height)
                    self.assertEqual(self.clipped(render(page, width=width), width), [])

    def test_replay_range_bars_have_solid_edges_and_pit_bars_are_opaque(self):
        pace = render(replay.html(self.laps, 'pace', 'dark', 400), width=1000)
        bars = re.findall(r'<rect [^>]*fill-opacity="[^"]*"[^>]*>', pace)
        self.assertEqual(len(bars), 6)
        self.assertTrue(all('stroke="#' in bar and 'stroke-width="1.5"' in bar for bar in bars))
        pits = re.findall(r'<rect [^>]*rx="4"[^>]*>', render(replay.html(self.laps, 'pitclock', 'dark', 488), width=1000))
        self.assertEqual(len(pits), 14)
        self.assertFalse([pit for pit in pits if 'opacity' in pit])

    def test_tyre_panels_use_one_column_on_a_narrow_screen(self):
        page = replay.html(self.laps, 'tyres', 'dark', 650)
        narrow, wide = (float(evaluate(page, 'svg.style.height', width=w).strip('"').replace('px', '')) for w in (420, 1240))
        self.assertGreater(narrow, wide)


if __name__ == '__main__':
    unittest.main()
