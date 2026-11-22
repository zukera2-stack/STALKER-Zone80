---
name: arma3-tools-zone80
description: Safe workflows for Arma 3 Tools (Terrain Builder, Object Builder, Work Drive, Addon Builder, Binarize, CfgConvert, Terrain Processor and Buldozer) in STALKER-Zone80. Use for Windows tool inventory, P-drive troubleshooting, synthetic terrain import, TB CSV/ASC verification, asset provenance and stage-gated diagnostics.
---

# Arma 3 Tools — STALKER-Zone80 / Cursor agent skill

## Scope and first actions
Use this skill when working with Bohemia Interactive Arma 3 Tools, especially the Zone80 TB-01 sandbox. This skill DOES NOT confer permission to run a build or modify installed tools.

1. Read repository AGENT_START.md, AGENTS.md, docs/PROJECT_STATE.yaml and docs/GO_NOGO.md. The repository stage gate overrides any examples below.
2. Check git status and base commit. Work on a separate branch; never merge or force-push without owner permission.
3. Identify the actual machine: Cursor local terminal vs Codex/remote shell; report the execution provenance. Remote evidence cannot prove the owner's local Windows/GUI state.
4. Run read-only discovery below, or mark NOT TESTED if no Windows access. Never guess an installed path or version from old reports.
5. Select the requested workflow from references/TOOLCHAIN.md or references/TERRAIN_BUILDER.md, limit inputs to a sandbox under ignored reports/, and record evidence.

## Safe commands from repository root

Read-only inventory on actual Windows (no launch, no mount, no extraction):

    pwsh -NoProfile -File .cursor/skills/arma3-tools-zone80/scripts/inspect_arma_tools.ps1
    pwsh -NoProfile -File .cursor/skills/arma3-tools-zone80/scripts/inspect_arma_tools.ps1 -ToolsRoot "D:\SteamLibrary\steamapps\common\Arma 3 Tools"

The example ToolsRoot is a placeholder, not a discovered installation. The inventory prints JSON; redirect output into ignored reports/ only if locally appropriate. Do not publish raw machine paths.

Pure Python offline fixture validation (does NOT launch Terrain Builder):

    python .cursor/skills/arma3-tools-zone80/scripts/validate_tb_inputs.py --asc reports/grm01-example/world/elevation.asc --absolute reports/grm01-example/world/absolute_fixture.txt --relative reports/grm01-example/world/relative_fixture.txt

If the example does not exist, mark NOT TESTED; the GRM-01 generator lives in PR #14 until merged. For a local synthetic fixture, use the documented GRM-01 exporter only after reviewing that code. The validator checks syntax/bounds, not actual TB import or model resolution.

Skill self-tests (do not require Windows or licensed software):

    python -m unittest discover -s .cursor/skills/arma3-tools-zone80/scripts -p "test_*.py" -v

## Tool routing
- Work Drive / P: — resolve actual project root and mount status; NEVER mount, unmount, extract PBO, overwrite, or copy game content automatically.
- Terrain Builder — import approved synthetic ASC and separate absolute/relative object layers into ONE sandbox Mapframe; record positions and elevation semantics. See references/TERRAIN_BUILDER.md.
- Object Builder — model/LOD/material workflow on the user's authorized editable source only; metadata inspection is not permission to de-binarize a P3D.
- Addon Builder / Binarize — packaging/compilation tools. Stage 001 prohibits running them; describe dependencies, arguments and a proposed test but DO NOT invoke.
- CfgConvert — config conversion, not evidence that PBO or WRP works. No conversion of user-owned files without explicit scope.
- Terrain Processor — terrain object placement and LBT output; not the WRP compiler. Use in a future authorized sandbox only.
- Buldozer — real graphical preview requires Windows/game resources, explicit owner approval and actual evidence. No fabricated screenshot or PASS.
- GRM gentb — upstream currently loads OSM and runs image conversion; never invoke blindly for an offline test. For Zone80, separate synthetic GRM-01 contract tests from verified native gentb execution.

## Safety gates — always enforce
- Stage 001 / PARTIAL: NO real 10.24 km sector, full 81.92 km map, WRP, PBO, addon packing, binarizing, large downloads, tool installs, license activation, automatic network calls or game-asset extraction.
- Never write to P:, Arma installation folders, original mods/PBO/P3D/PAA, or source GIS/GRM files during audit.
- Do not upload 3rd-party binaries, GIS rasters, protected models, local absolute paths, licenses or credentials to GitHub.
- Only synthetic inputs or separately authorized assets with tracked license/provenance. UNKNOWN asset license means no redistribution.
- Treat an empty or inaccessible tool path as NOT FOUND / NOT TESTED, not an installation failure or working tool.
- A successful CSV/ASC validator is NOT proof of GUI import, Terrain Builder compatibility, valid WRP or Arma engine load.
- Before future authorized tool execution: require isolated owner-controlled output, verified exact executable, a documented rollback/stop procedure, bounded time/memory, and evidence from that specific Windows session.

## Return to owner / auditor
Report: branch+SHA, terminal identity, tool executable paths (private raw report only), product/file versions, Work Drive/P: read-only status, tested commands and source hashes, input/output inventory, wall time and observed process memory where measured, screenshots/logs for actual GUI tests, PASS/PARTIAL/FAIL/NOT TESTED per criterion, blockers and next safe action. Keep detailed artifacts inside reports/, publish sanitized text summaries only.

Official documentation links and practical boundaries: references/TOOLCHAIN.md and references/TERRAIN_BUILDER.md.
