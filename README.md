# F1 Strategy Visualisation

A group data visualisation project investigating Formula 1 race pace, tyre stints and pit-stop timing for fans who want to understand how a race develops.

## Current status

This repository is the starting point for the group's original analysis, charts and documentation. The proposed scope is one completed Grand Prix, with a second race added only if feasible. The group still needs to confirm the race, audience and research questions. No race data has been analysed and no findings have been established.

## Proposed questions

- How does lap-time consistency differ between selected drivers?
- How does lap time change as tyres age within a stint?
- What happens to relative gaps and positions around pit stops?
- How do Safety Car periods affect comparisons of race pace?

These questions are provisional. Lap time also reflects fuel load, traffic and conditions, so changes in lap time alone do not establish tyre degradation or the causal effect of a strategy.

## Local setup

Python 3.11 or later is required. The dependency versions below match the installed environment used during setup.

The existing local environment is `C:\venv\f1-race-replay`. Check it from PowerShell with:

```powershell
& "C:\venv\f1-race-replay\Scripts\python.exe" -m pip check
```

Teammates can create their own environment:

```powershell
py -3.11 -m venv .venv
& ".\.venv\Scripts\python.exe" -m pip install -r requirements.txt
```

There is no analysis script to run yet. The next step is to confirm a Grand Prix and audit its available lap data.

## Data and reproducibility

Planned data access is through [FastF1](https://github.com/theOehrly/Fast-F1). Record the event, session, source, access date, missing values and transformations alongside the analysis. Retain raw data separately from prepared data, document exclusion rules and keep race events identifiable when comparing normal racing pace.

## Reference project

[F1 Race Replay by Tom Shaw and contributors](https://github.com/IAmTomShaw/f1-race-replay) is the reference for interactive replay ideas. Its local clone is in the sibling `f1-race-replay` folder. No reference source code has been copied into this repository. Attribute any code or design adapted later and preserve applicable licence notices.

## Group work and AI use

Assign both primary responsibilities and secondary review responsibilities. All members should understand the data, methods, charts and conclusions. Keep an AI decision log recording meaningful suggestions, how they were verified and why the group accepted, modified or rejected them.
