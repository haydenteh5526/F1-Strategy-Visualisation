"""Check the technical submission contents offline; this is not final acceptance."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import struct
from urllib.parse import unquote, urlsplit

import pandas as pd
from pandas.testing import assert_frame_equal

from explore_pace_tyres import analyse

ROOT = Path(__file__).resolve().parents[1]
DOCUMENTS = ('README.md', 'docs/visual-report/README.md', 'docs/submission-package/README.md')
TABLES = ('pace_summary', 'matched_laps', 'matched_windows', 'stint_summary')


def local_links(document: Path, root: Path) -> list[Path]:
    """Check file/image targets without following remote links or testing web availability."""
    files = []
    for target in re.findall(r'\]\(([^)]+)\)', document.read_text(encoding='utf-8')):
        target = target.strip().strip('<>')
        parts = urlsplit(target)
        if parts.scheme or parts.netloc or not parts.path:
            continue
        resolved = (document.parent/unquote(parts.path)).resolve()
        if not resolved.is_relative_to(root.resolve()):
            raise ValueError(f'{document.relative_to(root)}: target outside the package: {target}')
        if not resolved.exists():
            raise ValueError(f'{document.relative_to(root)}: missing link target: {target}')
        files.append(resolved)
    return files


def check_package(root: Path = ROOT) -> dict:
    root = root.resolve()
    data = root/'data/processed/austria-2026'
    summary = json.loads((data/'audit_summary.json').read_text(encoding='utf-8'))
    laps = pd.read_csv(data/'selected_laps.csv', dtype={'TrackStatus': str})
    for key, actual in [('selected_rows', len(laps)), ('pace_eligible', int(laps.EligibleForPace.sum()))]:
        if summary[key] != actual:
            raise ValueError(f'Audit {key} disagrees with the selected laps')
    if not summary.get('provenance', {}).get('access_date') or not summary.get('raw_laps_sha256'):
        raise ValueError('Missing source access date or raw-snapshot hash')

    generated = analyse(laps)
    for name in TABLES:
        saved = pd.read_csv(root/f'docs/pace-tyre-exploration/{name}.csv')
        # CSV values are rounded to six decimal places; compare values, not OS line endings.
        try:
            assert_frame_equal(saved, generated[name], check_dtype=False, check_exact=False,
                               atol=.00000051, rtol=0)
        except AssertionError as error:
            raise ValueError(f'{name}.csv does not reproduce from selected_laps.csv') from error

    linked = set()
    for relative in DOCUMENTS:
        document = root/relative
        if not document.is_file():
            raise ValueError(f'Missing package document: {relative}')
        linked.update(local_links(document, root))
    report = root/'docs/visual-report/README.md'
    images = re.findall(r'!\[[^\]]*\]\(([^)]+)\)', report.read_text(encoding='utf-8'))
    if not images:
        raise ValueError('The visual report contains no figure references')
    figures = []
    for target in images:
        path = (report.parent/unquote(urlsplit(target).path)).resolve()
        content = path.read_bytes()
        if len(content) < 24 or content[:8] != b'\x89PNG\r\n\x1a\n' or content[12:16] != b'IHDR':
            raise ValueError(f'Invalid or empty PNG figure: {path.relative_to(root)}')
        width, height = struct.unpack('>II', content[16:24])
        if not width or not height:
            raise ValueError(f'PNG figure has invalid dimensions: {path.relative_to(root)}')
        figures.append({'file': path.relative_to(root).as_posix(), 'width': width, 'height': height,
                        'sha256': hashlib.sha256(content).hexdigest()})

    raw = root/'data/raw/austria-2026/laps.csv'
    raw_check = 'unavailable (raw snapshot not installed)'
    if raw.exists():
        if hashlib.sha256(raw.read_bytes()).hexdigest() != summary['raw_laps_sha256']:
            raise ValueError('Installed raw laps do not match the committed audit hash')
        raw_check = 'matches audit hash'
    return {
        'technical_checks': 'passed',
        'source_access_date': summary['provenance']['access_date'],
        'selected_laps': len(laps), 'eligible_laps': int(laps.EligibleForPace.sum()),
        'matched_pairs': len(generated['matched_laps']),
        'analysis_tables_reproduced': list(TABLES),
        'documents_checked': list(DOCUMENTS), 'local_link_targets_checked': len(linked),
        'report_figures': figures, 'raw_snapshot': raw_check,
        'scope': 'Local technical consistency only; not a final submission approval.',
        'not_verified': [
            'Audience responses, interpretation and evidence-linked revisions (#8).',
            'Acceptance of the guided story and accessibility changes (#18/#19).',
            'Visual readability and agreement of each figure with the final dashboard.',
            'Human contribution records, presentation, required coursework PDFs and archive (#20).',
            'External URL availability, Markdown anchor IDs and immutable remote reference contents.',
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--output', type=Path, help='Optional JSON evidence file; stdout is always printed')
    args = parser.parse_args()
    try:
        result = check_package(args.root)
    except (ValueError, OSError, KeyError) as error:
        parser.exit(1, f'Package check failed: {error}\n')
    text = json.dumps(result, indent=2)+'\n'
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding='utf-8')
    print(text, end='')


if __name__ == '__main__':
    main()
