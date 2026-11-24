# Repository workflow

main is the stable reviewed foundation. Work in feat/*, fix/* or audit/* branches, make pull requests and keep verifiable commits. No force push, no unreviewed upstream GRM vendoring and no automatic merge for high-impact generation changes. Never commit addon binaries, large GIS data, credentials, cache or game builds.

Review checks: Python standard-library validation, source/asset allowlist, traceable configuration, no claims of in-game performance without evidence. Keep overrides small and reviewed; raw input remains local and immutable.

A local Cursor clone of the project must stay separate from an upstream ArmaRealMap clone. If experimentation needs upstream changes, preserve the original commit hash and do it in a dedicated patch branch; check the upstream license before publishing code.

## Current draft-stack discipline (audit 2026-11-24)

**Latest work is NOT on main.** MAP Draft stack: #36 → #37 → #38 → #40 → #41 → #44; earlier cloud heightmap PR #43 was CLOSED unmerged. A dependent documentation audit PR was based on #44. A successful CI check on a draft head does not indicate a merge or Windows runtime. For current work, always record **base branch + base SHA, head branch + exact head SHA**, review changed files, rebase only with explicit instruction. Never use a stale issue comment SHA as authoritative without verifying the PR head. If intended files exist only in a nonmerged PR, fetch them from that ref; **do not assume they are in main**.

After an accepted operation: update one active Issue, `docs/PROJECT_STATE.yaml`, `docs/REQUIREMENTS_MATRIX.md`, `docs/VERIFICATION_LEDGER.md` and, only when policy changes, date-stamped ADR. Do not bulk-close or automatically merge unrelated legacy Draft PR. See [Project Control](PROJECT_CONTROL.md) and [HANDOFF](HANDOFF.md).
