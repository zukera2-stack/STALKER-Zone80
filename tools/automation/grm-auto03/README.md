# GRM-AUTO-03 — four generation blocks, four offset storage sectors and shared corner

27.11.2026. Base e86aa041e233fa7c1c9e59e8ecce170cadee57bb, PR52, #42 task 7218929264. Bounded synthetic Windows experiment. PASS for native repeat, node/value consistency, sampled straight roads, deterministic cross-boundary anchor proxy arbitration, four full storage masks and localized fixture edit. Strict raw mask overlap FAIL (19 pixels); generalized production seam, P3D geometry collision, merged road export, native TB import NOT RUN. Stage001 PARTIAL. No real data, network acquisition, P: writes initiated, WRP/PBO, process interference, full world or merge.

## Geometry and inputs
Fixed synthetic world frame UTM36 test node origin E294388.084/N5698137.108, same GM source/profile/cache/installed GRM DLLs as GRM-AUTO-02. Four 600m generation cores span [300,1500) in each axis, internal crossing (900,900), 120m halos: SW (180,180), SE (780,180), NW (180,780), NE (780,780), nominal 840m windows, 28x28 nodes at 30m. Four 480m storage cores span [480,1440), center (960,960), offset from generation boundaries. Core membership is half-open. Local coordinate frame is fixed per generation block, not per storage request.

Synthetic inline OSM source feature101 forest [660,1140] squared, lake102 [850,950]x[1170,1250], roads103 horizontal y900 and104 vertical x900 from 400 to1400, forest105 SW [500,600] squared. Changed case expands feature105 east to640 (two node coordinates only), wholly outside other expanded windows. Baseline fixture SHA256 86a6b53a1ff56f992bc8ea7bd590058daba8869e3983dbb332467a85cfb17ce3; changed 8c4b2539983de0b55d84dffcd42dc3783d4dcefd7683aaddf7c071fb574e0e0a. No original source/profile changes. Lineage by synthetic rectangle containment, fixed block, quantized model/pose hash; not general upstream OSM feature lineage.

GM26.2 native offline export from pinned existing ASC, script exit0, 0.156s script / 2.6154s launcher. Center bounds and output SHA256:
| Block | Bounds | ASC SHA256 |
|---|---|---|
| SW | 294568.084,5698317.108,295378.084,5699127.108 | f3d0158fb40622b253f6774bc84667aa00d290d9f30854ca89280e4f3c1f97ab |
| SE | 295168.084,5698317.108,295978.084,5699127.108 | 475601225edaf3c3d02d5c18d3d99383df0b4245d55d6f6218907de2df988d2e |
| NW | 294568.084,5698917.108,295378.084,5699727.108 | d77ced544b3a72d83a0d880b7d4be24365da00ad6811df2cfc5c1d03112d3cac |
| NE | 295168.084,5698917.108,295978.084,5699727.108 | 94084204937b5c4cab13b22d9da988f02f944c5487bf5f580f35dea9c33a7a9d |
PRJ all 81f38559a85a513efce9238b782ac86bd2a05694754ccb6efdd627a016f822d8. No height synthesis outside GM. Independent readback all 3136 samples equal source, 2304 unique nodes, 704 shared incl. 64 four-way nodes, zero elevation delta. 361 common native interpolation probes max delta 0.000006m within 0.0001m tolerance.

## Native execution
Reused bounded CC05B guard, actual ForestGenerator, RoadsCompiler/Deserializer, upstream polygon drawing helper in companion mask (not full native IdMapRender). Installed DLL identities verified. Offline .NET restore/build exit0, 4.46s build, one known MSB3277 warning/0 errors. Program DLL SHA256 e522d4e223846f0a859d9c6a8e9eb2dc6c6e0aedb737925a6073fa58d3bca182. Twelve separate processes (SW/SE/NW/NE × a,b,changed) exit0, entire build/run shell 27.19s. Native times ms a:3045/1676/1536/1592; b:1636/1657/1652/1596; changed:1657/1713/1885/1532. All four baseline pairs 9/9 identical files, 36/36. Raw elevation fallback refused in each run, no OS network isolation proof.

| Block | Generated | Native accepted | Native held | Owned candidates |
|---|---:|---:|---:|---:|
| SW | 2624 | 2206 | 418 | 1290 |
| SE | 2424 | 2201 | 223 | 1090 |
| NW | 2424 | 2208 | 216 | 1092 |
| NE | 2424 | 2408 | 16 | 1092 |

Native holds from extent/outside-forest checks; overlap candidates not all emitted. 4564 owned candidates, 2 cross-boundary anchor-radius proxy conflicts (one across storage boundary within same block, one across generation boundary), both held, zero remaining across either boundary. 4562 unique IDs. Storage SW1850/SE1045/NW1033/NE634. Stable lexicographic block priority then ID, repeat/reversed-input output exact. Retained held records include conflict IDs. Radius proxy 0.7/1/2m scaled, not P3D footprint; intra-block intra-sector collisions not tested. Independent toy negative test (not native data): four candidates at shared corner, six pair conflicts incl. two diagonal; one accepted/three held, reverse order invariant. Exact half-open boundary ownership checked at (900,900) and (960,960).

Native PolyLineZ / SHX / DBF independently read back, two roads per block; straight-line perpendicular error 0m, clipped extents checked to 0.05m and crosses both internal coordinates. This is a simple two-road fixture, not arbitrary graph merge or complete road export.

## Masks and localized edit
Companion 4m raster source windows 210². Six pairwise raw overlap comparisons: NE/NW 19/12600 mismatch, NE/SE 0/12600, NE/SW 0/3600, NW/SE 0/3600, NW/SW 0/12600, SE/SW 0/12600. Strict independent equality FAIL. Deterministic owner per world pixel assembles four complete 120x120 storage masks, independent serialized pixel readback 57600/57600 exact to selected owners. Histogram grass41886/forest14313/lake481/asphalt920. This guarantees coverage and ownership, NOT physical rendering continuity or identical overlapped source masks.

Changed fixture ran natively in all four blocks. SW changed objects/mask and metadata; other three changed only common OSM and result metadata, all other seven native files byte identical per block. SW storage grows 1850→1927 (200 IDs removed, 277 added across final output), 250 SW mask pixels changed. Other three final storage object arrays and mask bytes identical. Local edit containment proven only for this fixture; arbitrary edits near halos can affect neighbors. IDs are deterministic content identities, not preserved when an object's pose changes.

Local GRMAUTO03_FOUR_SECTOR_REVIEW.zip 338019 bytes, SHA256 d49358ff4c7b33a17466639f628435ef0d2932cfe6dba37c82d9bf8cbe9c15d7, ten files verified: four object JSON, four BMP, held JSON, manifest. Manifest SHA256 49cc261ed8fc5da6c17945886a4d0ffe53752b4264efeccf4b1cbb64123a2368. Review package only, not TB-ready. Prior GRMAUTO02/01 ZIPs, MAP005 archive and tv4p hashes unchanged.

## Reproduce
Fresh owned ASCII root basename GRMAUTO03. Copy exact pinned terrain.asc/prj, synthetic.grma3a, modelinfo.json from previous verified local run. Native GM GMS export four directories using same commands as AUTO02 and exact center bounds above. Copy prior GrmAuto.csproj and CC05B GmOnlyContext.cs into src. Use same offline .NET restore/build (empty feed, GrmBin local installed folder, no audit). Run DLL root sector attempt for SW/SE/NW/NE with each of a,b,changed; then python -B verify_four.py (fresh output). Actual source SHA256 Program.cs 4d284e4c8f931af6f0e8d44920d18c6af1c2d1c0f84eb99ecb28c50232ecdad4; verify_four.py ac7fa96431015bc58807442acab3b9be0870f2aca935404ada538ee85299970b. No proprietary files or private paths committed. Next: resolve source mask discrepancies using canonical rasterization for cross-block features, complete TB-compatible road/object/TML and height/imagery package and native safe import; no new general architecture test without a concrete integration purpose.
