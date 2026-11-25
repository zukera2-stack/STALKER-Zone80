# CC-03 — logical Sector Manager
25.11.2026; Issue #42; Draft PR #47; base 0591395c40937fd524d4e9cafc4decf98f54942b. Python 3.13.5 Linux standard library only. Stage 001 PARTIAL. No real terrain generation, GIS acquisition, P: writes, native GRM/TB, placement or merge.

## Implementation
tools/automation/cc03/sector_manager.py consumes the existing foundation manifest contract, rather than replacing the coordinate-only writer. demo.py imports build_sector_manifests.manifests from a trusted repo root; validator/config still govern dimensions. 8×8 logical grid, integer millimetres and synthetic origin, half-open ownership [min,max) including exclusion of north/east maximum outer boundary (explicit prototype decision); exact translation, no geodetic CRS. Point anchors have one owner, straight segments only context, no native clipping/placement. Closed bounding-box intersection conservatively selects halo context; demo buffer 100 m is a synthetic test choice, not approved production radius. Rational crossing coordinates on common edges; collinear segment flags require review, not automatic resolution. Adjacent edge signatures checked in both directions, missing sector/neighbor/seam rejected. Global source snapshot digest recorded, per-sector identity includes local context, rules, generator hash, synthetic origin and halo, so changed source inputs invalidate dependent sectors only. No arbitrary auto-dedup by coordinates: duplicate source IDs are rejected, different IDs at same position not merged.

## Actual evidence
- `python -m py_compile sector_manager.py demo.py test_sector_manager.py`: PASS.
- `python -m unittest -v test_sector_manager.py` twice final: 11 methods PASS, 0.042s and 0.041s. Initial nine methods also passed, then strengthened missing-adjacency and JSON roundtrip tests.
- Real demo run against a local copy of five base repo files whose Git blob IDs were verified against GitHub: tools/validation/build_sector_manifests.py e8ae4a3fb539f5aff26affa068fc4d6d93eda0d2; validate_config.py 12befbb6eeb029a27265a6d689b34149030eca33; config/generation_profile.json e21b7e9518d480b0f35eb4c3648e5a0b306e21e8; stalker_locations.geojson 8b3698faf7fa84fe8ba04361daf74805a2d10154; terrain_extent.json 865d06285a3851764d19b43ff85972fbbfc4b37e.
- `python demo.py --repo-root <verified-base-copy>`: 64 manifests; 112 internal shared edges; zero seam issues for synthetic crossing fixture; anchor owner S01_00. Baseline and reversed-order input digest both 51dbc9177b597cce5e3ab0930d885c20d01404c8afdd85bfaf4919c105631568. Interior edit dirty S00_00 only.
- Test grid: exact total area, 2016 distinct pair checks with no positive-area core overlap, 224 directed neighbor relations. 128 corner/interior boundary ownership roundtrips, outside world rejected. Crossing fraction verified, corner anchor owned once while four contexts see it. Interior revision marks one; moving to seam marks two; removal marks both; rule hash change marks all 64; unchanged marks zero. Invalid foundation schema/geometry/CRS, duplicate IDs, unsupported polygons, noninteger inputs, degenerate segments and bad rule hash rejected. Missing edges and tampered signature detected; collinear review flagged.
- This measures invalidation decisions, not actual sector recomputation.

## Integrity
| File | SHA256 |
|---|---|
| sector_manager.py | 514072c171cf29128215e8fa4163612f2b3b38ecfb326e307c8d59c14845e66c |
| test_sector_manager.py | b53416e82a245551a3a3d85fd7a8645802fb5752ff75fa9be0df4dee6432d4a2 |
| demo.py | e6da8e97b4f0d51406e648613c68e3363da60824eb19f6cf334a831833a77f40 |
| tests.log | 36c6ccd6a4ca4205996d387d3ae4e38b5cee0445666208c5c3646fd249881c30 |
| tests_repeat.log | 2f0bf369ad2f9823d894dd6765f2d0a94c77cd91d28c3623e352a016fedff4aa |
| demo_result.json | 11ee37e7af3156b9e128bb703dbb39cad05571889953b07529b66308dd5d23f9 |
Owner ZIP Zone80_SectorManager_CC03.zip, 7815 bytes, SHA256 42f5e087afc0f7e7373fa9e04d34c6296bdc3ace01718d9e7642f39b98e4425e, CRC PASS. Seven repo file blobs match measured source/artifacts before publication.

## Limits and next
PASS bounded synthetic planning. Trusted state only, not authentication/security validation. No actual scheduling bridge to CC-02, polygon/polyline clipping or geospatial seam proof, source relation reconciliation, procedural seeds, asset matching, native import or Windows validation. Conservative bounding boxes may over-invalidate. No performance claim for full world. Production CRS, origin, epoch and halo unapproved; 629 NoData remains in actual MAP-003 diagnostic grid. Next CC-04 synthetic Config Builder/Asset Manager with explicit unresolved dependency gates; reuse v03 evidence. No stage promotion.