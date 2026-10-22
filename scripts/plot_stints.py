"""Validate and plot the six-driver Austria 2026 tyre-stint timeline offline."""
from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data/processed/austria-2026"
OUTPUT_DIR = ROOT / "charts/austria-2026"
DRIVERS = {
    "VER": "Red Bull Racing", "HAD": "Red Bull Racing",
    "RUS": "Mercedes", "ANT": "Mercedes",
    "LEC": "Ferrari", "HAM": "Ferrari",
}
COMPOUNDS = {"SOFT": ("#e56b73", "S"), "MEDIUM": ("#f2cf5b", "M"),
             "HARD": ("#e2e8ef", "H")}
RACE_LAPS = 71


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def validate_inputs(laps: pd.DataFrame, stints: pd.DataFrame,
                    pits: pd.DataFrame) -> None:
    """Cross-check summaries and pit markers against every prepared driver lap.

    This checks the committed prepared data, not the unavailable raw source.
    The strict 71-lap, six-driver contract is specific to this race chart.
    """
    for name, frame, columns in [
        ("laps", laps, ["Driver", "Team", "LapNumber", "Stint", "Compound",
                        "IsPitInLap", "IsPitOutLap", "PitInTimeSeconds", "PitOutTimeSeconds"]),
        ("stints", stints, ["Driver", "Team", "Stint", "Compound", "FirstLap",
                            "LastLap", "RecordedLaps"]),
        ("pits", pits, ["Driver", "Team", "EntryLap", "ExitLap", "EntrySeconds", "ExitSeconds"]),
    ]:
        require(set(columns).issubset(frame.columns), f"{name}: required columns missing")
        required = [c for c in columns if c not in ("PitInTimeSeconds", "PitOutTimeSeconds")]
        require(not frame[required].isna().any().any(), f"{name}: missing chart values")
        require(set(frame.Driver) == set(DRIVERS), f"{name}: expected six selected drivers")
        require(frame.Team.eq(frame.Driver.map(DRIVERS)).all(), f"{name}: driver/team mismatch")

    require(not laps.duplicated(["Driver", "LapNumber"]).any(), "Duplicate driver/lap keys")
    require(not stints.duplicated(["Driver", "Stint"]).any(), "Duplicate driver/stint keys")
    require(stints.Compound.isin(COMPOUNDS).all(), "Unsupported tyre compound")
    require(not pits.duplicated(["Driver", "EntryLap"]).any(), "Duplicate pit entries")
    require(not pits.duplicated(["Driver", "ExitLap"]).any(), "Duplicate pit exits")
    for flag, timestamp in [("IsPitInLap", "PitInTimeSeconds"),
                            ("IsPitOutLap", "PitOutTimeSeconds")]:
        require(laps[flag].isin([True, False]).all(), f"Invalid {flag} flag")
        require(laps[flag].eq(laps[timestamp].notna()).all(), f"{flag} disagrees with timestamps")

    for driver in DRIVERS:
        driver_laps = laps.loc[laps.Driver.eq(driver)].sort_values("LapNumber")
        driver_stints = stints.loc[stints.Driver.eq(driver)].sort_values("FirstLap")
        driver_pits = pits.loc[pits.Driver.eq(driver)].sort_values("EntryLap")
        require(driver_laps.LapNumber.tolist() == list(range(1, RACE_LAPS + 1)),
                f"{driver}: expected complete laps 1–71")
        require(set(driver_laps.Stint) == set(driver_stints.Stint),
                f"{driver}: stint identifiers disagree")
        next_lap = 1
        for stint in driver_stints.itertuples(index=False):
            actual = driver_laps.loc[driver_laps.Stint.eq(stint.Stint)]
            require(stint.FirstLap == next_lap and stint.LastLap >= stint.FirstLap,
                    f"{driver}: stint boundary gap or overlap")
            require(stint.FirstLap == actual.LapNumber.min()
                    and stint.LastLap == actual.LapNumber.max()
                    and stint.RecordedLaps == len(actual)
                    and stint.RecordedLaps == stint.LastLap - stint.FirstLap + 1,
                    f"{driver}: stint boundaries/count disagree with laps")
            require(actual.Compound.eq(stint.Compound).all(),
                    f"{driver}: stint compound disagrees with laps")
            next_lap = stint.LastLap + 1
        require(next_lap == RACE_LAPS + 1, f"{driver}: stints do not cover the full race")

        # Preserve tyre-set changes even when the compound stays the same.
        boundaries = list(zip(driver_stints.LastLap.iloc[:-1], driver_stints.FirstLap.iloc[1:]))
        recorded_pairs = list(zip(driver_pits.EntryLap, driver_pits.ExitLap))
        require(recorded_pairs == boundaries, f"{driver}: pit pairs disagree with stint transitions")
        require(driver_pits.EntryLap.tolist() == driver_laps.loc[driver_laps.IsPitInLap, "LapNumber"].tolist(),
                f"{driver}: pit entries disagree with lap flags")
        require(driver_pits.ExitLap.tolist() == driver_laps.loc[driver_laps.IsPitOutLap, "LapNumber"].tolist(),
                f"{driver}: pit exits disagree with lap flags")
        indexed = driver_laps.set_index("LapNumber")
        for pit in driver_pits.itertuples(index=False):
            require(np.isfinite([pit.EntrySeconds, pit.ExitSeconds]).all()
                    and pit.ExitSeconds > pit.EntrySeconds,
                    f"{driver}: invalid pit timestamps")
            require(np.isclose(pit.EntrySeconds, indexed.loc[pit.EntryLap, "PitInTimeSeconds"], rtol=0, atol=1e-6)
                    and np.isclose(pit.ExitSeconds, indexed.loc[pit.ExitLap, "PitOutTimeSeconds"], rtol=0, atol=1e-6),
                    f"{driver}: pit timestamps disagree with laps")


def make_chart(stints: pd.DataFrame, pits: pd.DataFrame):
    """Each lap occupies one unit centred on its numbered tick.

    Pit diamonds sit between the entry and exit lap cells; they do not encode
    exact within-lap timing or pit-lane duration.
    """
    with plt.rc_context({"font.family": "DejaVu Sans", "font.size": 11,
                         "svg.fonttype": "none"}):
        fig, ax = plt.subplots(figsize=(14, 8.5), facecolor="#f8fafc")
        fig.subplots_adjust(left=.19, right=.965, top=.76, bottom=.23)
        ax.set_facecolor("#f8fafc")
        for y, driver in enumerate(DRIVERS):
            for stint in stints.loc[stints.Driver.eq(driver)].sort_values("FirstLap").itertuples(index=False):
                colour, short = COMPOUNDS[stint.Compound]
                width = stint.LastLap - stint.FirstLap + 1
                ax.barh(y, width, left=stint.FirstLap - .5, height=.52,
                        color=colour, edgecolor="#475569", linewidth=1, zorder=3)
                ax.text((stint.FirstLap + stint.LastLap) / 2, y,
                        f"{short} · {int(width)} laps", ha="center", va="center",
                        fontsize=10, color="#172033", zorder=4)
            for pit in pits.loc[pits.Driver.eq(driver)].itertuples(index=False):
                boundary = pit.EntryLap + .5
                ax.plot([boundary, boundary], [y - .28, y + .28], color="#172033", lw=1.5, zorder=5)
                ax.plot(boundary, y - .36, marker="D", ms=4, color="#172033", zorder=5)
                ax.text(boundary, y - .54, f"L{int(pit.EntryLap)}", ha="center", va="center",
                        fontsize=9, color="#334155")
        ax.set_yticks(range(len(DRIVERS)), [f"{driver}   {team}" for driver, team in DRIVERS.items()])
        ax.tick_params(axis="y", length=0, pad=12, labelsize=11)
        ax.set_ylim(5.7, -.85)
        ax.set_xlim(.5, RACE_LAPS + .5)
        ax.set_xticks([1, 10, 20, 30, 40, 50, 60, 71])
        ax.set_xlabel("Race lap", labelpad=12, color="#334155")
        ax.tick_params(axis="x", colors="#475569")
        ax.set_axisbelow(True)
        ax.grid(axis="x", color="#dce3eb", linewidth=.8)
        for divider in [1.65, 3.65]:
            ax.axhline(divider, color="#dce3eb", lw=1)
        for spine in ax.spines.values():
            spine.set_visible(False)
        fig.text(.045, .94, "AUSTRIA 2026  /  RACE STRATEGY", fontsize=11, weight="bold", color="#526477")
        fig.text(.045, .89, "Tyre stints across 71 laps", fontsize=25, weight="bold", color="#172033")
        fig.text(.045, .845, "Six drivers · 20 tyre stints · 14 pit visits", fontsize=12, color="#526477")
        handles = [Patch(facecolor=c, edgecolor="#475569", label=f"{s}  {name.title()}")
                   for name, (c, s) in COMPOUNDS.items()]
        handles.append(Line2D([], [], marker="D", color="#172033", linestyle="None", ms=5,
                              label="Pit entry lap (L#)"))
        fig.legend(handles=handles, loc="lower left", bbox_to_anchor=(.185, .125),
                   ncol=4, frameon=False, fontsize=10)
        fig.text(.045, .092, "A stint is a continuous run on one tyre set. Segment labels show compound and recorded race laps, not tyre age.",
                 fontsize=10, color="#475569")
        fig.text(.045, .061, "Pit markers sit between entry and exit laps; they do not show exact stop timing or duration. All laps are retained.",
                 fontsize=10, color="#475569")
        fig.text(.045, .030, "Source: retained FastF1 snapshot · Prepared data reproduced byte-for-byte; all 426 selected laps retained.",
                 fontsize=9, color="#64748b")
        return fig


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=DATA_DIR)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    args = parser.parse_args()
    laps = pd.read_csv(args.data_dir / "selected_laps.csv")
    stints = pd.read_csv(args.data_dir / "stints.csv")
    pits = pd.read_csv(args.data_dir / "pit_visits.csv")
    validate_inputs(laps, stints, pits)
    fig = make_chart(stints, pits)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for extension in ("png", "svg"):
        path = args.output_dir / f"tyre_stints.{extension}"
        fig.savefig(path, dpi=180, facecolor=fig.get_facecolor())
        print(f"Saved {path}")
    plt.close(fig)
    print(f"Validated {len(laps)} laps, {len(stints)} stints and {len(pits)} pit visits across six drivers.")


if __name__ == "__main__":
    main()
