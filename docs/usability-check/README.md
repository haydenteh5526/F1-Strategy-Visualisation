# Usability, accessibility and static-export check (issue #19)

Technical checks only. They do not replace the audience sessions in #8.

## Tested

| Item | Version |
| --- | --- |
| Browser | Microsoft Edge 155 (Chromium, headless, Playwright) |
| App | Streamlit 1.66.0, Altair 6.3.0, pandas 2.3.3, Python 3.12.3 |
| Replay script tests | Node.js 24 |
| Date | 22 October 2026 |

## Results

| Check | Result |
| --- | --- |
| Layout at 420, 700, 1000 and 1500 px wide, all six views | 24 of 24 clean: no clipped chart text, no sideways page scroll |
| Narrow screens | Tyre panels switch to one column; pit-clock, event and tyre labels wrap or flip instead of running off the edge |
| Keyboard | Arrow buttons are reachable with Tab and work with Enter; named "Previous chart" and "Next chart" |
| Visible focus | 3 px white outline on buttons and controls |
| Reading order and headings | Browser accessibility tree checked: H1 page title first, then H2 chart question, H3 guide boxes and sections, H4 table titles; no level skipped. The earlier banner image role that hid the H1 was removed |
| Screen readers | Every chart frame has a text description; page language is set |
| Colour is not the only cue | Team-mates use circle/triangle or solid/dashed; tyres carry S/M/H letters; pit visits carry text badges; VSC laps carry rings and labels |
| Contrast | Small text at least 4.5:1; every team colour and all three tyre colours at least 3:1 on both the dark and white surfaces (automated test, no allowance), also at the opacity each mark is drawn with. All data marks are now fully opaque; the pale range bars on the pace view keep a solid full-colour outline, so their edges meet 3:1. Pale VSC shading is background, always labelled "VSC", and is not counted as a data mark. Medium (amber) was 2.17:1 on white and the light-mode Mercedes green 2.82:1, so both were darkened (Medium `#cc8400`, light green `#199e70`) |
| Reduced motion | No running animations; charts are drawn at once with full information |
| Static exports | All six PNGs re-exported with source, filtering and unit notes under each title; values match the dashboard (same data and chart code) |

Automated checks live in `tests/test_accessibility.py` and `tests/test_replay.py`; the browser audit is repeatable with Playwright against `streamlit run app/story.py`.

## Remaining limitations

- Tyre-age export: a few end-of-stint labels sit on top of dots (e.g. LEC "S1 M", HAM "S3 S") and the HAD/VER labels reach the panel edge. They stay readable.
- Matched-pace export: "n" labels next to a point close to zero touch the zero line.
- VSC export: the dots crowd together at normal pace; only the VSC laps stand out. The dashboard view is the clearer one.
- Contrast was computed from the colours used, not measured from screenshots.
- Not tested: real screen readers, Safari/Firefox, touch devices, printed output.
