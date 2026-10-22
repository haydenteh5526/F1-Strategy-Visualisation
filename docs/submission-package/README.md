# Visual package preparation

This is working material for issue #20, not a final-release declaration. The [draft visual report](../visual-report/README.md) brings the five planned views together with evidence, encodings, alternatives and interpretation limits. It uses merged main `f29be98`; pending PR #22 changes are excluded.

## Technical contents

| Item | Location |
| --- | --- |
| Prepared data and provenance | `data/processed/austria-2026/` |
| Preparation and timing validation | `scripts/prepare_race.py`, `scripts/validate_timing.py` |
| Pace and tyre exploration | `scripts/explore_pace_tyres.py`, `docs/pace-tyre-exploration/` |
| Pit and VSC exploration | `scripts/explore_pit_vsc.py`, `docs/pit-vsc-exploration/` |
| Dashboard | `app/story.py` and its local modules |
| Static export command | `scripts/export_figures.py` |
| Stints, pace, matched pace and tyre-age images | `figures/austria-2026/` |
| Recorded-clock pit and event images | `figures/austria-2026/pit-vsc/` |
| Installation, run commands and limitations | Root `README.md`, `requirements.txt` |

The five primary views are stints, comparable pace (overview plus matched panels), tyre age, recorded pit/VSC timing and event context. The generic `positions.png` and `vsc.png` are supplementary views; they do not replace the recorded-clock event figures. A multi-panel figure remains part of its corresponding audience task rather than an artificial extra chart type.

## Reproduce from the repository root

```powershell
python -m pip install -r requirements.txt
python -m streamlit run app/story.py
python scripts/export_figures.py
python scripts/explore_pace_tyres.py
python -m unittest discover -s tests -v
```

For full offline reproduction, install the original retained files locally in `data/raw/austria-2026/`, then run `python scripts/prepare_race.py --from-snapshot`, `python scripts/validate_timing.py` and `python scripts/explore_pit_vsc.py`. Missing raw files can cause raw-dependent tests to skip. Do not assume a fresh download is available; the retained snapshot and its audit hash are the reproduction source.

Raw snapshots, environments and credentials remain outside Git. Coursework copies with student identifiers and individual records are managed in the team's submission folder, not in this public directory.

## Remaining acceptance work

- Resolve the contrast and accessible-title findings on PR #22 and verify the accepted version.
- Complete real audience sessions and evidence-linked decisions under #8; the protocol is available but responses remain pending.
- Review the final message, dashboard, static sequence, captions and reference versions together.
- Confirm the remaining charter arrangements and complete the presentation and individual coursework records.
- Re-export and visually check the final PDFs before replacing the cumulative weekly submission.

The separate coursework checklist maps all required submission stages and the oral defence. The visual report is supporting material, not an invented extra mandatory long report. Keep #20 open until the final package and its dependent evidence are complete.
