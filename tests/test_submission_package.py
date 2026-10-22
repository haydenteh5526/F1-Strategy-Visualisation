"""Detect missing assets and stale evidence in the technical submission package."""
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
import check_submission_package as package  # noqa: E402


class SubmissionPackageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        # Only copy the evidence the checker consumes, plus its relative link targets.
        for name in ['README.md', 'CONTRIBUTING.md']:
            shutil.copy2(ROOT/name, self.root/name)
        for name in ['docs', 'figures', 'data/processed', 'scripts', 'charts']:
            shutil.copytree(ROOT/name, self.root/name)

    def test_committed_package_reports_counts_and_outstanding_acceptance(self):
        result = package.check_package(self.root)
        self.assertEqual(result['technical_checks'], 'passed')
        self.assertEqual(result['selected_laps'], 426)
        self.assertEqual(result['eligible_laps'], 361)
        self.assertEqual(result['matched_pairs'], 126)
        self.assertEqual(len(result['report_figures']), 7)
        self.assertTrue(result['not_verified'])
        self.assertIn('not a final submission approval', result['scope'])

    def test_stale_analysis_value_is_rejected(self):
        file = self.root/'docs/pace-tyre-exploration/pace_summary.csv'
        file.write_text(file.read_text(encoding='utf-8').replace('71.887000', '99.887000'), encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'pace_summary.csv does not reproduce'):
            package.check_package(self.root)

    def test_missing_report_figure_is_rejected(self):
        (self.root/'figures/austria-2026/pace.png').unlink()
        with self.assertRaisesRegex(ValueError, 'missing link target'):
            package.check_package(self.root)

    def test_non_image_in_place_of_png_is_rejected(self):
        (self.root/'figures/austria-2026/pace.png').write_text('not a figure', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'Invalid or empty PNG'):
            package.check_package(self.root)

    def test_missing_local_document_link_is_rejected(self):
        with (self.root/'docs/submission-package/README.md').open('a', encoding='utf-8') as file:
            file.write('\n[Required evidence](missing-evidence.md)\n')
        with self.assertRaisesRegex(ValueError, 'missing-evidence.md'):
            package.check_package(self.root)

    def test_mismatched_installed_raw_snapshot_is_rejected(self):
        path = self.root/'data/raw/austria-2026/laps.csv'
        path.parent.mkdir(parents=True)
        path.write_text('different snapshot', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'raw laps do not match'):
            package.check_package(self.root)


if __name__ == '__main__':
    unittest.main()
