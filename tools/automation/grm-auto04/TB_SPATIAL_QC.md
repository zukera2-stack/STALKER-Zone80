# TB-BULDOZER-CLI-02 — connection gate and native template radius QC

27.11.2026. Base 77dac375e397502dcaa19a09ee96a1dd2c0e2931, task #42 comment 7221948881. Connection/3D preview BLOCKED under current no-config-change restriction. Native export NOT RUN; owner-drawn menu exposes unnamed commands. Independent native TML bounds / source placement QC PASS as diagnostic; spacing review candidate PASS under previous small-radius proxy, NOT a native collision test. Stage001 PARTIAL.

## Connection and editor state

Same verified Terrain Builder process, saved GRMAUTO04 open, responsive, 4562 total objects, Save disabled, no pending action. Official documentation https://community.bistudio.com/wiki/Buldozer_Manual documents editor Connect to Buldozer and configured viewer launch, not supported attach-only CLI. Historical Visitor 3 -connect named pipe option does not establish current Arma 3 channel/handshake. No repeat of already passed standalone launch, no guessed IPC, no installed preference edits or P: writes. File menu semantic Expand succeeded; child items include unnamed expandable and invoke-only leaves. A read-only native popup identity guard refused stale handle; one corrected same-call capture failed unique File popup identification (popup transient). No unknown menu item invoked. Native pose, shape and height exports NOT RUN. No new Buldozer started; final process inventory confirms none running, TB remains open.

## Native template metadata versus exported placements

Saved native arma3.tml SHA256 30bcbe590643f6f6fc10c400d93f8b3390e180429b5dd1f3ad66a11a9e1ca3c5 matches original native archive manifest. Parse the three templates and compare saved BBRadius values against earlier *unverified* small anchor spacing proxies. Source CSV, placement-ID sidecar and planar road SHP/SHX/DBF hashes checked. All 4562 source placements join by ID and model; coordinate translation +15m independently checked within 0.00051m. This uses exported source anchors, NOT independent native imported per-object readback.

| Model | Count | Prior proxy radius m | Saved BBRadius m | Native bounding box extents X/Y/Z m |
|---|---:|---:|---:|---|
| t_betula_pendula_2f | 1709 | 0.7 | 5.489546 | 7.45639 / 13.741541 / 10.979092 |
| t_betula_pendula_3f | 1567 | 1 | 7.869692 | 19.24852 / 18.260102 / 15.739385 |
| t_betula_pendula_3s | 1286 | 2 | 11.195412 | 16.030861 / 15.49155 / 22.390823 |

These are TB metadata fields, not trunk measurements or a validated horizontal footprint. Diagnostic circles centered on exported anchors use scaled BBRadius; no claim exact bbox geometry, rotation, visual canopy, collision LOD or axis conventions. All 10403641 unordered anchor pairs tested; 34651 intersecting native-radius pairs, all 4562 involved, 42 across generation blocks and 1046 across storage sectors (1088 either). Small-radius proxy 562 conflicts, 1021 involved, zero across generation/storage boundary (prior seam check did not test interior). Closest pair 0.0590592922m, median nearest neighbor 3.653607m. Cumulative raw pair distances: <0.1m 1, <0.25m 1, <0.5m 17, <1m 67, <2m 408. Two source planar roads/20 vertices decoded; nearest anchor to road centerline 5.189m; 65 scaled BBRadius circles reach centerline. NOT actual road-surface encroachment or P3D geometry collision. Overlap of tree crowns can be normal; do not remove all native-radius overlaps. Need actual trunk/geometry LOD and vegetation-density requirements; distinguish road surface, clearance and canopy.

Local verify_native_radii.py source SHA256 f4a626e5f76401ce85bca8ec72c145444c21ab4314ceaddfab7d6d6f5ccb6715, spatial_radius_qc.json SHA256 edccd7271f10902a783098173988ec7df9782d257c174511d6438efa5196aa26. Native runtime 20.73s exit0.

## Review-only candidate

Apply existing profile radii 0.7/1/2m globally instead of only cross-boundary. Stable lexicographic ID order, 4m spatial buckets and neighbor search, preserve exact source CSV lines and IDs for retained objects; hold all rejected IDs with conflicting accepted IDs. No original project edit. Independent count confirms raw 562 proxy pairs. 4054 retained, 508 held; zero remaining proxy pairs; reverse input order identical; conservation 4562, exact retained CSV readback. Counts retained/held 2f 1583/126, 3f 1388/179, 3s 1083/203. This arbitrary stable ID priority is for review only, not validated forest density or physical collision criterion. Candidate not imported. Source verify_spacing_candidate.py SHA256 1d1c34fe7df2f2a04f5309047f5cd17eb4bf9aafaef5ef339c1d2c4453f75250; local SpacingReview/MANIFEST.json SHA256 1065c7b2a8109e9530bafb43ae5a5eafa95236b6300ccfc1fd1a0a63c1b18957; local SPACING_REVIEW.zip 242066 bytes SHA256 1765cb3ec2d5724578b659599ab732fd56d82758bdd5b73913390e76fb8ac33a, 4 files independently archive verified. Scripts in this directory expect the same owned fixture root and pinned inputs; no game assets or private paths committed.

Original GRMAUTO04 tv4p and 67-file ZIP, P: cfg and installed TB opt SHA256 unchanged. No pending ACTION, no viewer process; TB open. Next gate: owner-directed supported TB viewer connection without permanent config edits, or explicitly authorized scoped temporary settings; actual native spatial export through named verified UI; calibrate trunk/road clearance before adopting spacing changes. No stage promotion or merge.
