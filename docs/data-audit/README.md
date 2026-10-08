# F1 Strategy Visualisation

Group Data Visualisation Project    Data Audit    8 October 2026

We audited FastF1 data for the 2026 Austrian Grand Prix at the Red Bull Ring on 28 June. The comparison contains 426 driver laps with complete core timing and tyre fields. We retain every selected record and mark 361 laps as eligible for initial normal-racing pace analysis. This audit records preparation decisions, not final performance findings.

## Source and provenance

Data were accessed on 8 October 2026 using FastF1 3.8.3 and pandas 2.3.3. The raw download contains 1,339 field laps, results, weather, track status and race-control messages. Telemetry was not downloaded. Raw files remain locally; prepared files and the script are shared in the repository. A SHA-256 hash identifies the raw lap snapshot.

## Selected drivers and coverage

| Team | Driver | Recorded laps | Pace eligible |
| --- | --- | --- | --- |
| Ferrari | HAM | 71 | 61 |
| Ferrari | LEC | 71 | 58 |
| Mercedes | ANT | 71 | 61 |
| Mercedes | RUS | 71 | 60 |
| Red Bull Racing | HAD | 71 | 61 |
| Red Bull Racing | VER | 71 | 60 |

## Missing values and duplicates

No selected lap lacks lap time, compound, tyre age, position, completion time or stint. There are no duplicate driver-lap keys. Sector 1 is missing on six first laps; sectors 2 and 3 are complete. Empty pit timestamps normally mean no pit event on that lap. They are not filled or counted as general missing-data defects.

## Structure and variable types

Each main row represents one recorded driver lap. Track-status, weather and race-control tables contain separate timestamped events. The initial analysis does not use spatial variables. Q denotes quantitative, O ordinal, N nominal and T temporal data.

| Attributes | Type | Interpretation |
| --- | --- | --- |
| Driver, DriverNumber, Team | N | Identifiers; car numbers are categories |
| LapNumber, Position | O | Ordered lap sequence and race position |
| Stint | N | Tyre-stint identifier within a driver’s race |
| Compound, FreshTyre | N | Tyre category and fresh-set flag |
| TyreLife | Q | Age in laps, not measured wear |
| LapTime and sector times | Q | Durations converted to seconds |
| Time, LapStartTime, pit times | T | Session-relative timestamps |
| TrackStatus and quality flags | N | Several status codes can occur on one lap |
| Derived lap-boundary interval | Q | Same-lap timestamp difference, not a live gap |

## Unusual values and validation

Lap times range from 70.374 to 113.381 seconds. Slow laps are retained for inspection. Checks confirm positive durations, increasing lap order, unique keys, source row retention and sector totals within 3 milliseconds on eligible laps. All 14 recorded pit entries pair with a later exit for the same driver.

## Review of the 55 accuracy flags

FastF1’s accuracy logic considers pit activity, track status, sector availability and timing consistency. A false flag does not alone mean a bad record. These mutually exclusive categories account for all 55 flags; pit activity takes priority where categories overlap.

| Category | Laps | Treatment |
| --- | --- | --- |
| Pit-entry or pit-exit laps | 28 | Retain for strategy; exclude from normal pace |
| First laps | 6 | Retain; exclude standing-start laps from normal pace |
| Other status-affected laps | 21 | Retain and annotate; exclude from normal pace |
| Outside these categories | 0 | No residual flagged records in this snapshot |

## Initial pace eligibility rule

An eligible lap must be accurate, green-only and positive in duration, and neither a first lap nor a pit-entry or pit-exit lap. Deleted and generated laps are excluded. This retains 361 laps and excludes 65. The source contains six deleted laps and no generated laps. Status and validity checks explain the difference between 55 accuracy flags and 65 pace exclusions.

## Cleaning and transformations

No values were imputed, duplicates deleted or slow laps trimmed. We select the three teams, order records by driver and lap, convert timings to seconds, and add flags and exclusion reasons. There are 25 VSC-affected and 11 yellow-affected selected laps; these counts overlap. No selected lap contains a full Safety Car flag. Lap-level flags do not specify exact event start or end times.

## Prepared outputs and aggregation

The selected-lap file retains all 426 records. Separate pace and flagged files support different tasks. Stint summaries record driver-level boundaries, compounds and eligible counts; teammates are not averaged together. Pit visits pair entry and exit times. Their 21.042 to 22.742 second intervals measure elapsed pit-lane time, not stationary service time or the causal cost of stopping.

## Prepared dataset preview

| Driver | Lap | Compound | Tyre age | Lap seconds |
| --- | --- | --- | --- | --- |
| ANT | 3 | MEDIUM | 3 | 72.568 |
| HAD | 2 | MEDIUM | 2 | 73.413 |
| HAM | 2 | MEDIUM | 2 | 72.028 |

## Assumptions and limitations

The derived gap compares completion times for the same lap against the earliest full-field completion. Label it as a lap-boundary interval. The loader warned about alignment for driver 77, outside the selected teams, and a 0.530-second session-end discrepancy for driver 63. Investigate effects before using field-reference gaps in final charts. Complete fields do not prove every value is correct.

Fuel load, traffic, weather and track evolution remain confounders. The pace rule is a starting point; stint phase and compound need further checks. Offline reprocessing and three regression tests passed. Human review by Roy and exploratory analysis remain pending.

## Reproduction and sources

Run scripts/prepare_race.py, then use --from-snapshot for offline reprocessing. Run python -m unittest discover -s tests -v after downloading. The repository README explains the outputs.

Repository: https://github.com/haydenteh5526/F1-Strategy-Visualisation

FastF1: https://docs.fastf1.dev/core.html

Official result: https://www.formula1.com/en/results/2026/races/1288/austria/race-result

