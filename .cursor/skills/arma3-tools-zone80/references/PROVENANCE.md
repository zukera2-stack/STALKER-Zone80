# Evidence contract

Keep raw Windows reports and screenshots only in ignored reports/. Do not upload local user paths, protected P3D/PAA/PBO, third-party GIS imagery, credentials or licenses.

Levels of evidence:
1. SOURCE REVIEW: documentation or code read, no run.
2. OFFLINE CONTRACT TEST: Python/.NET checks of ASC/CSV/TML structure.
3. WINDOWS TOOL RUN: exact binary executed with logs and version.
4. TB GUI IMPORT / ENGINE LOAD: observed editor/game state with project snapshot and evidence.

Report PASS/PARTIAL/FAIL/NOT TESTED at each level. Report source SHA, tool versions, commands, hashes, inputs/outputs, observed process memory method and unresolved assumptions.

Current baseline:
- GIS-04: PR #12 has 4/4 offline tests in CI, GM26.2 Windows reported.
- GRM-01: PR #14 has 5/5 offline tests in CI; upstream serializer was used in isolated probe; native gentb and TB import NOT TESTED.
- TB-01: GitHub Issue #15 is the next controlled synthetic import.
- Entire project: Stage 001 / PARTIAL.
