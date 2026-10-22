# Review of open issues #5, #6 and #8

Reviewed on 21 October 2026 against `Roys_Branch` at `818e132` and the current GitHub issue descriptions. Implementation for #5/#6 is proposed in [PR #16](https://github.com/haydenteh5526/F1-Strategy-Visualisation/pull/16). Its unittest, reviewer-request and security checks passed at review time; no approving review was recorded. These statuses are a dated snapshot.

“Implemented” below means the evidence is present on this branch, awaiting teammate review and merge. It does not mean the GitHub issue is closed or the work is on main.

## #5 — Explore driver pace and lap-time consistency

| Completion criterion | Status | Evidence |
| --- | --- | --- |
| Document eligibility and per-driver counts | Implemented | [Analysis notes](pace-tyre-exploration/README.md#eligibility-and-samples), `pace_summary.csv`; 361 eligible observations from 426 retained laps |
| Pace-over-lap and distribution views, individual drivers identifiable | Implemented | `pace_by_lap.png` with teammate shapes and `pace_distribution.png` with driver labels in [the exploration directory](pace-tyre-exploration/) |
| Appropriate race windows, compound or stint comparisons | Implemented | `matched_laps.csv` and `matched_windows.csv`: exact same-lap, same-compound, eligible teammate pairs in fixed race windows; tyre ages retained |
| Consider traffic, fuel and interruptions | Implemented with limits | [Alternative explanations](pace-tyre-exploration/README.md#alternative-explanations-and-design-choices); no measured fuel or traffic adjustment is claimed |
| Reproducible code, figures and observations/limits | Implemented | `scripts/explore_pace_tyres.py`, four CSVs, three PNGs and the analysis notes |
| At least one alternative chart and trade-off | Implemented | Violin/density alternative versus the chosen boxplot and race-lap scatter, described in the analysis notes |

No additional chart implementation is missing from this checklist. Teammates still need to review the methods and interpretation in PR #16 before merging and closing #5.

## #6 — Explore tyre stints and lap time against tyre age

| Completion criterion | Status | Evidence |
| --- | --- | --- |
| Driver-level timeline, compounds, stint boundaries and pit laps | Implemented | `scripts/plot_stints.py`, [timeline and reading guide](../charts/austria-2026/README.md); all 20 stints and 14 pit visits validated |
| Lap time against age within driver/stint/compound | Implemented | `tyre_age.png` and `stint_summary.csv`; one eligible-lap point per observation, separate marker per stint |
| Sample sizes versus recorded stint lengths | Implemented | Per-stint eligible/recorded counts in the legend and table; total 361 eligible versus 426 recorded laps |
| Fresh/used information; age distinguished from wear | Implemented | `FreshTyreAtStart` and recorded age columns, used-set labels and the Hamilton/Leclerc examples in the notes |
| Race phase, fuel and traffic explanations | Implemented with limits | The same-lap comparison tables and [limitations](pace-tyre-exploration/README.md#alternative-explanations-and-design-choices); within-stint slope is descriptive, not a wear estimate |
| Reproducible code, figures, alternatives and evidence note | Implemented | Both plotting scripts, generated exports and the connected-line/pooled-trend alternatives discussed in the notes |

No additional chart implementation is missing from this checklist. Human interpretation review and approval of PR #16 remain pending before merging and closing #6.

## #8 — Draft layout and check audience understanding

The existing `app/story.py`, theme, replay and static exports cover the prototype requirements already checked in the issue: desktop sequence, driver identities, terminology, units, source and limitations. [The design rationale](design-rationale.md) records the baseline layout, the subsequent story update, alternatives and known interpretation limits. [PR #15](https://github.com/haydenteh5526/F1-Strategy-Visualisation/pull/15) is now merged into main at `b61a8e3`, after approval of head `1e5e03e` and 64 passing tests. This branch incorporates that merge through integration commit `65bf96d`. Audience feedback remains pending independently of the implementation merge.

| Remaining criterion | Status | Next action |
| --- | --- | --- |
| Ask teammates/F1 fans to explain the charts and record responses | **Pending** | Collect real responses using the [feedback form](audience-feedback/README.md) and [session template](audience-feedback/SESSION_TEMPLATE.md) |
| Save prototype, feedback notes and alternatives for rationale | **Partly complete** | Prototype and rationale are present; completed feedback records and resulting revisions await sessions |

No audience feedback has been collected. Do not check these requirements off or close #8 until actual anonymous responses and resulting design decisions are recorded. Automated validation does not establish audience understanding.

## Validation and review boundary

The baseline combined suite has 59 passing tests with no skips on this Windows checkout. Five analysis tests check eligibility independence, matching correctness/completeness, retained counts and tyre sets, used ages, duplicates and within-stint slope isolation. Eight standalone chart tests validate data and rendered geometry. Existing app, export, replay, preparation and timing tests also pass. These checks support reproducibility and behaviour, not audience comprehension or causal strategy claims.

All six prepared outputs were previously reproduced byte-for-byte from the retained snapshot after updating to main `ce8a0a1`. Session-status offsets remain unverified because the raw pack lacks `session_status.csv`.

This review adds documentation only. It does not change eligibility, analysis results, charts, the app, GitHub checkboxes or PR approvals. Review the evidence in PR #16; retain the normal approval requirement before merging.


## Regression fixes after integration

The combined Roy/main checkout now passes **81 tests with no skips**, run with `python -X utf8=0 -m unittest discover -s tests -v` on Windows. Replay subprocess input/output explicitly uses UTF-8, so Unicode labels no longer depend on Python UTF-8 mode. All four animated views redraw at their current race time after resizing, including midway through playback and at the finished frame. Exact teammate comparisons return empty tables with headers when no pairs match, and driver summaries retain zero-eligible drivers and all recorded-lap counts. Regression tests cover these cases. All four existing exploration CSVs reproduce byte-for-byte; no analysis results or exports were changed. Audience feedback remains pending.
