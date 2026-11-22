# GRM audit worksheet (fill with measured evidence only)

Upstream tag / HEAD SHA: NOT TESTED.
Local Studio version and target .NET runtime: NOT TESTED.
Build unchanged: NOT TESTED.
Demo/small regeneration: NOT TESTED.
Known previous user's symptom: generation exhausted 32 GB RAM (cause unknown).

Inspect and document: BuildContext caching and lifetime; BuildersCatalog/GetData<T>; RawSatelliteImageBuilder/HugeImages; DEM/SRTM builder; OSM data graph; object-layer generator; WRP writer; CLI genwrp/gentb/genmod/layer; concurrency; memory use through pipeline. Include direct code locations, command line, object counts, stage timings, Private Bytes vs Working Set and allocations.

Do not begin patches before measurement; document every hypothesis as hypothesis. If upstream terms for source redistribution are unresolved, keep patches out of public repo until reviewed.
