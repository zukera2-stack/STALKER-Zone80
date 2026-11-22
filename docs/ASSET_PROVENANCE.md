# Addon asset index / legal gates

The owner will supply existing mod folders containing houses, fences, wrecks, cars and equipment. **Never** modify, overwrite, copy into Git or repack the original PBO/P3D/PAA. Scan originals read-only and put all derived metadata into ignored local assets/catalog/.

Target metadata catalogue: asset_id; addon; pbo; hash; prefix; virtual_path; classname; model_path; bounding box x/y/z; footprint ratio; candidate category; estimated floors; visual/geometry/fire/view LOD; requiredAddons; license_status; license_source; redistribution_allowed; dependency_only; review_notes; quality_tier; allowed_for_zone80.

Stage-001 scanner only produces a basic physical file inventory and checksums; internal PBO contents/config dependency/LOD/bounding analysis remain unverified until official tools and explicit addon permissions are available. **UNKNOWN license = not approved**.

Prefer external mod dependencies for final terrain. Matching requires width, depth, floors, category, orientation and manual review for landmarks such as CNPP and iconic Pripyat architecture. Never automatically scale every P3D to fit an arbitrary polygon.

Sources: https://community.bohemia.net/wiki/BankRev and https://community.bohemia.net/wiki/CfgConvert
