# GIS pipeline and CRS approval

## Acquisition
- Record source release/snapshot date, source URL, ODbL or provider license, retrieval UTC, SHA256, geographic coverage and expected size **before downloading**.
- For large OSM areas prefer a local PBF extract imported once to GeoPackage; do not rely on repeated large Overpass requests.
- For DEM distinguish SRTM/GLO-30 posting from true fine terrain resolution; resampling to 20 m does not add detail. Copernicus GLO-30 is a DSM, not a bare-earth survey.
- Historical buildings require separate temporal validity and quality grades, not blind reuse of modern OSM.

## Geometry
WGS84 (EPSG:4326) is the input storage convention. Test one projected metric CRS across the entire fixed square. Candidate UTM 36N or a centered custom Transverse Mercator must be evaluated quantitatively at west/east/north/south control points. Do not finalize EPSG or local XY origin before tests. Store CRS, bounds, axis order, vertical datum and inverse mapping in terrain_extent.json when approved.

## Global Mapper 27
Use Script Builder or documented GMS EXPORT_ELEVATION / EXPORT_VECTOR workflows. Any .gms should be based on actually installed v27 syntax and a small reference DEM; no untested export scripts should masquerade as verified. Prefer tiled data and intermediate files on SSD. Stage 001 deliverable: validated sample DEM export to GeoTIFF + Arc ASCII Grid, reproducible batch script and coordinate-residual report.

## Feature metadata (minimum)
source_id, source_dataset, source_date, license, geometry_confidence, type_confidence, height_confidence, historical_state, manual_override, production_feature_id, review_status. Use explicit unknown/null where evidence is absent. Distinguish placement_accuracy from model_authenticity.
