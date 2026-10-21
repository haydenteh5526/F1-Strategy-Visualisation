"""Run the story interface headlessly and check what it shows."""
from pathlib import Path
import re
import sys
import unittest

import pandas as pd
from streamlit.testing.v1 import AppTest

APP = Path(__file__).resolve().parents[1]/'app/story.py'
sys.path.insert(0, str(APP.parent))
import charts  # noqa: E402


class StoryAppTests(unittest.TestCase):
    def setUp(self):
        self.app = AppTest.from_file(str(APP), default_timeout=30).run()

    def go_to(self, slide):
        while self.app.session_state.slide != slide:
            self.app.button(key='next').click().run()
        self.assertFalse(self.app.exception)

    def test_every_slide_shows_one_chart(self):
        titles = set()
        for slide in range(6):
            self.go_to(slide)
            replays = [f for f in self.app.get('iframe') if 'Race replay' in str(f.proto)]
            charts_shown = len(self.app.get('vega_lite_chart'))+len(replays)
            self.assertEqual(charts_shown, 1)
            titles.add(self.app.subheader[0].value)
        self.assertEqual(len(titles), 6)

    def test_arrows_wrap_around(self):
        self.app.button(key='previous').click().run()
        self.assertEqual(self.app.session_state.slide, 5)
        self.app.button(key='next').click().run()
        self.assertEqual(self.app.session_state.slide, 0)

    def test_race_facts(self):
        cards = next(h.proto.body for h in self.app.get('html') if 'f1-facts' in h.proto.body)
        facts = dict(re.findall(r'class="label">([^<]+)</div><div class="value" data-value="([^"]+)"', cards))
        self.assertEqual(facts['Race laps'], '71')
        self.assertEqual(facts['Pit stops, selected teams'], '14')
        self.assertEqual(facts['Virtual Safety Car periods'], '2')

    def test_strategy_table_matches_stints(self):
        strategy = self.app.dataframe[0].value.set_index('Driver')
        self.assertEqual(len(strategy), 6)
        self.assertEqual(strategy.loc['HAM', 'Tyres (laps)'],
                         'Medium 1–12 → Hard 13–25 → Soft (used) 26–42 → Hard 43–71')
        self.assertEqual(strategy['Pit stops'].sum(), 14)

    def test_team_filter_limits_tables(self):
        self.app.multiselect[0].set_value(['Ferrari']).run()
        for slide in [0, 3]:
            self.go_to(slide)
            self.assertEqual(set(self.app.dataframe[0].value.Team), {'Ferrari'})

    def test_pace_chart_values_match_prepared_data(self):
        pace = pd.read_csv(APP.parents[1]/'data/processed/austria-2026/pace_laps.csv')
        summary = charts.pace_summary(pace).set_index('Driver')
        for driver, laps in pace.groupby('Driver'):
            self.assertAlmostEqual(summary.loc[driver, 'Typical'], laps.LapTimeSeconds.median())
            self.assertEqual(summary.loc[driver, 'Laps'], len(laps))

    def test_slides_follow_the_design_plan_order(self):
        order = []
        for slide in range(6):
            self.go_to(slide)
            order.append(self.app.subheader[0].value)
        self.assertEqual([title.split('.')[0] for title in order[:5]], ['1', '2', '3', '4', '5'])
        self.assertTrue(order[5].startswith('Extra'))

    def test_pit_slide_states_the_main_message_and_the_counts(self):
        self.go_to(3)
        message = ' '.join(box.value for box in self.app.info)
        self.assertIn('requires the recorded event clock', message)
        self.assertTrue(any('3 have a VSC flag on the entry or exit lap, but 1 overlap' in m.value for m in self.app.markdown))

    def test_every_slide_explains_itself_in_plain_english(self):
        for slide in range(6):
            self.go_to(slide)
            boxes = [h.proto.body for h in self.app.get('html') if 'f1-takeaway' in h.proto.body]
            self.assertEqual(len(boxes), 1, slide)
            self.assertIn('How to read this', boxes[0])
            self.assertIn('What to notice', boxes[0])

    def test_takeaways_state_the_numbers_in_the_data(self):
        def takeaway():
            body = next(h.proto.body for h in self.app.get('html') if 'f1-takeaway' in h.proto.body)
            return body.split('class="big">')[1].split('</div>')[0]
        self.go_to(1)
        self.assertIn('ANT was quickest (71.64 s)', takeaway())
        self.go_to(3)
        self.assertIn('only 1 (HAM on lap 25)', takeaway())
        self.go_to(4)
        self.assertIn("HAD's lap 25 at 100.5 s", takeaway())

    def test_vsc_laps_are_summarised(self):
        self.go_to(4)
        self.assertTrue(any('laps 24–26, 52–53' in text.value for text in self.app.markdown))


if __name__ == '__main__':
    unittest.main()
