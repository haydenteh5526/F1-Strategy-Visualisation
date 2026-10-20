# Austria 2026 timing investigation

## Decision

Use the six selected drivers' timestamps for **same-lap completion intervals**, with explicit labelling and race-event context. Do not describe them as instantaneous/live gaps or causal estimates of pit-stop benefit. The two recorded warnings do not require changing the current selected gap values. Human review and the separate offline-reproduction task in issue #3 remain necessary.

## Evidence and warning disposition

### Driver 77 lap alignment

FastF1 3.8.3 `_api._align_laps` attempts to align drivers using the stream's reported gaps. It warns when a driver's offset cannot be established. The retained Bottas data contain only two laps, both accuracy-flagged; they must not be treated as trustworthy comparison data.

None of the 71 earliest-completion references belongs to driver 77. The reference drivers are Russell for 57 laps, Antonelli for eight and Verstappen for six. Every reference has recorded position 1. Removing driver 77 changes the reference and all 426 selected intervals by **0.000 seconds**. The preparation code now excludes that known unaligned driver from this race's reference pool and rejects missing, non-finite, duplicate or position-inconsistent reference data.

### Driver 63 session-end warning

FastF1's retired-driver handling warns when a driver has completed the total race distance before the session-status feed reports `Finished`; that branch returns without adding a lap. This message does not measure a lap-timing integrity failure.

The retained status message is at session time 8626.455 seconds; Russell completes lap 71 at 8625.925 seconds. Their difference is **0.530 seconds**, reproducing the warning. The winner's cumulative lap durations total **5197.979 seconds**, matching the published race time. The other five selected drivers' final completion intervals match the published finishing gaps to the displayed millisecond. Do not shift Russell's times by 0.530 seconds: that would introduce an error into these matching comparisons.

The `Started` message is at 3427.653 seconds, whereas the shared origin reconstructed from completion time minus cumulative lap durations is 3427.946 seconds: a **0.293-second difference**. Thus session-status messages should not define race-duration measurements. Use lap durations and like-for-like completion timestamps; keep their origin distinct from status signalling.

## Checks performed

- The raw laps SHA-256 matches the committed audit snapshot.
- Every selected driver has 71 unique, consecutive lap records and monotonic completion times.
- Each subsequent completion-time difference matches its recorded lap duration within 3 milliseconds.
- All 15 selected driver pairs were compared over all 71 laps: 1,065 comparisons. Timestamp differences agree with differences of cumulative lap durations within floating-point rounding, below 3 milliseconds.
- Reprocessing offline leaves every committed prepared CSV and the audit summary unchanged.
- Published race positions, completed laps and final gaps were independently transcribed into `official_finish_reference.json`; the script does not obtain those expected values from FastF1's own results file.

| Driver | Position | Completed laps | Final interval seconds |
| --- | --- | --- | --- |
| RUS | 1 | 71 | 0.000 |
| VER | 2 | 71 | 1.611 |
| ANT | 3 | 71 | 1.986 |
| HAM | 5 | 71 | 26.393 |
| HAD | 6 | 71 | 29.399 |
| LEC | 8 | 71 | 45.659 |

The cumulative-duration and position checks share the retained timing source; they are internal consistency checks. The independent official checks cover the finish, not every intermediate lap. No independent official lap-by-lap history has been verified in this task.

## Interpretation rules for charts

- Match the **same completed lap number** when subtracting completion timestamps. The drivers cross the line at different moments, so this is an interval at a timing boundary rather than a simultaneous distance/time gap.
- The six selected drivers complete the full distance. Do not apply this interpretation unchanged to lapped cars, retirees or missing laps. A lapped car's same-number lap can finish much later and does not describe its live race deficit. Omit unmatched comparisons; do not fill missing laps or interpolate through a retirement.
- Retain pit and interrupted laps in strategy timelines, but annotate them. A change in interval can combine pit-lane travel, tyre changes, traffic, VSC timing and ordinary pace changes. It does not isolate the benefit of a decision.
- Use the separately defined normal-racing subset for pace analysis. Do not reset timestamps or compress away interruption time when charting race progression.
- Withhold Bottas comparisons, live-gap claims, inferred stationary stop times, and claims of an optimal strategy from these data alone.

## Reproduction

From the repository root with the pinned environment:

```powershell
python scripts/prepare_race.py --from-snapshot
python scripts/validate_timing.py
python -m unittest discover -s tests -v
```

`validate_timing.py` checks the retained raw lap hash, interval arithmetic and the independently recorded finish reference. It writes `validation_summary.json`. If `data/raw/austria-2026/session_status.csv` is present, it also reproduces the status-message offsets. This file was exported from the original retained FastF1 cache; it is included in the updated local raw-data ZIP and is ignored by Git along with the other raw files. If absent, the report explicitly marks status evidence unavailable rather than substituting values.

## Sources

- [Official Formula 1 classification](https://www.formula1.com/en/results/2026/races/1288/austria/race-result)
- [FIA race report and classification](https://api.fia.com/news/f1-russell-wins-closely-contested-austrian-grand-prix-ahead-verstappen-and-antonelli)
- [FastF1 3.8.3 lap-alignment implementation](https://github.com/theOehrly/Fast-F1/blob/v3.8.3/fastf1/_api.py)
- [FastF1 3.8.3 session processing](https://github.com/theOehrly/Fast-F1/blob/v3.8.3/fastf1/core.py)
