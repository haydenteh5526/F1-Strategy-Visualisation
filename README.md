# F1 Strategy Visualisation

A group data visualisation project for F1 fans, initially studying the 2026 Austrian Grand Prix at the Red Bull Ring. We compare both drivers from Red Bull Racing, Mercedes and Ferrari.

## Current status

The audience brief, data audit and preparation pipeline are on this branch. We retain all 426 selected laps and mark 361 as eligible for initial normal-racing pace comparisons. No final performance findings have been established.

## Research questions

- How do lap times and pace consistency differ during comparable normal racing conditions?
- How does lap time vary with tyre age within stints and compounds?
- How do lap-boundary intervals and positions change around pit stops?
- How do Virtual Safety Car periods affect interpretation?

Fuel load, traffic and conditions also affect lap times. The data cannot isolate causal tyre degradation or prove an optimal strategy.

## Setup and reproduction

Use Python 3.11 or later:

```powershell
py -3.11 -m venv .venv
& ".\.venv\Scripts\python.exe" -m pip install -r requirements.txt
& ".\.venv\Scripts\python.exe" scripts\prepare_race.py
& ".\.venv\Scripts\python.exe" -m unittest discover -s tests -v
```

Hayden can substitute `C:\venv\f1-race-replay\Scripts\python.exe`. The first download requires internet access. The retrieval date is recorded in audit_summary.json.

After downloading, reprocess offline:

```powershell
& ".\.venv\Scripts\python.exe" scripts\prepare_race.py --from-snapshot
```

Tests use the local raw snapshot; without it, the snapshot-dependent tests are skipped. Run the download first.

## Data and documentation

Raw laps, weather, results, race-control messages and track-status events remain locally in ignored `data/raw/austria-2026/`. Download caches are also ignored.

Prepared files in `data/processed/austria-2026/`:

| File | Purpose |
| --- | --- |
| selected_laps.csv | All 426 selected laps, explicit units, flags and eligibility |
| pace_laps.csv | 361 initial normal-racing pace laps |
| flagged_laps.csv | 55 FastF1 accuracy-flagged laps retained for review |
| pit_visits.csv | 14 paired entry/exit records; elapsed pit-lane time, not stationary stop time |
| stints.csv | Driver-level stint boundaries, compounds and eligible-lap counts |
| audit_summary.json | Coverage, validation, source versions, provenance and raw-laps hash |

`GapToEarliestLapCompletionSeconds` compares timestamps for the same lap number against the earliest full-field completion. It is not an instantaneous/live gap. Investigate the full-field alignment warning for driver 77 before using field-reference gaps in final charts.

No missing values are imputed or slow laps automatically removed. Every selected source lap is retained. Columns ending in `Seconds` distinguish durations (LapTimeSeconds) from session-relative timestamps (TimeSeconds). Further comparisons need attention to stint phase, compound, traffic and fuel load.

See `docs/audience-brief/` and `docs/data-audit/`. Public documents omit student IDs. Keep identification details in coursework submission copies.

## Team workflow

Hayden is Head Developer, Roy Second Developer and Sebastian/Tan Shyi Sheng Third Developer. Hayden reviews Sebastian; Roy reviews Hayden; Sebastian reviews Roy. Use feature branches and approved PRs; see [CONTRIBUTING.md](CONTRIBUTING.md).

## Sources

- [FastF1 core documentation](https://docs.fastf1.dev/core.html)
- [Official Austrian GP 2026 result](https://www.formula1.com/en/results/2026/races/1288/austria/race-result)
- [F1 Race Replay](https://github.com/IAmTomShaw/f1-race-replay) as a presentation reference. No reference code has been copied. Attribute future adaptations and retain applicable licence notices.
