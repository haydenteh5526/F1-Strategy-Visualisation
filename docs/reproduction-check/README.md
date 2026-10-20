# F1 Strategy Visualisation

Group Data Visualisation Project    Raw Snapshot Reproduction Check

This note records the issue #3 check: can the prepared Austria 2026 data be rebuilt from the retained raw snapshot without downloading the race again? Checked against main at commit dcc7e50.

## Environment

- Windows 11, Python 3.12.3 in a project virtual environment.
- Pinned packages from requirements.txt: FastF1 3.8.3, pandas 2.3.3, numpy 2.4.6, matplotlib 3.11.2.
- Raw snapshot from Hayden's raw-data ZIP: laps, results, weather, track status, race-control messages and provenance.

## Steps

1. Copy the raw files into `data/raw/austria-2026/`, which Git ignores.
2. Compare the SHA-256 hash of laps.csv with `raw_laps_sha256` in audit_summary.json.
3. Rebuild the prepared files offline:

   ```powershell
   & ".\.venv\Scripts\python.exe" scripts\prepare_race.py --from-snapshot
   ```

4. Compare the rebuilt files in `data/processed/austria-2026/` with the committed versions using `git status` and `git diff`.
5. Run the full test suite:

   ```powershell
   & ".\.venv\Scripts\python.exe" -m unittest discover -s tests -v
   ```

## Results

- The laps.csv hash matches the committed audit (`4e3286…c6841e`), and provenance.json matches the committed provenance.
- All six prepared files, including audit_summary.json, were rebuilt byte for byte. Git reported no changes.
- All 16 tests passed: the 13 prepared-data tests and the 3 snapshot regression tests.

## Limitations

- This confirms reproduction from the same retained source. It does not check the timing data against official results.
- Python 3.12.3 was used rather than the 3.11 minimum.
- The snapshot did not include session_status.csv, which PR #9 uses for its status-message offsets. Those offsets were not reproduced here.
