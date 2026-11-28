# GRM-AUTO-02 — measured independent adjacent-sector seam and bounded canonical block

27.11.2026. Base ea48a02d126fa4967714c158cc8402458425dff8, draft PR52, #42 task comment 7218537278. Stage001 PARTIAL. Bounded synthetic fixture only. Independent native vegetation seam FAIL, full tested overlap companion mask equality FAIL; shared elevation and sampled road crossings PASS. Fixed shared block + deterministic partition PASS for this one fixture; scalable independent generation NOT PROVEN. No native TB import, PAA/Buldozer, real geography, full world, merge or stage promotion.

## Exact geometry and method

All locations below are in the fixed GRM node-origin frame (E294388.084/N5698137.108 UTM36 test coordinates). No geographic reprojection or new height synthesis. W core [360,960)×[480,1080), E [960,1560)×[480,1080), 600×600m each. Halo 180m each side; W expanded origin (180,300), E (780,300), 32² nodes at 30m, nominal 960×960m expanded area. Reference uses original GM 64² nodes, 1920m. Same inline synthetic OSM source generated in fixed world area then independently parsed/projected in each process, SHA256 918ffadf67cb33770169f45807c216df500a811eb2ffb10ecbb5d0ed799f0ae5. Forest [800,1120]×[550,940], lake [880,1040]×[950,1030], two crossing roads (x=960 at y=600 and 760). Existing reviewed GRM-AUTO-01 profile 4321314e74a02638a3c018d829226fdebc0c6fda0468484474d8c904b19fb039, model cache 1177ec6d4618f198bd40f79880d3434ecbd7e0b8414881e23159c3e2a4cd9e94. No profile modifications, no new models. Companion polygon mask, not full internal IdMapRender. Physical source feature lineage not implemented.

Global Mapper Pro 26.2 b110625 x64, verified previous executable hash 71097e955b206db28c2b37fb3afc1c98d38ac8926c3984dccacdf224d00c89a0. Native GMS offline crop from pinned existing synthetic ASC, EPSG32636, 30m, exact center bounds. GM batch exit0, script marker GRMAUTO02_GM_FINISHED, 1.234s reported script / 7.7174s launch. W ASC 09dc163a8c50db62bb345319f7eba43b2d44535fbedc594f7c2d33698612a18e; E cfcbc627695e713f95fff43e5b907a8e2c3e3cb5f17f020e2b2a083b49a47326; PRJ both 81f38559a85a513efce9238b782ac86bd2a05694754ccb6efdd627a016f822d8. All 2048 nodes equal corresponding source samples, no NoData, all 384 shared nodes identical. Independent gm_qc.json SHA256 5a3477941271108848fef7e7bae8b0c2265e471f46e4bf22176462fd1b306780.

Reused CC05B guard/NodeInput and GRM-AUTO-01 resolver, road memory writer, native ForestGenerator and RoadsCompiler/Deserializer, same installed GRM DLLs (version and two hashes verified in prior report), offline .NET restore/build exit0, 1 known MSB3277 warning/0 errors. No raw-elevation fallback permitted; no OS network isolation claim. Build 4.36s. Executable DLL SHA256 4378728134061cf863ca71e99963f1ceedcbb85b0c36d8a0d45ee0c1fd868f61. Separate native processes W/a,E/a,REF/a,W/b,E/b all exit0, times 3055,2167,1666,1532,1530ms; each sector repeats 9/9 exact files. Not a translated copy of generated objects.

## Independent measurements

| Check | Result |
|---|---|
| Shared height interpolation 231 subcell sample points | W/E maximum delta 0m; versus REF max 0.00001m (tolerance 0.0001m) |
| Roads | Native SHP type13/SHX/DBF and 2 roads in each run independently decoded, at x900/960/1020 compared with REF; maximum delta 0.00166755m (tolerance 0.05m); seam y600/760 both exact. Sampled crossings, not full topology proof. |
| Mask | 4m grid, W/E overlap test [840,1080)×[480,1080): 2 mismatches/9000, asphalt/default swaps. 40m seam strip 0/1500. W-core vs REF 3/22500, E-core vs REF 2/22500. FAIL strict whole tested overlap equality. |
| Native W objects | 2342 generated, 2263 accepted, 79 held (70 extent, 9 outside forest). |
| Native E objects | 2343 generated, 2326 accepted, 17 held (outside forest). |
| Native REF | 2342 generated, 2321 accepted, 21 held (outside forest). |
| Raw overlap | 1768 W / 1758 E / 1735 REF; zero matching model+position+pose keys (1mm rounded) W vs E. FAIL independent seam equality. Not an assertion of zero exact XY-only matches. |
| Half-open raw ownership | 1186 W + 1169 E = 2355; no duplicate exact identity keys; 4 cross-boundary anchor-distance conflicts using profile radii 0.7/1/2m, not actual geometry. |
| Reference partition | 1148 W + 1173 E = 2321, unique deterministic fixture-local IDs, reverse order invariant. One anchor-radius conflict in reference partition. |

Independent QC SHA256 3897a8f1c9802ec43c043df70b2cc6cee30bae6bc0a3456a168dde3487059ca2. Native placement identity and physical collisions are different: radius is a heuristic from profile, not an actual P3D footprint test. Upstream pinned RandomHelper.CreateRandom(TerrainPoint) uses truncated X+Y seed; local frame/geometry-dependent random generation is a plausible contributor, not isolated single-cause proof. Do not solve this by discarding arbitrary duplicates or increasing halo until an apparent PASS.

## Corrective bounded experiment: shared fixed block

Fixed canonical generation window (600,420), 720×720m, 24² nodes; covers entire synthetic forest with margin and the lake, spans sector boundary. Both consumers use exactly the same origin/input/profile/geometry. Global Mapper native crop second batch exit0 2.9158s, ASC a5f14e61851795de724548869189373c7c3e5b25f7d145587c8b891d949c49d9, same PRJ as W/E. All 576 nodes compared equal source; 231 interpolated samples vs reference max 0.00001m. Native source variant only adds fixed C branch, same actual native calls. Build exit0, 1 warning/0 errors; binary SHA256 d0019f3c44e4f92cc9df7e1cf2a5bd9a732e8851136694349efd53f57165ed67. Independent C/a and C/b processes exit0 at 2840/1584ms, 9/9 files byte identical. Generated 2343, native filter accepted 2331, held 12. Assign deterministic synthetic IDs from canonical model/position/pose key, half-open core ownership, reverse request/iteration order same exact arrays. W 1136/E1195, 2331 distinct assigned IDs, no extra hold. 0 cross-seam anchor-radius conflict pairs before/after. The deterministic extra-hold branch is implemented but not exercised on C because no conflicts; no claim it solves model footprint collision. Intra-sector physical collision and full P3D bounds NOT RUN.

Crop shared native-geometry companion mask into core intersections [600,960) and [960,1320), y[480,1080) from same fixed 4m grid, 90×150 each. Independent byte readback and reassembly 27000/27000 pixels exactly equal source intersection. Not complete masks for both 600m cores; no global material/road engine approval. Canonical block road native outputs exist, sampled W/E geometry check above passed, but merged road export for all cores NOT RUN.

Local GRMAUTO02_CANONICAL_REVIEW.zip 171909 bytes, SHA256 6e95478cc524a555b84f3379c2a1dee737de2488fd24b925bdd8c780f1be4dbd, six files verified against local contents (W/E object JSON, held JSON, W/E intersection BMP, manifest). Manifest SHA256 706c1dc33e3e2886cef57f68f8ad7309ae89152678691c44f05daaf710c8b3b8. Review package, not game-ready or full TB import package. Previous GRMAUTO01_TB_IMPORT.zip, MAP005_INTEGRATION.zip and MAP005_BASELINE.tv4p all retained exact previous hashes. No P: write initiated, no editor process change.

## Reproduction (Windows, pinned local inputs only)

Use fresh owned ASCII root basename GRMAUTO02; keep original native GM ASC, PRJ, reduced synthetic.grma3a, modelinfo.json in root. Copy original ASC/PRJ to REF; GM exports W/E/C into separate fresh directories. Global Mapper 26.2 native script import existing synthetic ASC, LOAD_PROJECTION PROJ="EPSG:32636", EXPORT_ELEVATION TYPE=ARCASCIIGRID ELEV_UNITS=METERS SPATIAL_RES=30,30 GEN_PRJ_FILE=YES, exact sample-center bounds:
- W: 294568.084,5698437.108,295498.084,5699367.108
- E: 295168.084,5698437.108,296098.084,5699367.108
- C: 294988.084,5698557.108,295678.084,5699247.108

Check exact exported hashes and node grid first. Copy unchanged grm-auto01/GrmAuto.csproj and cc05b/GmOnlyContext.cs into src and srcCanonical respectively. Use previous offline restore/build recipe (empty feed, GrmBin local installed folder, no audit), run src DLL for W a, E a, REF a, W b, E b; python -B verify_gm.py then verify_seam.py. Run srcCanonical DLL for C a and C b, then python -B verify_canonical.py. All scripts require fixed scope and fresh result directories. Inputs/outputs/SDKs/binaries local only, no proprietary files committed. Actual source SHA256: src Program b8f79bf36137df26ee64bcdd64d449c6cbb0c1ee9cf5c301cb05a999dc7f46d5; srcCanonical dcf7f75d0afd2299baf175e8c97817f7d316c23382e0738c8664c3ea7c17b0e1; verify_gm 20837e52fba238ac75fe2a2e71ca97b6bac228ef4c033593fef61c7bdd3cff53; verify_seam 52808cf739a87b00a05710aece49beaceff3a3112ebc953f92e0c9f366e5e9b1; verify_canonical 47d5d36f6100e327826fcdccfa853b72b3d365390d8424c6e040acece7884b20.

## Decision / remaining gates

Independent native W/E generation cannot yet be used as final production ownership. One fixed shared canonical block and later sector assignment is a measured bounded remedy, not evidence that arbitrary very large connected forest polygons, 64 independent production sectors or changed inputs will remain stable. Next design a fixed globally anchored block/feature partition, explicit overlap arbitration and stable source lineage, test more than two blocks, intersections/corners and changed inputs. Need full core layer outputs, actual P3D bounds/clearance, actual separate TB import/readback before promotion. No full-world run. Stage001 PARTIAL.
