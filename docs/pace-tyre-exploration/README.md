# Austria 2026: preliminary pace and tyre exploration

Local exploratory work for Roy's issues #5 and #6, based on main `ce8a0a1`. These observations describe six drivers in one race. They do not identify an optimal strategy or isolate tyre wear. The story interface is unchanged; Sebastian's pending PR #15 addresses presentation separately.

## Reproduce

From the repo root with the pinned requirements installed:

```powershell
$env:MPLCONFIGDIR = Join-Path (Get-Location).Path '.venv\matplotlib-cache'
& '.\.venv\Scripts\python.exe' scripts\explore_pace_tyres.py
& '.\.venv\Scripts\python.exe' scripts\plot_stints.py
& '.\.venv\Scripts\python.exe' -m unittest discover -s tests -v
```

No download is needed. The first command generates the four CSVs and three PNGs here from `selected_laps.csv`; the second regenerates Roy's complete stint timeline in `charts/austria-2026/`. Both scripts support `--data-dir` and `--output-dir`. Source: the retained FastF1 3.8.3 snapshot, accessed 8 October 2026, as recorded in the committed audit.

## Eligibility and samples

All 426 recorded laps remain in the inputs and stint accounting. Analysis uses the existing `EligibleForPace` rule unchanged: exclude lap 1, pit entry/exit laps, non-green track status, deleted laps and FastF1 accuracy flags. No further trimming or imputation is applied. A valid lap can still contain traffic or unusual pace.

| Driver | Recorded | Eligible | Excluded | Median (s) | Middle-half width, IQR (s) |
| --- | ---: | ---: | ---: | ---: | ---: |
| HAD | 71 | 61 | 10 | 71.910 | 1.140 |
| VER | 71 | 60 | 11 | 71.760 | 1.209 |
| ANT | 71 | 61 | 10 | 71.644 | 1.352 |
| RUS | 71 | 60 | 11 | 71.662 | 0.940 |
| HAM | 71 | 61 | 10 | 71.887 | 0.848 |
| LEC | 71 | 58 | 13 | 71.952 | 1.336 |

`pace_summary.csv` contains unrounded quartiles and counts. `pace_by_lap.png` keeps teammates distinct with circle/triangle markers and uses shared axes across teams. Shading indicates the VSC-affected lap ranges, whose laps are excluded from these points. `pace_distribution.png` shows median, quartiles and min/max whiskers. Whole-race medians and IQRs mix compounds, stint phases and changing race conditions; smaller IQR does not establish better driving consistency under equal conditions.

## Comparisons at the same race lap and compound

`matched_laps.csv` contains only teammate pairs with both laps eligible, at the exact same race lap and on the same compound. `matched_windows.csv` summarises those pairs in fixed race windows 1–20, 21–40, 41–60 and 61–71, separately by compound. Empty combinations are absent rather than filled. A negative A-minus-B value means A completed the matched laps faster. Groups with very few laps are exploratory and should not support a strong claim.

- Whole-race Mercedes medians differ by only 0.018 s (ANT faster), but matched medium laps in 1–20 have ANT 0.155 s slower than RUS (16 pairs). In the final 11 matched hard laps ANT is 0.883 s faster, with tyres eight recorded laps younger. This change makes a single whole-race ranking inadequate.
- HAD is 0.747 s slower than VER across 15 matched medium laps in 1–20, with equal recorded tyre age. This is an observed difference, not a controlled estimate of driver ability. Their compounds diverge in the next window, so there is no same-compound comparison for 21–40.
- HAM is 0.225 s faster than LEC over nine matched medium laps in 1–20, and 0.432 s faster over 13 matched hard laps in 41–60. In the latter window HAM's tyres are five recorded laps younger. In 21–40 the hard comparison has only three pairs and the sign reverses; that small sample needs caution.

Same-lap matching improves race-phase comparability but does not equalise tyre age, fuel load, track position or traffic. The CSV explicitly preserves each driver's stint and tyre age. Some window groups cross a same-compound tyre change, so their tyre-age differences vary substantially; inspect individual pairs before interpreting a window median. No significance tests or independent-sample assumptions are applied to these serially related laps.

## Stints and tyre age

`stint_summary.csv` keeps all 20 tyre sets separate, even when a stop changes to the same compound. It reports eligible versus recorded laps, boundaries, first/last tyre ages and fresh/used status at stint start. The complete timeline in `charts/austria-2026/` shows all laps and 14 pit-entry boundaries. `tyre_age.png` shows one point per eligible lap, with a distinct marker for each stint; it does not draw lines over excluded laps.

Hamilton's soft stint covers 17 recorded race laps but only 15 eligible observations and begins at recorded tyre age 3 on a used set. Leclerc's final soft stint covers 12 recorded laps, 11 eligible observations and begins at age 4 on a used set. Recorded stint length therefore differs from both analysis sample size and total tyre age.

The table includes an ordinary least-squares descriptive slope only for stints with at least five eligible laps and two distinct tyre ages. Hamilton's opening medium stint has a positive slope of about 0.206 s per tyre lap (10 points); Leclerc's second hard stint has about -0.013 s per tyre lap (19 points). Neither slope measures physical wear. Within each uninterrupted stint, tyre age and race lap advance together, so fuel burn, track evolution and tyre age cannot be separated with this regression. Positive and negative slopes must be read with the race-lap view, not as a causal degradation rate. The fitted slopes are tabulated rather than drawn as authoritative trend lines.

## Alternative explanations and design choices

- Race phase: the matched comparisons hold race lap fixed, while the full scatter exposes later stints at lower lap times. Later race pace also coincides with fuel burn and potentially track evolution; fuel quantity is not available here.
- Interruptions: VSC laps 24–26 and 52–53 are excluded, along with other non-green laps. Effects after a restart can persist into eligible laps. Eligibility is not proof of equal track conditions.
- Traffic: the selected-lap data has positions but does not identify the distance to every car ahead, backmarkers or dirty air. A selected driver's position cannot establish free air. No traffic adjustment or traffic-free claim is made; full-field timing/context review is needed before attributing a particular slow lap to traffic.
- Tyres: matching compound alone leaves different set ages and fresh/used histories. The per-stint panels and paired-age columns expose this remaining difference rather than pool it away.
- A violin or density plot would expose multimodality better than the chosen boxplot, but smoothing choices can dominate samples of roughly 60 laps and would still mix race phases. The boxplot is compact; the race-lap scatter supplies its missing sequence.
- A connected tyre-age line makes direction easier to follow but visually bridges excluded laps. Points and stint-specific markers preserve missing sections. A single pooled trend would mix tyre sets and race phases, so it is not used.

## Validation and remaining work

On 21 October 2026, the combined Windows suite passed **59 tests, no skips**, including five new analysis tests. They check excluded-time independence, exact matching and pair completeness, all-lap/stint accounting, same-compound sets, used-tyre ages, duplicate rejection and slope isolation/minimum samples. All three PNGs were rendered and visually inspected. The upstream app/export/replay tests and Roy's eight standalone chart tests also passed. Streamlit's tests need local socket access on this Windows host; the restricted sandbox stalls while creating its asyncio socket pair, while the approved run passes.

The retained raw snapshot reproduced all six prepared files byte-for-byte after the pull. Timing validation passed 1,065 pairwise comparisons and six finishing checks against the saved reference. The snapshot lacks `session_status.csv`, so start/finish-message offsets remain unverified locally. Committed data and the existing timing report were preserved.

Human interpretation review, teammate approval and actual audience feedback remain pending. Review the matching choices and these provisional observations before moving them into the story or closing #5/#6. No issue updates, commits, pushes or PRs were made by this continuation.
