"""Offline chart checks using the committed prepared data; no raw snapshot needed."""
import importlib.util
from pathlib import Path
import unittest

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("plot_stints", ROOT / "scripts/plot_stints.py")
chart = importlib.util.module_from_spec(spec)
spec.loader.exec_module(chart)


class StintChartTests(unittest.TestCase):
    def setUp(self):
        self.laps = pd.read_csv(chart.DATA_DIR / "selected_laps.csv")
        self.stints = pd.read_csv(chart.DATA_DIR / "stints.csv")
        self.pits = pd.read_csv(chart.DATA_DIR / "pit_visits.csv")

    def test_committed_data_is_consistent(self):
        chart.validate_inputs(self.laps, self.stints, self.pits)
        self.assertEqual((len(self.laps), len(self.stints), len(self.pits)), (426, 20, 14))

    def test_missing_or_duplicate_lap_is_rejected(self):
        for changed in [self.laps.iloc[1:], pd.concat([self.laps, self.laps.iloc[[0]]])]:
            with self.subTest(rows=len(changed)), self.assertRaises(ValueError):
                chart.validate_inputs(changed, self.stints, self.pits)

    def test_off_by_one_boundary_is_rejected(self):
        self.stints.loc[0, "LastLap"] += 1
        with self.assertRaisesRegex(ValueError, "boundaries/count"):
            chart.validate_inputs(self.laps, self.stints, self.pits)

    def test_wrong_compound_is_rejected(self):
        self.stints.loc[0, "Compound"] = "SOFT"
        with self.assertRaisesRegex(ValueError, "compound"):
            chart.validate_inputs(self.laps, self.stints, self.pits)

    def test_shifted_pit_marker_is_rejected(self):
        self.pits.loc[0, "EntryLap"] += 1
        with self.assertRaisesRegex(ValueError, "pit pairs"):
            chart.validate_inputs(self.laps, self.stints, self.pits)

    def test_wrong_pit_timestamp_is_rejected(self):
        self.pits.loc[0, "EntrySeconds"] += 1
        with self.assertRaisesRegex(ValueError, "timestamps disagree"):
            chart.validate_inputs(self.laps, self.stints, self.pits)

    def test_same_compound_stop_cannot_be_dropped(self):
        # VER changes HARD to HARD between laps 49 and 50.
        changed = self.pits.loc[~(self.pits.Driver.eq("VER") & self.pits.EntryLap.eq(49))]
        with self.assertRaisesRegex(ValueError, "pit pairs"):
            chart.validate_inputs(self.laps, self.stints, changed)

    def test_rendered_segments_match_lap_records(self):
        fig = chart.make_chart(self.stints, self.pits)
        try:
            ax = fig.axes[0]
            self.assertEqual(len(ax.patches), 20)
            for y, driver in enumerate(chart.DRIVERS):
                bars = [p for p in ax.patches if abs(p.get_y() + p.get_height()/2 - y) < 1e-8]
                self.assertEqual(sum(p.get_width() for p in bars), 71)
                driver_laps = self.laps.loc[self.laps.Driver.eq(driver)]
                for lap in driver_laps.itertuples(index=False):
                    covering = [p for p in bars if p.get_x() <= lap.LapNumber < p.get_x() + p.get_width()]
                    self.assertEqual(len(covering), 1)
                    expected = chart.matplotlib.colors.to_rgba(chart.COMPOUNDS[lap.Compound][0])
                    self.assertEqual(covering[0].get_facecolor(), expected)
            markers = [line for line in ax.lines if line.get_marker() == "D"]
            actual = sorted((round(float(line.get_ydata()[0]) + .36), float(line.get_xdata()[0])) for line in markers)
            expected = sorted((list(chart.DRIVERS).index(p.Driver), p.EntryLap + .5) for p in self.pits.itertuples())
            self.assertEqual(actual, expected)
            fig.canvas.draw()
            renderer = fig.canvas.get_renderer()
            for label in list(fig.texts) + list(ax.texts) + ax.get_yticklabels() + ax.get_xticklabels() + [ax.xaxis.label]:
                box = label.get_window_extent(renderer)
                self.assertGreaterEqual(box.x0, 0)
                self.assertGreaterEqual(box.y0, 0)
                self.assertLessEqual(box.x1, fig.bbox.width)
                self.assertLessEqual(box.y1, fig.bbox.height)
        finally:
            chart.plt.close(fig)


if __name__ == "__main__":
    unittest.main()
