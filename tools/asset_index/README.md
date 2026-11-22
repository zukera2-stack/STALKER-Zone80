# Asset inventory stage 001

Use scan_assets.py only on an addon directory selected by the owner. Files are opened read-only; sorted filenames, size, timestamps and optionally SHA256 are written into ignored assets/catalog/scan.csv. It supports loose PBO/P3D only; it does not extract PBOs, read packed P3D models, resolve paths/classnames, calculate bounding boxes, license models, or approve redistribution. No false claims about these fields.

Stage 002 candidate work: run permitted official BankRev/CfgConvert tools in a dedicated scratch directory, infer config + model relationships, verify LOD/geometry, emit reviewed assets.sqlite and class catalog without modifying the user mod.
