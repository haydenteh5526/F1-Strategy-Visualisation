# Coursework decision log

Working disclosure and decision record for Roy's contribution. An existing coursework log or required submission template was not present in this checkout. Transfer these entries into the course's required format before submission; this file does not establish that all coursework disclosure requirements have been met. No student IDs or credentials are recorded here.

## AI assistance and inspection — 20–22 October 2026

At Roy's request, Codex assisted with the standalone tyre-stint plotting script, automated checks and initial chart exports. Subsequent assistance produced the pace/tyre exploration script, comparison tables, figures, regression tests and supporting documentation, and implemented the replay-resize, Windows subprocess-encoding and empty-comparison fixes. Roy committed and pushed the work on `Roys_Branch` and opened PR #16. Main's approved story changes were merged into that branch during integration.

Codex inspected the generated standalone stint PNG and the three exploration PNGs for label readability, legends, markers and layout. It also inspected Sebastian's updated static pace and tyre-age images while reviewing PR #15. These were assistant visual inspections, not human audience sessions or proof of audience understanding. Automated checks supported data consistency and rendering; they do not independently establish source accuracy or causal strategy effects.

The standalone chart keeps drivers identifiable, labels compounds beyond colour and retains same-compound tyre-set changes. The exploration keeps eligible observations separate from all-lap stint accounting and reports race-phase, tyre-age, fuel and traffic limitations. Recorded age is not physical wear; fitted slopes are descriptive.

## Validation and review evidence

- Earlier combined checks passed 59 tests before integration of PR #15. After integration and regression fixes, 81 tests passed with no skips on Windows with Python UTF-8 mode disabled.
- The retained snapshot reproduced the six prepared outputs. Four exploration CSVs also reproduced; Git/Windows line endings must be considered when comparing checkouts. The raw pack lacks `session_status.csv`, so those session-status offsets remain unverified locally.
- Hayden approved PR #16 at head `5e3997c`, reporting no blocking correctness findings and one non-blocking documentation note. His review reports independent checking of the 126 matched teammate pairs, figures and reproduction. That is teammate review evidence, distinct from Codex's checks.
- Roy confirmed that no audience feedback has been collected. Issue #8 remains pending. Do not substitute this log, automated tests or assistant inspection for actual audience responses.

## Documentation decision — 22 October 2026

In response to Hayden's [PR #16 documentation note](https://github.com/haydenteh5526/F1-Strategy-Visualisation/pull/16#discussion_r4342490540), process attribution and assistant-inspection disclosures were moved here from the standalone chart notes, design rationale and issue review. The public method documents retain reproducibility evidence, limitations and the pending audience-feedback status. Disclosure is preserved rather than removed.
