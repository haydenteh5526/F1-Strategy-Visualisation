# Story review against the Message and Visualization Design Plan (issue #18)

Evidence is recomputed from `data/processed/austria-2026/` and `docs/pit-vsc-exploration/`.

| # | Question | Main message on the page | Evidence |
| --- | --- | --- | --- |
| 1 | Which tyre sequences did the drivers use? | Every driver made 2 stops except HAM and LEC (3); only they used Soft | stint table |
| 2 | How do lap times and consistency compare in normal racing? | ANT typical 71.64 s, RUS 71.66 s, VER 71.76 s, HAM 71.89 s, HAD 71.91 s, LEC 71.95 s; spread is not a ranking of strategy | 361 pace-eligible laps; matched windows kept separate with sample counts (n) and tyre-age differences |
| 3 | How does lap time vary with tyre age? | Tyre age counts laps, not wear; sparse stints support no trend | stint-context table (recorded vs eligible laps, start and end age) |
| 4 | Which pit visits overlap a VSC? | 3 pit stops carry a VSC flag; only 1 (HAM, lap 25, 21.2 s) overlaps the VSC; ANT lap 24 ended 0.132 s before it began, too close to call | `pit_event_comparisons.csv`, session-clock windows |
| 5 | What do the laps around each VSC show? | 25 laps affected (21 of them not pit laps); slowest HAD lap 25 at 100.5 s against a 71.8 s normal-lap median; a ringed lap can finish outside the shaded zone | affected laps, 361-lap median |
| Extra | Positions through the race | RUS won; the selected drivers finished RUS 1, VER 2, ANT 3, HAM 5, HAD 6, LEC 8 | final lap positions |

## Plan check of the merged dashboard (7 November 2026)

Each design card's intended message was compared with the live page on main `c88a1fe`. These were missing or only implied, and are now stated from the data:

| Card | Added |
| --- | --- |
| 1 Tyre stints | "Two bars of the same colour in a row are two different sets": a pit stop starts a new stint even on the same tyre (ANT, Hard twice) |
| 2 Matched pace | The Mercedes contrast as the takeaway: whole race ANT 0.018 s faster than RUS; matched laps ANT 0.155 s slower on Medium in laps 1–20 (16 pairs) and 0.883 s faster on Hard in laps 61–71 (11 pairs, tyres 8 laps younger) |
| 3 Tyre age | HAM's used Soft set: recorded tyre age 3 laps on the first lap of the stint (FastF1 counts that lap, so this is not the age when fitted), 15 normal laps from a 17-lap stint. The stint table now shows the descriptive change per tyre lap (stints with at least five normal laps and two tyre ages), with a caption that it is not a wear rate |
| 4 Pit/VSC clock | Seconds from the nearest VSC for every non-overlapping visit (ANT lap 24: 0.132 s; ANT lap 51: 48.957 s) |
| 5 Event context | The first car to finish a lap can differ from lap to lap |
| All views | A line under each view naming the teams shown and the source |

The pick of each example is computed, not typed in: the matched takeaway uses the team-mate pair whose windows (5+ pairs each) differ most, and the tyre example uses the longest stint on a used set. Both change with the team filter.

No new data was needed. Everything above comes from the prepared files already in the repository.

## Wording rules applied

- Describe what the data shows; no "best strategy", no causal tyre wear, no live gaps.
- One term per idea: "lap-boundary interval" (seconds behind the first car to finish the lap), "normal racing lap" for pace-eligible laps, "recorded tyre age" for laps on a set.
- Stint, compound, tyre age, pace eligibility, VSC and lap-boundary interval are explained in each view's guide box and in Key terms.
- Sources, units and filtering context appear in the page's Sources and About the data sections and under every static export.

## Audience feedback (#8)

No audience sessions have been run yet. No changes are attributed to audience feedback. Wording, ordering and the "Extra" slide are provisional until the sessions are done; any change will be logged here with its reason.
