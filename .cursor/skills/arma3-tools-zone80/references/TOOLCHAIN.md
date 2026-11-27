# Arma 3 Tools — routing reference

| Tool | Intended usage | Safe at Stage 001 |
|---|---|---|
| Terrain Builder | DEM/ASC, imagery, objects, mapframes | Only tiny sandbox inspection and explicitly authorized test import |
| Work Drive (P:) | Project workspace/mapping | Read-only status; never auto-mount or change P: |
| Object Builder | P3D authoring, LODs and material configuration | Inventory + owner-authorized editable-source inspection |
| Addon Builder | PBO packaging | DO NOT RUN in Stage 001 |
| Binarize | Asset and terrain compilation | DO NOT RUN in Stage 001 |
| CfgConvert | Game config conversion | Discover version only; don't mutate originals |
| Terrain Processor | Placement/terrain processing | Plan only until authorized |
| Buldozer | Real-time Arma terrain/model preview | Requires real GUI evidence and authorization |

The inventory script checks only an explicit installation root, or Steam defaults under Program Files, to a bounded depth. NOT FOUND is not proof of absence if tools are installed on another drive.

A TML library defines templates; a valid TML does not prove a P3D model exists or has a redistribution license. Maintain source_id, stable placement ID, owner sector, intended template, verified model dependency and license provenance separately.

Official references:
- https://community.bistudio.com/wiki/Arma_3:_Tools
- https://community.bistudio.com/wiki/Work_Drive
- https://community.bistudio.com/wiki/Addon_Builder
- https://community.bistudio.com/wiki/Binarize
- https://community.bistudio.com/wiki/CfgConvert
- https://community.bistudio.com/wiki/LOD
- https://community.bistudio.com/wiki/Buldozer_Manual
- https://community.bistudio.com/wiki/Terrain_Processor:_Introduction
