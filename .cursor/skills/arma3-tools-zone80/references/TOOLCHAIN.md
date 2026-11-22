# Arma 3 Tools — toolchain map (skill reference)

This reference distinguishes read-only discovery, manual editing and dangerous output-producing operations. Official Bohemia Interactive documentation may change; confirm against installed versions before invoking any executable.

| Program | Purpose | Safe Stage 001 activity | Not authorized by this skill |
| --- | --- | --- | --- |
| Arma 3 Tools Launcher | Launcher and preferences | Locate and record version | Reconfigure paths or launch automated builds |
| Work Drive | Project working drive (commonly P:) | Check whether P: exists; inspect drive mapping metadata | Mount/unmount, copy/extract protected PBOs |
| Terrain Builder | Heightmap, objects, surfaces, mapframe editing | Inspect a small synthetic sandbox, after owner permission | Build Zone80 world, export WRP or full Terrain |
| Object Builder | Editable P3D model construction, LOD and selection editing | Inventory executable, inspect allowed unmodified metadata | Modify third-party P3D or unbinarize protected assets |
| Addon Builder | Addon packing; can invoke Binarize | Identify location/version, plan command in writing | Build PBO, sign or publish addon |
| Binarize | Binarizes game assets, textures/model processing | Read version/docs only | Binarize any original or final package |
| CfgConvert | Convert config text/binary representation | Locate executable | Convert original asset configs |
| Terrain Processor | Process terrain object distribution; export LBT | Read tool docs and inspect version | Populate real Zone80 objects |
| Buldozer | Preview game terrain/model in editor context | Record prerequisites | Claim visual preview without real launch evidence |

## Read-only executable discovery

Run scripts/inspect_arma_tools.ps1. The script searches only known candidate Arma 3 Tools roots (or the -ToolsRoot parameter), with bounded directory depth. It never recursively searches an entire drive or P:, never reads PBO contents, and never invokes an Arma binary.

Example:

    pwsh -NoProfile -File .cursor/skills/arma3-tools-zone80/scripts/inspect_arma_tools.ps1 -ToolsRoot "C:\Program Files (x86)\Steam\steamapps\common\Arma 3 Tools"

Record actual executable path, signed/file version when available, P: existence, and whether Windows PowerShell/PowerShell 7 and actual local terminal were used. Many installations live outside default Steam roots; NOT FOUND from default scan is inconclusive.

## Windows UI work — gated

For later authorized synthetic tests:
1. Open ONLY a purpose-built copy under ignored reports/ and verify the target project path.
2. Avoid global/preferences changes without the owner's permission; particularly do not alter P: mapping while another editor instance is open.
3. Check output locations twice; preserve input hashes and original user files.
4. Export or save only within the test sandbox. Stop before Binarize/Addon Builder unless separately approved.
5. Keep actual evidence: screenshot of GUI version and Mapframe coordinates, log paths, observed object positions. If no UI access, state NOT TESTED.

## Asset and dependency integrity

A TML library is an object template list; it is not a model distribution package or proof that a model can be resolved in Terrain Builder. A symbolic model name in CSV is not necessarily the P3D path. Maintain a separate source_id -> template/model -> owner -> license manifest. Never publish assets with unknown redistribution rights. Do not add fictitious Arma model paths as if verified.

## Official sources (use exact tool/version for decisions)
- Arma 3 Tools listing: https://community.bistudio.com/wiki/Arma_3:_Tools
- Work Drive: https://community.bistudio.com/wiki/Work_Drive
- Addon Builder: https://community.bistudio.com/wiki/Addon_Builder
- Binarize: https://community.bistudio.com/wiki/Binarize
- CfgConvert: https://community.bistudio.com/wiki/CfgConvert
- Object LOD overview: https://community.bistudio.com/wiki/LOD
- Buldozer Manual: https://community.bistudio.com/wiki/Buldozer_Manual
- Terrain Processor: https://community.bistudio.com/wiki/Terrain_Processor:_Introduction
- Cursor Agent Skills: https://cursor.com/docs/skills
