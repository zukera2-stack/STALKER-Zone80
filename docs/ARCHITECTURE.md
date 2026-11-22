# Design boundaries and data contract

## Layer separation
1. **Geographic source-of-truth**: validated WGS84 geometries for DEM, waterways, roads, rail, building footprints and verified fences.
2. **Reconstruction**: placement of the best-fit allowed P3D with category, footprint dimensions, orientation, floors, known model path and authenticity grade.
3. **Gameplay fiction**: lore locations, wrecks and procedural decorations with recorded seeds, separate from factual historical objects.

## Dataflow
Acquire source + checksum + license → immutable raw archive → normalized spatial database and common metric CRS → confidence and historical tagging → buffered sector extraction → owner-only placement output → deterministic sorted object spool → **single** final WRP → Binarize/PBO → game tests.

Source IDs e.g. osm:way:123456, ohm:way:123456, manual:pripyat:block12:bldg07. Derived procedural IDs e.g. procedural:fence:osm:way:123456:seg0042. Normalization must not change source identity.

## Sector invariants
Logical index x,y in [0,7]. Sector size 10,240 m, coordinate bounds half-open [min,max), except full-world upper bound can be deliberately clamped. Buffer is read-only context, never ownership. A point belongs to exactly one index computed from its anchor. Polygon owner defined consistently by stable centroid/anchor; lines clipped into pieces with original source ID and deterministic segment indices. Adjacent sector reruns must produce identical stable IDs and geometry.

## Assets
Asset manifest is metadata only. Real virtual addon paths, CfgPatches, requiredAddons, dimensions, LOD and license rights require verification. Source PBOs stay in their original directories.

## Non-goals for initialization
No automated scraping/downloading of a whole region; no 64-WRP binary concatenation; no upstream GRM rewriting; no asserted historical accuracy for undocumented props; no generated Arma terrain yet.
