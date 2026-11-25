# CC-04 — review-only Config Builder / Asset Manager
Python 3.10+ standard library; tested Linux Python 3.13.5. No native `.grma3a` output and no writes to project or P: by the tool. `production` is deliberately refused. Exit 0 means review completed, not native approval.

`python -m unittest -v test_config_builder.py`

`python config_builder.py BASELINE.grma3a CANDIDATE.grma3a INVENTORY.json` prints deterministic review JSON to stdout. Keep the original owner baseline and inventory immutable. Six modular groups are assembled in memory, material usage/RGBA and road IDs locked to the baseline, references audited. Inventory presence is not dependency or license proof. Unknown or missing assets are explicitly unapproved. The baseline is a trusted input, not authenticated evidence.

`python demo.py --baseline Zone80_v02.grma3a --inventory Zone80_inventory.json --v03-zip Zone80_Config_Preflight_v03.zip [--repo-root REPO]` reproduces the v03 summary; optional repo root audits the four reference catalogs and ZPB metadata. The owner input files are not bundled. Synthetic dependency closure tests validate graph behavior only, not installed CfgPatches. ZPB review cannot select even MODEL_READY until local evidence and placement permission are verified. No full recursive native schema validation, real PBO closure, Windows/Studio/Arma test or scheduler. No new heights. Stage 001 PARTIAL.
