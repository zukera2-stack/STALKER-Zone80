# CC-04 — review-only Config Builder / Asset Manager
25.11.2026, Issue #42, Draft PR #47, base 408680a81267647957506170634f73ce930a141d. Linux Python 3.13.5 stdlib. Stage 001 PARTIAL. No native GRM/TB, real elevation generation, placement, P: writes, scheduler or merge.

## Scope and architecture
Six modules from the existing GRM editor config (vegetation, roads, materials, infrastructure, buildings, dependencies), preserving all 15 top-level fields. In-memory assembly, canonical SHA256 per module/config/baseline/inventory; trusted baseline locks 11 material RGB/RGBA definitions with all 16 usages and 9 road IDs. Reject duplicate/missing/unknown usage, RGB change, mismatched texture stems, surface mask mismatch, invalid road widths/resources, re-enabled generic buildings, ponds, sidewalks/lamps and external Dependencies entries. Surface mask semantics checked against pinned upstream SurfaceConfig.Match and TerrainMaterialDefinition.cs. Missing surface metadata is an explicit blocker, not a silent fallback. Case-insensitive virtual paths, conflicting inventory observations rejected. Presence in inventory never implies rights or CfgPatches/entitlement approval. Review output is JSON report only; production CLI explicitly refuses, no .grma3a emitted. Hashes record revisions, not authenticity. This is not a complete native schema compiler: nested compositions/properties beyond checked fields not fully validated. It is an audit gate, not an authorization or security boundary.

Synthetic dependency graph validates transitive closure, missing/duplicate/unknown and cycles in explicitly synthetic rows only; no real CfgPatches proof. ZPB review checks basic ID/path/package/class collisions and statuses; every asset remains unselectable, even synthetic MODEL_READY, pending local QA and placement approval. Actual reserved manifest candidate confirmed via GitHub; no model geometry/hash/build/engine readiness claimed. No actual Worker integration.

## Actual tests
`python -m py_compile config_builder.py test_config_builder.py demo.py` PASS. `python -m unittest -v test_config_builder.py` 13/13 methods twice (1.380s, 1.430s), covering deterministic assembly, usage/color locks, negative road/feature cases, resource path normalization, missing/forbidden references, missing surface, inventory conflicts, synthetic dependency graph, ZPB metadata, catalog flags, module shape, duplicate/nonfinite JSON, real CLI review and production refusal. CLI return 0 = review completed, never native PASS.
`python demo.py --baseline Zone80_v02.grma3a --inventory Zone80_inventory.json --v03-zip Zone80_Config_Preflight_v03.zip` run twice on actual owner attachments, summary byte-identical; no raw owner config or inventory committed. Input SHA256:
- v02 84e0cdee7501b7e9f01cc92b6635c70e8d6503f591e0b1a0ffffef2a2d6bf41a
- inventory bced5f4e610ef0c3667f1f91f6dd2016e5f0223fb147f5986664c17d9493668e
- v03 ZIP 5c1acdf80eaa5e0fd61adddd41845946e8df6e994881c16faaaf2a20cdbee90a
- v03 config 418a6b1db5493c8b9f89f288024a769522f568483a5e614383d934506e7a941e
203 unique resource paths: 179 presence in earlier inventory or paired texture candidates, 22 stock namespace unverified, 2 external ice. Zero runtime-approved. Missing surface usages LakeGround/RiverGround. External base class/dependency, ice policy, local entitlement/dependencies, complete GM heights and adapter, native parser all unresolved. No elevation or model placement output.

Separate actual GitHub connector audit of base reference arrays (not Python optional repo-root demo): vegetation 76 refs, roads 9 profiles/18 refs, materials 11 definitions/50 refs, infrastructure 65 refs; dedup union 204 refs = 181 stock path candidates +23 external. All main reference rows remain unapproved. Catalog blobs: 3c70b1eb866fbb92dcada2f3b5c42d57e98bc5fe, c4b798c3397bc518f3035116731a548db8fc1f70, 7fd0a4f4b33532f5683b6afb66633eb3c0e30379, a73fdb0652fc00ef8decec7cafe1a5fef162171b. ZPB example blob 3a09cd4730b0a77e01d93cb2dd658f398191b705: zpb.house.111_60_12.v01 status CANDIDATE, addon_release null. Python reference/ZPB helper exercised on synthetic fixtures; optional --repo-root actual mode NOT RUN.

## Integrity
| File | SHA256 |
|---|---|
| config_builder.py | 243bb07a8ed606fd711359f419150e797725d521d636d95909e2be0cedfcad25 |
| test_config_builder.py | ff1d67d826df626dc2ed7f8a99b48586b97cc39b0b27749b8fa18fe14de18062 |
| demo.py | 19ed0035db223797a79072f36f857949a64a2679405a86c9ffb88143b7b05614 |
| README.md | 3313d97b5f3ce5bff9f529273b4b20ac291edad23324cfe2e16c074c5ed056ca |
| tests.log | dc3154d859c881a93af2f4df5354c175b9c00d62ea01271a823f8d6003745ae9 |
| tests_repeat.log | 8c14cd8932bf700147209df3a7e98cf03ce7c9e85f07583f3e30f634da669155 |
| demo_result.json | 42f88135322fc6ea5b7430516cabe068b79cef92b32a6554ce6b5e09389e5480 |
Owner archive Zone80_ConfigBuilder_CC04.zip 12114 bytes SHA256 8f6b261cc14bb03cf6fe576aa496fe5e080238538a3242178c198dfd5a5409e7, CRC PASS. Seven source/artifact Git blobs matched tested source before publication.

## Assessment and next
PASS bounded review assembly and static audits, actual production compiler BLOCKED. No fabricated approvals, no full recursive native schema validation, actual class/dependency closure, local inventory refresh, real model QA, native v03 parser or clean game test. No production-ready config created. Next CC-05: review pinned GRM dependency graph and design GM-only read-only input adapter with synthetic in-memory fixtures and rejection of wrong NoData/grid/origin/units; no new real elevations or native layer generation. Existing local GM NoData=629, TB BLOCKED, Stage 001 PARTIAL unchanged.
