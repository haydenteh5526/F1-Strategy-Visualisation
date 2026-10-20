# F1 Strategy Visualisation

Group Data Visualisation Project    Exploration Notes: Pace and Tyres

Exploratory notes for issues #5 and #6. They describe patterns in the Austria 2026 data and are not final findings. `scripts/explore_pace_tyres.py` produces every number below (saved in `pace_tyres_summary.json`) and the figures in `figures/austria-2026/exploration/`. The traffic check also needs the raw snapshot in `data/raw/austria-2026/`.

## Pace and consistency (#5)

Sample: normal racing laps only. HAD 61, VER 60, ANT 61, RUS 60, HAM 61, LEC 58.

- **Whole-race typical laps are close.** Medians range from 71.64 s (ANT) to 71.95 s (LEC), a 0.31 s spread (`pace.png`).
- **Consistency differs more.** The middle half of laps spans 0.85 s for HAM and 0.94 s for RUS, against 1.35 s for ANT and 1.34 s for LEC.
- **The order depends on the part of the race** (`pace-same-compound-windows.png`):
  - Laps 2–11, all on Medium: RUS 72.01 s, VER 72.08, ANT 72.28, HAM 72.44, LEC 72.72, HAD 72.97 (9–10 laps each).
  - Laps 44–59, all on Hard: VER 70.76 s, RUS 70.94, HAM 71.30, HAD 71.48, LEC 71.72, ANT 71.72 (12–14 laps each).
  - ANT has the best whole-race median but the slowest in the Hard window. Tyre ages in that window range from 1 to 31 laps, so it still mixes old and new sets.
- **Lap times fall through the race.** Every driver's typical lap got faster with each new stint (`pace-by-lap.png`).

Alternative explanations checked:

- **Traffic.** A lap is treated as possibly in traffic when it started within 1 s of another car crossing the line. That applies to 7% of RUS's laps, 10% LEC, 17% VER, 18% ANT and 25% each for HAD and HAM. Without those laps the order becomes ANT, VER, HAM, RUS, HAD, LEC, so RUS moves from second to fourth. The proxy is rough because it only measures gaps at the finish line.
- **Fuel load and track changes.** Later stints are faster at the same tyre age (see the tyre notes), so windows from different parts of the race are not comparable.
- **Interruptions.** VSC and yellow-flag laps are already excluded by the pace rule.

Alternative chart: the box plot (`alternative-pace-boxplot.png`) shows the full spread and slow outliers, such as HAM's two laps above 74 s, but is busier. The range chart is quicker to read and hides those outliers.

Implication for the charts: show like-for-like windows instead of a single whole-race ranking.

## Tyres and tyre age (#6)

Recorded laps differ from eligible laps because pit-in and pit-out laps, lap 1, VSC and yellow laps, deleted laps and FastF1 accuracy flags are left out. The summary JSON has the reasons for each stint.

| Driver | Stint | Tyre | Laps | Recorded | Eligible | Set |
| --- | --- | --- | --- | --- | --- | --- |
| HAD | 1 | Medium | 1–18 | 18 | 16 | New |
| HAD | 2 | Medium | 19–40 | 22 | 17 | New |
| HAD | 3 | Hard | 41–71 | 31 | 28 | New |
| VER | 1 | Medium | 1–18 | 18 | 15 | New |
| VER | 2 | Hard | 19–49 | 31 | 26 | New |
| VER | 3 | Hard | 50–71 | 22 | 19 | New |
| ANT | 1 | Medium | 1–24 | 24 | 20 | New |
| ANT | 2 | Hard | 25–51 | 27 | 23 | New |
| ANT | 3 | Hard | 52–71 | 20 | 18 | New |
| RUS | 1 | Medium | 1–19 | 19 | 17 | New |
| RUS | 2 | Hard | 20–43 | 24 | 19 | New |
| RUS | 3 | Hard | 44–71 | 28 | 24 | New |
| HAM | 1 | Medium | 1–12 | 12 | 10 | New |
| HAM | 2 | Hard | 13–25 | 13 | 10 | New |
| HAM | 3 | Soft | 26–42 | 17 | 15 | Used (age 3) |
| HAM | 4 | Hard | 43–71 | 29 | 26 | New |
| LEC | 1 | Medium | 1–13 | 13 | 10 | New |
| LEC | 2 | Hard | 14–37 | 24 | 19 | New |
| LEC | 3 | Hard | 38–59 | 22 | 18 | New |
| LEC | 4 | Soft | 60–71 | 12 | 11 | Used (age 4) |

- **Lap time rises with tyre age in most stints.** A straight-line trend on eligible laps is positive in 18 of 20 stints, from 0.02 to 0.21 s per lap. Two LEC stints are slightly negative: Hard stint 2 at −0.01 and Soft stint 4 at −0.02 (`tyre-age.png`).
- **The steepest trends come from short first stints.** HAM gains 0.21 s per lap and LEC 0.15 s, each over 10 laps on Medium at the start of the race.
- **Used sets.** HAM's and LEC's Soft sets were not new; their first recorded tyre ages were 3 and 4 laps.
- **Race phase matters.** For all six drivers who used the same tyre type twice, the later stint was faster at the same tyre ages, by 0.57 to 1.63 s (`tyre-race-phase.png`). Lap time against tyre age therefore mixes tyre ageing with lighter fuel and track changes, so the trends above are not tyre wear.

Alternative chart: lap time relative to the start of each stint (`alternative-relative-tyre-age.png`) removes the stint-to-stint baseline, so changes within a stint are easier to compare. It hides real lap times and depends on the first three laps used as the baseline.

## Limitations

- One race and six drivers. Samples per stint or window are small (9–28 laps).
- Fuel load and track evolution are not measured, and the traffic proxy is rough.
- Tyre age counts laps on a set; it is not a measurement of wear.
- All comparisons use the data audit's pace rule. Slow laps remain in the other prepared files.
