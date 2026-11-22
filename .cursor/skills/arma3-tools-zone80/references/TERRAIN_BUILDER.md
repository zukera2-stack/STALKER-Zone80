# Terrain Builder — Zone80 TB-01 sandbox checklist

## Data contract from GIS-04 / GRM-01

This project targets ONE final Arma 3 world, not 64 separate WRP files. The 8×8 sectors are preprocessing units only. Stage 001 evidence is synthetic.

The GRM-01 intermediate is a 64×32 rectangular ASC assembled from W/E 32×32 tiles (8 m per cell), with local TB Easting around 200000. The real Terrain Builder's acceptance of this rectangular ASC as a final mapframe input has NOT been confirmed. Do not silently assume that a 64×32 ASC is importable as a TB sampler: inspect the editor's size restrictions and, if needed, create a documented *separate* square synthetic test frame, without falsifying geometry.

General TB coordinate contract to verify, NOT assert as GUI-pass:
- Imported sector-local GRM CSV X contains XShift=200000.
- localX = tbSectorX - 200000, worldX = localX + sectorOffsetX, tbWorldX = worldX + 200000.
- worldY = sectorLocalY + sectorOffsetY.
- W offset (0,0); E offset (256,0) in GRM-01 synthetic fixture.
- W/E shared boundary at tbWorldX=200256; source IDs and part IDs must be preserved in sidecars.
- ASC rows conventionally run north-to-south; xllcorner and yllcorner denote lower-left **cell corner**, xllcenter/yllcenter denote center. Compare actual GUI import to known markers.
- A NoData cell (e.g., -9999) must remain missing semantically; a different marker in GeoTIFF is acceptable only if the mask matches.
- Absolute and relative object height modes are distinct import choices. The CSV row itself does not carry a reliable standalone height-mode marker; preserve the file-to-mode association.
- Models in fixture CSV are symbolic. If missing, do NOT treat a TML preview or file parse as verified 3D model import.

## Non-destructive TB-01 trial (only after explicit local owner approval)

1. Record Windows/tool/launcher version and P: status using scripts/inspect_arma_tools.ps1. Verify GUI availability. If no actual Windows/editor, stop with NOT TESTED.
2. Reproduce the GRM-01 fixture into a fresh ignored reports/ directory; run scripts/validate_tb_inputs.py against the assembled ASC and separate CSVs. Record SHA-256.
3. Create a **new isolated** minimal TB project / Mapframe within the sandbox; do not open an existing world or change global Work Drive settings to force success.
4. In Terrain Builder choose the installed version's documented terrain import for the ASC, create or inspect the mapframe sampler as needed, then verify width, height, cellsize, origin and orientation. If the editor rejects rectangular data, document the rejection and test a separately labelled square fixture only if authorized.
5. Load an allowed TML library and legitimate test model (if available and approved); never copy P3D/PAA/PBO into the repository. Import absolute and relative CSV **separately** with correct elevation modes. A test fixture with a non-existent model is NOT a successful model import.
6. Inspect four GRM-01 checkpoints in *world-local* XY: west (32,48), east (480,72), seam (256,80), outer edge (512,256). In TB Easting, add 200000 exactly once to X. Record height and orientation yaw/pitch/roll, scale. Check one source_id/part_id per placed entity.
7. Compare terrain heights near seam, a selected NoData position, edge positions and cell-center offsets. Record whether GUI tools actually preserved all four objects.
8. Save only in the isolated sandbox; capture screenshots and log versions. **Do not generate WRP, PBO or launch a full game build.**

If the tool needs an incompatible sampler dimension, licensed missing model, or an unsupported GUI step, mark that criterion BLOCKED/PARTIAL and describe the exact condition. Never silently substitute a successful Python test for TB import.

## Read-only validator

From repository root (if these files exist locally):

    python .cursor/skills/arma3-tools-zone80/scripts/validate_tb_inputs.py --asc reports/grm01-example/world/elevation.asc --absolute reports/grm01-example/world/absolute_fixture.txt --relative reports/grm01-example/world/relative_fixture.txt

The validator checks ASC header and numeric values, TB semicolon row format, finite transform and positions within declared ASC bounds. It does NOT inspect P3D, require P: mounted or launch an editor. A rectangular ASC can pass this validator while remaining unsupported by TB.

## Required report
- Input SHA, project path (private evidence), TB executable/file version and window identity.
- Mapframe sampler and imported terrain size/origin, cell center and edge checks.
- Exact import sequence per height mode; number of visible/accepted placements and screenshots.
- Status split: input syntax, editor import, model resolution, in-game result.
- No PASS for WRP/Arma load without actual independent evidence.

Related project report: docs/audits/GRM_01_MODULAR_EXPORT.md in PR #14; task: GitHub Issue #15.
