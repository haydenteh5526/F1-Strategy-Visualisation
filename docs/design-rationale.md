# Prototype design rationale

This records the baseline layout on `Roys_Branch` at `818e132` and the subsequent main-branch story update for issue #8. It describes design intent and available evidence. Audience testing is pending; no comprehension or preference results are claimed. Sebastian's PR #15 is now merged into main at `b61a8e3`, following review of head `1e5e03e`. The local Roy branch has not yet incorporated that merge.

## Audience and tasks

The [audience brief](audience-brief/README.md) targets F1 fans who recognise teams and basic rules but do not regularly analyse timing. The desktop/projector presentation should let viewers identify a chart's main point in roughly a minute, compare individual drivers, and distinguish observed timing from causal strategy conclusions. That one-minute goal remains untested.

## Baseline desktop layout and static sequence

The page starts with the race identity, source/access date, team filter and race facts. A single chart panel has previous/next navigation and progress labels. Below it, the glossary, source details, eligibility and limitations remain available. One chart at a time limits the number of competing views, while the filter supports team comparisons. This is a design choice, not a demonstrated usability improvement.

| Step | Question and implemented view | Evidence and interpretation limit |
| --- | --- | --- |
| Overview | What tyre sets did each driver use? Stint timeline and strategy table | Preserve six driver rows and same-compound changes; lengths count race laps, not physical wear or exact stop duration |
| Pace | How do eligible lap-time distributions differ? Median and middle-half bars | Explain eligibility and sample context; whole-race spread mixes race phases and tyre choices and cannot isolate driver consistency |
| Tyre age | How do observed lap times change across tyre sets? Driver panels | Driver identity, compound and individual stints matter; tyre age advances with race lap, confounding fuel/track effects |
| Pit stops | Where did positions change around stops? Positions and pit table | Pit-lane elapsed time includes traversal; it is neither stationary service time nor causal time lost |
| VSC | What do affected lap times look like? VSC lap-time view | Retain affected non-pit laps and distinguish whole-lap shading from the recorded deployment/ending/clear clock |

The five images in `figures/austria-2026/` provide the static companion sequence. They do not require animation or interaction to be presented. Roy's additional `docs/pace-tyre-exploration/` figures are exploratory evidence, not automatically integrated story slides. The complete standalone timeline in `charts/austria-2026/` additionally marks all 14 pit-entry boundaries.

## Encoding choices and alternatives

- Keep drivers individually labelled within team groups. Team colour alone cannot separate teammates; the scatter views use circle/triangle marks and position traces use solid/dashed styles. Driver labels remain necessary in static exports.
- Compound colours follow the soft/medium/hard convention, with letter labels so colour is not the only cue. Same-compound changes remain separate sets rather than being merged into one interval.
- The carousel uses a repeatable question sequence instead of a dense five-chart dashboard. A dashboard would make cross-chart comparison faster but create smaller plots on laptops/projectors. Navigation and the visibility of the glossary need audience evaluation.
- Animation presents a compressed recorded timeline and includes a replay action. Reduced-motion preference selects the finished view. A static-first display would reduce waiting and may help reading; compare the two using real audience responses before deciding.
- A boxplot/middle-half summary is compact, but hides lap order. The exploration's race-lap scatter and matched windows supply that context. Density/violin plots offer distribution shape at the cost of smoothing choices and more explanation.
- Tyre-age lines show direction clearly but may imply continuity over excluded laps. Roy's exploration therefore uses points and stint-specific markers. The baseline animated prototype used lines; merged PR #15 switches the story view to points and reports sample counts.

## Merged story update (PR #15)

The merged presentation orders five primary views as stints, pace, tyre age, pit visits against the VSC clock, and event-context panels, then adds a sixth positions view. Each slide has a takeaway and reading guide. Pace uses teammate shapes and sample counts; tyre age uses individual lap points. Pit and event views are static, use recorded session timestamps, and stack at narrower widths. Position values hold the last completed lap rather than interpolating between recorded positions.

Review corrected callout bounds, the normal-lap reference and interpretation of affected laps. The event reference is explicitly the median of eligible laps across the selected drivers' whole race, with its sample size; it is descriptive rather than a controlled local comparison. Amber rings distinguish VSC-affected laps from their completion timestamps, which may fall after the VSC window. Hayden approved head `1e5e03e`; CI and an independent local run passed all 64 tests with the retained snapshot. This verifies behaviour and recorded values, not audience comprehension.

## Interpretation risks to evaluate

The pace caption says a shorter bar means more consistent pace. Test whether viewers incorrectly infer superior driver skill or equal conditions from that phrase; the documented limitation is that compound, race phase, fuel and traffic also affect spread. Likewise, check whether the position traces communicate that observations occur at lap completion. PR #15 removes interpolation of recorded positions, but audience interpretation still requires testing.

Test whether viewers can distinguish a used tyre's age from the length of its current stint, recognise same-compound tyre changes, explain the once-per-lap interval, and separate pit-lane elapsed time from stationary service time. Do not pre-explain these answers during the first reading task. The [feedback protocol](audience-feedback/README.md) and [session template](audience-feedback/SESSION_TEMPLATE.md) record unaided understanding before any clarification.

## Evidence and remaining work

Automated tests check chart values, source counts, driver separation, recorded VSC clock behaviour, rendering, filters and slide navigation. They do not establish text readability on a projector, navigation discoverability or audience understanding. Existing images received assistant visual inspection; that is not a human audience session.

No audience sessions have been collected as of this review. For each session, record the exact build or static file shown, anonymous responses, time to main point, confusing elements and interpretation errors. Link each actual design decision to its response evidence and rerun the relevant checks after changing code or exports. Record a reason when a suggestion is declined or deferred. Keep issue #8 open until the response records and resulting decisions exist.
