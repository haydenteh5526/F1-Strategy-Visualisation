# Dashboard integration

The five planned views remain in their existing order. This update integrates the reviewed pace/tyre evidence without changing preparation, eligibility or the pit/VSC calculations.

| Planned view | Existing implementation retained | Integration change |
| --- | --- | --- |
| Tyre stints | Driver rows, compound letters, separate same-compound sets, strategy table | Retained; detailed stint accounting is available alongside the tyre-age view |
| Comparable pace | Whole-race median and middle-half overview with driver shapes and sample counts | Added an explicit alternative for same-lap, same-compound teammate comparisons in four fixed windows |
| Lap time and tyre age | Eligible individual lap points within driver panels | Added all-stint accounting, including used-set starting ages, recorded and eligible counts; static labels now identify stint numbers |
| Pit visits and VSC clock | Recorded deployment/ending/clear times, all-visit table and boundary caution | Retained unchanged |
| Event context | Lap-completion observations, affected-lap rings, position and lap-boundary interval panels | Retained unchanged; affected laps can finish beyond the status shading |

## Matched comparisons

Windows are laps 1–20, 21–40, 41–60 and 61–71, as in the reviewed exploration. Within each team, A and B are alphabetically ordered driver codes. Both observations must be eligible, on the same race lap and on the same compound. The point is the median of the individual A − B lap-time differences. It is not a difference between whole-race medians. Negative means A was faster.

The table supplies the number of pairs and minimum/maximum recorded tyre-age differences using the same A − B direction. A negative age difference means A had younger tyres. These ranges are descriptive, not confidence intervals. Diamonds mark fewer than five pairs as a reading caution, not a statistical threshold. No point is invented when there are no pairs.

The dashboard recalculates comparisons from the selected teams' prepared laps. Tests compare every resulting window with `docs/pace-tyre-exploration/matched_windows.csv`: 126 pairs across 11 groups. For Mercedes, the initial Medium window has 16 pairs and a median A − B of +0.155 s; the final Hard window has 11 pairs and −0.883 s, with A's tyres eight recorded laps younger. Matching does not control tyre age, fuel, traffic or car differences and cannot establish an optimal strategy.

## Stint accounting

The tyre-age view retains every stint in its table, including any with zero eligible observations. Recorded laps include excluded laps; eligible laps count the plotted pace observations. Hamilton's third stint has 17 recorded laps, 15 eligible observations and a starting recorded age of three because the Soft set was used. Stint number distinguishes separate sets of the same compound. Recorded tyre age is not measured wear.

## Reproduction and static outputs

From the repository root, with the pinned requirements installed:

```powershell
python -m streamlit run app/story.py
python scripts/export_figures.py
python -m unittest discover -s tests -v
```

The first command starts the dashboard. The exporter produces six images: the existing five exports plus `figures/austria-2026/pace-matched.png`. The matched image contains explicit panels for Medium and Hard in all four windows, including empty panels. Soft has no matched eligible pairs; the dashboard reports this when selected. Static tyre-age labels include stint numbers. The matched image and dashboard use the same aggregation and chart function. Hover details are supplemented by the dashboard table; use that table or the committed comparison CSV for the numeric tyre-age ranges when presenting the static image.

The recorded-clock pit and event exploration figures remain in `figures/austria-2026/pit-vsc/`, reproduced with `python scripts/explore_pit_vsc.py` and the retained raw snapshot. The generic `vsc.png` and `positions.png` exports remain supplementary views, not replacements for the clock-based evidence.

Relevant checks cover agreement with reviewed window/stint tables, zero-eligible selections, team filtering, the empty-compound message, both chart themes, static rendering and existing replay behaviour. Technical checks do not establish audience understanding. Audience sessions remain under #8, story refinement under #18 and broader usability checks under #19.
