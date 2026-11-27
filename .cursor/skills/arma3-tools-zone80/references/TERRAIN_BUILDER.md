# Terrain Builder — TB-01 small synthetic import

Zone80 is intended as ONE world, with 8x8 sectors used for preprocessing. Stage 001 is PARTIAL. Do not produce WRP or PBO.

GRM-01 produced two synthetic tiles W and E: 32x32 cells each, 8 m per cell, with an intermediate merged ASC 64x32. This rectangular grid has NOT been confirmed as a supported finished Terrain Builder mapframe. If TB rejects it, log the result and, only if authorized, create a distinctly labeled small square test wrapper.

## TB coordinates to verify, not assume accepted by GUI

GRM TB CSV carries a fixed 200000 offset on X:
- local_x = sector_tb_x - 200000
- world_x = local_x + sector_offset_x
- final_tb_x = world_x + 200000
- world_y = local_y + sector_offset_y

GRM-01 W offset=(0,0), E=(256,0). Seam TB x=200256. Control points world XY: (32,48), (480,72), (256,80), (512,256). Asc rows are north-to-south. xllcorner/yllcorner describe lower-left CELL CORNER; xllcenter/yllcenter describe center. Relative and absolute object elevation are different import modes and must remain in separate CSVs. NoData should retain missing-cell semantics.

## Safe procedure only with owner authorization

1. Verify actual Windows, TB version, P: state and launch scope. Never change P: or globally shared project settings just to make a test pass.
2. Generate fixture under ignored reports/ (if GRM-01 exporter exists locally) and run validate_tb_inputs.py.
3. Create a NEW isolated TB project/mapframe, not an existing project.
4. Try loading the synthetic ASC. Record actual sampler, dimensions, corner/center alignment and any rejection messages. Do NOT infer acceptance from Python passing.
5. If owner-approved legitimate model is available, load its TML/model and import absolute/relative object CSV separately; fictitious FixtureMarker is not a valid game model.
6. Record GUI-observed XY, Z, yaw/pitch/roll, scale for four check points and examine the seam and NoData. Validate no duplicate boundary placement.
7. Capture screenshots or logs of the actual GUI and store only in ignored reports/. No WRP, PBO, packaging or full game launch.

If no Windows/TB/approved model exists, mark the respective check NOT TESTED/BLOCKED. An offline parser PASS is not a TB import PASS.
