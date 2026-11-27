# A3-first: структура оригинальных миров и повторное использование штатных ресурсов
26.11.2026. MAP-003 / Issue #42 / Draft PR #50. Владелец поручил изучить P: и максимально использовать базу A3. Базовый SHA c567d04d27db2e1d3f093ee70dfec07cfe1b23f7. Источник измерений: локальный P:\a3, read-only PowerShell (списки каталогов, чтение текстовых config/RVMAT, заголовков SHP/DBF, Test-Path, SHA-256 PRJ). Не запускались Terrain Builder, Arma, распаковщики, конвертеры; не изменялись P:, чужие проекты или настройки. Луна не получила нового задания. Ни одного оригинального бинарника, текстуры, карты или полного конфига не копируем в репозиторий.

## Решение: native A3 by reference first
Приоритет: уже установленный ресурс A3, проверенный по назначению, зависимостям и правам; затем собственный авторский ресурс только для отсутствующей/неподходящей детали. Используем ссылки a3/... из наших конфигов/WRP, а не дублируем содержимое P: в моде. Штатный ресурс не означает обязательно бесплатный для всех игроков. Не перепаковывать оригинальные PBO, WRP, P3D, PAA или обходить DLC. Выбор базового мира, перечень обязательных DLC, итоговый профиль и runtime closure не утверждены. Не копировать оригинальный CfgWorlds целиком: география, климат, время, населённые пункты и карты должны быть нашими. Не переопределять глобальные классы A3 случайно. Использовать уникальный namespace Zone80 и штатное наследование/ссылки после проверки.

## Измеренная архитектура оригинальных карт
| Карта / каталог | WRP bytes | mapSize m (прочитанный config) | DBF records |
|---|---:|---:|---:|
| Enoch / map_enoch | 207580126 | 12800 | 407 |
| Altis / map_altis | 183317346 | 30720 | 1414 |
| Stratis / map_stratis | 26304095 | 8192 | 73 |
| Tanoa / map_tanoabuka | 170708437 | 15360 | 719 |
| Malden / map_malden | 55417351 | NOT_READ | 212 |
| VR / map_vr | 393427 | NOT_READ | 10 |

Each has root config.cpp, WRP and data directory. Enoch data has 59 PAA, 13 RVMAT, 2 P3D plus config, rap.txt, texheaders.bin and roads. Larger maps' data/layers not present on inspected P:; do not conclude absence in game, nor recreate a TB project from compiled WRP. Enoch CfgAddons preload explicitly refers to A3_Map_Enoch_Data_Layers; full source project not found/inspected. VR data/layers has 64 each s_*_lco.paa, m_*_lca.paa, n_*_no.paa, p_*.rvmat (256 files). Example p_000-000_l00.rvmat links satellite, material mask, detail normal/color and satellite normal via TerrainSNX/Terrain and worldPos UV transforms. Pattern is packaging reference only; tile size/overlap/UV values not approved for Zone80. Do not copy VR material geometry or index assumptions to another map. WRP internals NOT_READ. GM prepares source georaster; GRM prepares game material semantics; TB generates engine-specific layers from reviewed mask/material definitions. Keep logical production sectors distinct from TB mapframes and rendered texture tiles.

## Surfaces: Enoch as regional reference, actual files checked
Every row below: local matching _co.paa + _nopx.paa + .rvmat in a3/map_enoch/data present (33/33 file checks). Enoch's CfgSurfaces uses wildcard file prefix and character binding.
| Surface | Prefix | Character | Proposed Zone80 usage (not final mapping) |
|---|---|---|---|
| GdtKLDirt | gdt_dirt | empty | dirt/gravel |
| GdtKLGrass1 | gdt_engrass1 | KLGrass1 | meadow |
| GdtKLGrass2 | gdt_engrass2 | KLGrass2 | tall grass / overgrown field |
| GdtKLForestCon | gdt_enforestcon | KLForestCon | conifer forest floor |
| GdtKLForestDec | gdt_enforestdec | KLForestDec | deciduous forest floor |
| GdtKlSoil | gdt_ensoil | KLSoil | exposed soil |
| GdtKlTarmac | gdt_entarmac | Empty | asphalt |
| GdtKlWeatheredTarmac | gdt_enweatheredtarmac | KlWeatheredTarmac | worn asphalt |
| GdtKLCobblestone | gdt_encobblestone | Empty | cobblestone |
| GdtKlField | gdt_enfield | KLField | cultivated land |
| GdtKlStubble | gdt_enstubble | KLStubble | stubble |
RVMAT sampled gdt_enforestdec references matching nopx and co, both stages UV scale 10 in original material; do not equate this with GRM texture scale or meters without test. CfgSurfaces controls surface sound, dust, roughness, speed and grassCover; do not silently copy tuning values as physical facts. Enoch clutterGrid 1.3, clutterDist 100, noDetailDist 65, fullDetailDist 10, satelliteNormalBlendStart/End 10/100; reference only, performance for 81.92km target not established. Eight CfgSurfaceCharacters checked: 2+2+10+9+2+3+9+7 named memberships; all resolve to local DefaultClutter definitions and all referenced files exist. 43 unique model paths in inspected Enoch clutter section, 43 present. Some memberships overlap. No runtime tests. Distinguish engine clutter (grass, leaves, mushrooms etc rendered from surface character) from GRM placed trees/large bushes/objects; do not place same clutter as individual WRP objects by default.

For v03 prior mud question: a3/map_data/config.cpp actually defines GdtMud, wildcard gdt_mud_*, character MudClutter. Texture pair a3/map_data/gdt_mud_co.paa and _nopx.paa present in earlier local inventory. This supports candidate, not automatic equivalence to river/lake bottom. Need actual MudClutter inheritance/availability in selected world; not same as Enoch gdt_enmud (file pair exists, no GdtEnMud class established in inspected 11 surfaces). Water, ice, scree and unusual surfaces require explicit mappings or reviewed unused policy; no silent defaults, no replacing ice by white texture. Preserve v03 editor-only until full parser/dependency gate.

## Roads: native format and coordinate boundary
All six map data/roads directories contain roads.shp/.shx/.dbf/.prj and roadslib.cfg. SHP header type 3 (polyline) for all. Enoch roadslib active five types: 1 main asphalt 14m; 2 asphalt 10m; 3 track 7m; 4 asphalt 8m; 5 pedestrian trail 1.6m. All 15 direct texture/end/material path checks pass; all five explicitly read nested normal-map paths in their RVMAT pass. Do not mistake authored game width for observed real-world width. Enoch DBF has __LAYER, ID, WIDTH, __ID; 407 active records, ID1=8, ID2=107, ID3=292, ID4/5 unused in this DBF; no deleted records. ID maps to road type, not a unique OSM feature ID. Other official maps have ORDER, ROADMASK, WIDTH etc differing schemas; inspect required schema for actual TB/runtime. Keep source stable IDs separately, define semantic mapping for OSM types, no duplication of area outlines, sidewalks/bridges/tunnels need explicit treatment.
All six roads.prj byte SHA-256 20451220b3475131fbfd7cf3983f9fd1fd14bd87e33c6d8190a1cca9b0717808. Enoch PRJ is WGS84 Transverse Mercator central meridian 3 degrees, false easting 500000, scale .9996, false northing 0, not our EPSG32636. SHP header ranges (Xmin,Ymin,Xmax,Ymax) Enoch 200002.669,116.415,212801.688,12795.775; Altis 202663.700,5015.855,228319.190,25768.652; VR 200609.413,1525.139,201639.699,2032.021. These show common TB-style offset/world-local export conventions, not real geographical positions; do not blindly copy PRJ or apply +200000 without verified mapframe/import control. Maintain authoritative source UTM/CRS and independent local/world coordinate transform, exact anchors, axis order, height units and round-trip five asymmetric controls. Verify in small sandbox only after source acceptance. No native road conversion or placement performed.

## Actual GRM reference overlap with local A3
Read current configs/grm/{vegetation,roads,materials,infrastructure}.references.json from baseline SHA, case-normalized unique referenced paths in main arrays (exclude additional unselected candidates and generic Buildings). Checked exact leaf path for each a3 prefix against P:. 
| Catalog | A3 refs | Present | External refs |
|---|---:|---:|---:|
| Vegetation | 76 | 76 | 0 |
| Roads | 18 | 18 | 0 |
| Materials | 32 | 32 | 18 |
| Infrastructure | 60 | 60 | 5 |
| Combined deduplicated | 181 | 181 | 23 |
204 unique total in upstream reference inventory, not the 203-path v03 transformed profile; separate scope. This is path existence only, not P3D integrity, runtime entitlements, geometry, material closure or approved assets. Do not mark reference JSON approved/verified globally or claim the 22 additional v03 clutter paths checked: exact v03 input list not reopened in this turn. Existing 181 all present is evidence for A3-first, not guarantee of all local stock. Additional candidates measured recursive P3D counts: vegetation_f_enoch/tree 68, bush14, clutter40, crop1; plants_f/tree15, clutter113; structures_f_enoch/ruins18, infrastructure118, industrial132; structures_f/bridges8; roads_f/sidewalks4. Counts are files, not unique species/usable models. Prefer temperate regional vegetation, native road textures, fences, rails, concrete, ruins, utility props where visual/geometry checks pass. Tropical/modern/mediterranean assets not default. Authentic Pripyat buildings, Soviet identity assets, interiors and unique landmarks remain separate ZPB; procedural proxy must not be presented as real building. Use existing infrastructure audit; do not create new generic building generation.

## Dependency and rights gates
Read first declared CfgPatches and requiredAddons of inspected root configs (not full recursive closure):
- A3_Map_Enoch -> A3_Data_F_Enoch, A3_Map_Data_Exp, A3_Structures_F_Enoch
- A3_Map_Enoch_Data -> A3_Map_Enoch
- A3_Vegetation_F_Enoch, A3_Structures_F_Enoch, A3_Rocks_F_Enoch, A3_Props_F_Enoch each first declaration -> A3_Data_F_Enoch
- A3_Plants_F -> A3_Data_F; A3_Roads_F -> A3_Data_F
- A3_Map_Data -> A3_Data_F, A3_Roads_F, A3_Structures_F; A3_Map_Data_Exp -> A3_Map_Data
Per-asset nearest owning config, nested material/texture dependencies and recursive graph still needed. Enoch itself is a terrain reference, not approved base class; v03 currently inherits arm_world_centraleurope / arm_centraleurope. Prefer a verified independent CAWorld-derived Zone80 config or reviewed stock base with minimal dependencies; compare actual generated GRM config and inherited clutter/global classes, no silent substitution of base name. A3 base game entitlement vs DLC platform assets vs premium DLC differs, test with intended non-owner client and verify official rules; do not infer requirement/free from folder name. Source BI docs: https://community.bistudio.com/wiki/Arma_3:_DLC_Restrictions ; https://community.bistudio.com/wiki/Arma_3:_DLC_Content_Licensing ; https://www.bohemia.net/en/licenses ; https://www.bohemia.net/en/licenses/faq ; https://community.bistudio.com/wiki/Arma_3:_CfgSurfaces_Config_Reference ; https://community.bistudio.com/wiki/CfgWorlds_Config_Reference ; https://community.bistudio.com/wiki/Arma_3:_Common_Terrain_Creation_Problems . Reference original installed assets in Arma, not redistribute proprietary payload; separately published licensed data may be modified only under applicable license.

## Next implementation contract (not a new local job)
1. Reuse CC04 and existing config manifests, not a new framework. Asset status stages: PATH_PRESENT -> REGIONAL_FIT -> DEPENDENCY_CLOSED -> RIGHTS/ENTITLEMENT_ACCEPTED -> NATIVE_VALIDATED -> APPROVED. Record source path, owner CfgPatches, model bounds/pivot, material links, licence, DLC requirement, selected role, provenance; fail closed if unknown. Preserve previous evidence.
2. Build reviewed Zone80 v04 candidate only after reopening exact v03 and 22 paths, resolving 23 external upstream references vs transformed profile, ice/water policy and independent base world. Use one explicit material usage -> mask RGB -> stock texture pair -> matching CfgSurface -> CfgSurfaceCharacters -> clutter class -> P3D chain, plus road type ID and roadslib fields. No duplicate class names/mask IDs, no unknown fallback. Use templates and source references, no original file copies.
3. Check native parser, minimal requiredAddons and one sandbox test (after explicit gate); verify actual surface appearance, clutter, texture transitions, road alignment, object placement, absence of missing paths, DLC non-owner test. Scale only after seam and performance QA.
4. Production split proposal: Zone80 world WRP/config and generated layers/roads, separate own ZPB assets and optional additional modules; runtime references to A3. Exact PBO subdivision and prefixes remain design, not release output. Global Mapper primary GIS, GRM game profile and objects, TB final engine-specific assembly.
G1 diagnostic QC PASS, source acceptance pending; G2 real imagery BLOCKED_WMTS_ACCESS; native synthetic task prepared, not run by this audit. Stage001 PARTIAL. No new job to Luna, no P: write, network data acquisition, native generation, merge, or promotion.
