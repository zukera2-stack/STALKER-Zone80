# Evidence, licenses, and reporting

## Locality
Reports, screenshots, outputs and hashes from the user's Windows system go to ignored reports/ only. Public PR contains sanitized summaries and source code, NOT personal absolute paths, environment secrets, PBO/P3D/PAA, raw third-party GIS imagery, license material or extracted assets. Review .gitignore and git diff --cached --name-only before pushing.

## Four distinct result levels
1. SOURCE REVIEW — read code/docs; no executable was invoked.
2. OFFLINE CONTRACT TEST — static/pure Python or isolated .NET serializer. Only verifies declared format.
3. WINDOWS TOOL RUN — exact installed executable/version tested in real workstation; preserve measured commands/logs.
4. GUI IMPORT / GAME LOAD — actual TB UI or engine stage verified with screenshots/logs. Do not infer from earlier levels.

For each tool feature record PASS, PARTIAL, FAIL or NOT TESTED, and what evidence supports it. Mark missing license, missing executable or inaccessible GUI as NOT TESTED / BLOCKED rather than claiming success.

## Current Zone80 baseline
- GIS-04: two GM26.2 synthetic tiles and tile ownership controls (PR #12). Windows integration reported; offline unit tests run in CI.
- GRM-01: Python CSV/ASC assembler and upstream serializer probe (PR #14); native gentb, satmap/idmap and TB import NOT TESTED.
- TB-01: Issue #15, synthetic import into one TB project; until evidenced it is a plan, NOT a completed run.
- Stage 001 remains PARTIAL; owner has not authorized Stage 002.

## Report template

    Task / date / tested Git SHA:
    Source/Tool version + exact Windows test environment:
    Input fixtures + SHA:
    Commands, logs, screenshots (local paths only):
    Checks: expected / observed / status / evidence:
    Outputs and hashes:
    Runtime / measured peak memory (state process and polling method):
    Unverified assumptions and dependencies:
    GO / PARTIAL / NO-GO and next gate:

Never transform an unsuccessful test into a successful claim by changing the test scope after running it.
