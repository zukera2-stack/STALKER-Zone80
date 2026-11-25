---
name: zone80-grm
description: Audit and automate the pinned ArmaRealMap GRM CLI, project and asset configurations for MAP-003. Use before any GRM layer or configuration task.
---
# Zone80 GRM
Read AGENT_START.md, AGENTS.md, Issue #42, docs/map/MAP_003_GRM_AUTOMATION.md, docs/automation/LUNA_HANDOFF.md. Latest owner constraints win. This skill does not grant execution permission.

1. Identify actual installed Studio and CLI, versions, executable hashes, upstream tag/SHA v0.11.1 / 2aef2040836daa11a8a368bb0c7f9ecd8f405d65. Do not update installed Studio. Use separate local checkout only after recording provenance and license. No vendored upstream or licensed models.
2. Check CLI help and actual source, parse configs without generation. Example .grma3m uses 64*30 m; SW lat,lon, not lon,lat. Confirm origin, four corners, extent and supported sizes. Force TargetModDirectory to new owned sandbox, never null/default. PboPrefix is only a draft identifier, not permission to build.
3. Audit MapWorkspace, asset resolution, SourceLocations, BuildContext, selected layer generator and all transitive dependencies. Produce table: data type -> builder -> network/disk effects -> elevation/satellite/PAA dependency -> evidence. CLI layer is NOT guaranteed offline or elevation-free. RawElevationBuilder is forbidden. No hidden elevation, satellite, PAA generation or writing P:. No use of unapproved cached heights.
4. Read CentralEurope.grma3a schema; inventory model paths and required addons from read-only local sources. Create a separate candidate asset config using only confirmed permitted resources. Keep buildings disabled in this map task; use no invented P3D paths. OSM geometric facts and procedural objects separate. Unknown material stays unknown.
5. Only run one authorized bounded layer after all gates; use exact CLI absolute executable path, argument array, no shell interpolation. Candidate syntax: grma3 layer -c <local-config> -l forest -t <new-output>. Determine whether forest or trees is actually safe. gentb/genwrp/genmod prohibited in current preflight. Empty layer output is not proof of meaningful generation; verify counts, extents, hashes, repeatability and no unauthorized side effects. 
6. If an elevation dependency exists, STOP/BLOCKED and propose a reviewed GM-input adapter or vector-only export; no silent substitution or fake heights. Preserve completed work. Return one consolidated report, not many new issues.

## Resume 2026-11-25
Read docs/map/MAP_003_CURRENT_CHECKPOINT.md and GRM_CONFIG_PREFLIGHT_V03.md before repeating source/asset review. v02 editor open/save confirmed six surfaces; v03 editor-only transform is tested but native v03 NOT RUN. Reuse inventory, check 22 newly added stock clutter refs, mud, ice and base class/dependency; no inferred approval from a3 prefix or empty Dependencies. Raw owner configs/scripts are separate owner artifacts, not repo files. Verify their hashes. Native layer remains blocked by elevation dependencies.
