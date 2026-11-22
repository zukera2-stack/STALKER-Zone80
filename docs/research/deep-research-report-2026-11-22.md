# Мастер-план STALKER Zone80: реальная Чернобыльская зона для Arma 3

## Вывод и целевая архитектура

Проект **реально стоит продолжать**, но не как «запустить GameRealisticMap на 80×80 км и дождаться результата». Для карты с реальными зданиями, дорогами, заборами, промышленными объектами и вашим набором Arma 3 assets нужен собственный воспроизводимый конвейер, в котором GameRealisticMap является одним из компонентов, а не единственным генератором. Сам GRM уже построен именно как C#-toolchain с независимыми builders, отдельным Arma 3-слоем, CLI, WRP/PBO-генерацией и локальной системой координат; он получает OSM, SRTM и спутниковые данные и умеет преобразовывать их в Arma 3 world. citeturn623001view1turn623001view0

Целевой world я бы зафиксировал как **81 920 × 81 920 м, heightmap 4096², terrain cell 20 м**. Арифметически это ровно `4096 × 20 = 81 920`, то есть искомые 80 км помещаются внутрь с небольшим техническим полем. Это не означает, что конфигурация уже доказана работоспособной на вашем компьютере: её нужно подтвердить последовательными испытаниями 1–2 км → 10,24 км → два сектора → полный world. Документация Bohemia подтверждает связь размера мира с resolution и cell size; в сообществе Terrain Builder 4096² считается значительно безопаснее 8192², а для cell 20 м рекомендуют texture layer около 80 м. citeturn594636search2turn594636search1turn985663search0

Ключевая идея масштабирования: **один WRP, но данные готовятся пространственными партиями**. WRP по своей структуре содержит terrain grids и последовательность размещённых объектов; отдельного «счётчика общего количества объектов» в описании формата нет. Поэтому я не нашёл первичного источника, подтверждающего распространённое утверждение о каком-либо универсальном жёстком лимите вида «N миллионов объектов». Практический предел будет определяться Terrain Builder/Binarize, размером WRP, памятью генератора, стоимостью spatial lookup, streaming и производительностью Arma 3. Ошибка Terrain Builder «Too many objects in grid rectangle» также не является доказательством глобального object cap. citeturn594636search0turn594636search4

Для проекта следует разделить данные на три класса достоверности. **Географическая истина**: координаты рельефа, дорог, footprint зданий, водоёмов, железных дорог и подтверждённых ограждений. **Визуальная реконструкция**: выбор наиболее похожей P3D-модели для реального footprint. **Игровой слой**: STALKER-локации, дополнительные wrecks, аномалии, декор и драматургические изменения. Смешивать эти три уровня в одном генераторе нельзя: иначе впоследствии невозможно будет понять, где реальный объект, где реконструкция, а где художественное решение.

Состояние Windows сейчас надо считать **непроверенным**. В текущем задании целевая конфигурация — Windows 11 Pro, но в предыдущих разговорах фигурировала Windows 10. Cursor в самом начале должен получить фактические `ProductName`, `DisplayVersion`, `BuildNumber`, объём RAM, pagefile, диски и версии .NET/Arma Tools. Наличие `Zona.grma3m`, локальных аддонов и других файлов тоже должно подтверждаться только поиском на вашем ПК; исследование не предполагает доступа к ним.

## Ограничения Arma 3 и конструкция мира

Terrain Builder импортирует квадратные heightmap-сетки степени двойки; официальный пример Terrain Processor использует ASC/UTM и показывает прямую связь grid count, cell size и размера terrain. Для 4096² × 20 м геометрическая часть world не является необычной по структуре, но 81,92 км — уже экстремальная площадь по количеству объектов и растров. Bohemia отдельно отмечает, что land grid используется движком для размещения и поиска объектов и dynamic simulation, а terrain grid — для поверхности и высот; поэтому увеличение площади не сводится только к размеру heightmap. citeturn594636search3turn594636search2

Для Terrain Builder разумная стартовая конфигурация Zone80:

| Компонент | Базовое решение | Статус |
|---|---:|---|
| World size | 81 920 м | решение проекта |
| Terrain grid | 4096² | консервативный выбор |
| Cell | 20 м | решение проекта |
| Texture layer | ~80×80 м | соответствует рекомендации для cell >10 м |
| Prototype | 512² × 20 м = 10,24 км | решение проекта |
| Micro-pilot | 1–2 км | для проверки реальных домов |
| Full 8192² | не использовать до отдельного доказательства | высокий риск |

Для крупных terrains со cell 20 м community documentation Bohemia рекомендует texture layer примерно в четыре cell, то есть 80×80 м; неправильный размер texture layer способен вызывать ошибки land-grid и проблемы физики/AI. При этом рекомендация «8192 broken» находится на community sandbox-странице, а не в формальной спецификации движка, поэтому её следует считать сильным практическим предупреждением, но не математическим запретом формата. citeturn985663search0turn594636search1

Спутниковый raster быстро становится главным объёмом. При 4 м/px карта 81,92 км требует `20 480 × 20 480` пикселей, то есть около **1,56 GiB** только для одного несжатого RGBA-буфера. При 2 м/px это уже около **6,25 GiB**, а при 1 м/px — примерно **25 GiB** на единственный RGBA-слой. Любая операция, создающая source + working copy + output, может превысить 32 ГБ ещё до обработки объектов. Поэтому full-map satellite нельзя держать как несколько обычных ImageSharp images: он должен быть tiled/memory-mapped или собираться по блокам.

Для «максимальной точности домов» satellite texture не является источником моделей. Sentinel-2 даёт 10 м в наиболее детальных спектральных каналах, чего недостаточно для точного выделения большинства отдельных построек, заборов и автомобилей. Sentinel полезен как фон, landcover и временной контроль, но не как источник сантиметровой/метровой геометрии. citeturn239165search1turn239165search3

Нельзя заранее обещать сохранение каждого дерева, автомобиля или забора на площади 6700 км². Структура WRP допускает длинный список объектов, но Arma должна ещё выполнять spatial queries, physics, AI и rendering. Поэтому для каждого класса объектов должен существовать **quality tier**: `Q0 absent`, `Q1 sparse`, `Q2 normal`, `Q3 landmark/high fidelity`. Фактические пороги объектов на км² следует получить измерением, а не взять из форумных советов.

## GameRealisticMap как основа, но не как монолит

Актуальный репозиторий `jetelain/ArmaRealMap` содержит отдельные проекты `GameRealisticMap`, `GameRealisticMap.Arma3`, Studio, Generic export и два CLI; Arma 3 CLI документирован с verbs `genmod`, `genwrp`, `gentb`, `layer`. Архитектура использует `IDataBuilder<T>`, lazy `GetData<T>()` и caching результатов в контексте. `Pmad.HugeImages` уже предназначен для memory-mapped huge-image storage, что очень полезно именно для Zone80. citeturn623001view1turn985663search8

Это одновременно объясняет возможный источник вашей прежней аварии по RAM. Lazy build сам по себе экономит вычисления, но если результаты builders остаются закешированными до завершения всей генерации, большой OSM graph, satellite images, elevation, geometries и object lists могут существовать одновременно. Дополнительно новые версии GRM параллелизовали часть генерации, что сокращает время, но потенциально увеличивает peak working set. Это **гипотеза, которую Cursor обязан измерить**, а не считать установленной причиной вашего сбоя. citeturn623001view1turn157167view0

В релизах репозитория действительно присутствуют исправления ImageSharp memory limit, обновления .NET/dependencies, поддержка memory-related stability, custom source endpoints и cache management. По состоянию просмотренной страницы release-линия содержит pre-release `v0.10.130`, а исправление ImageSharp видно в `v0.10.4`; поэтому старое предположение про обязательные версии 0.11.x нельзя использовать без проверки локальной установки и актуальных tags. citeturn157167view0turn157167view1

Минимальная ветка патчей GRM должна выглядеть не как «переписать генератор», а как instrumentation → ограничение concurrency → освобождение/вытеснение тяжёлых cached objects → возможность внешнего prepared data. В первую очередь Cursor должен измерить `BuildContext`, `RawSatelliteImageBuilder`, elevation builders, OSM builders, `Arma3LayerGeneratorCatalog` и WRP writer. Если peak создаёт satellite stage, секторизация объектов не поможет; если peak создаёт объектный список перед WRP — понадобится streaming/spooling placement records на диск.

**Тайловая генерация единого WRP осуществима концептуально, но пока не доказана текущим GRM.** Сектора должны быть всего лишь единицами вычисления: каждый обрабатывает buffered bbox, выдаёт нормализованные records, а финальный writer создаёт один WRP. Нельзя генерировать 64 независимых WRP и «склеивать» их на бинарном уровне: WRP содержит единую terrain-grid структуру и единый объектный список. citeturn594636search0turn623001view1

Правило владения объектом между тайлами должно быть детерминированным. Для point-object owner определяется сектором точки-якоря; polygon building — сектором centroid или стабильного source ID; длинная дорога может быть геометрически разрезана, но её исходный `source_id` сохраняется; fence segment получает дочерний ID от source way + segment index. Buffer нужен, чтобы геометрические операции на краях сектора знали соседей, но запись в финальный слой разрешается только owner-сектору. Тогда повторный запуск не создаёт дубликаты.

Отдельно необходимо проверить юридический статус самого исходного кода ArmaRealMap перед распространением модифицированной сборки. В отображённом дереве корня репозитория отдельный `LICENSE` не виден, поэтому публичность GitHub-репозитория нельзя автоматически трактовать как разрешение на любое распространение производных версий. Это именно пункт юридического аудита, а не утверждение об отсутствии какой-либо лицензии вообще. citeturn623001view0

## GIS, реальная география и историческая реконструкция

Для GIS Global Mapper 27 подходит хорошо: официальная документация поддерживает `.gms`, `EXPORT_ELEVATION`, `EXPORT_VECTOR` и запуск script-файла непосредственно из командной строки; Script Builder может записывать действия GUI в GMS. Значит, Cursor может генерировать параметры и запускать повторяемый экспорт, не щёлкая вручную сотни тайлов. citeturn824561search44turn824561search3turn824561search19

OSM лучше однажды получить в `.osm.pbf`, а затем преобразовать в локальный GeoPackage/PostGIS/SQLite, чем постоянно гонять большую область через публичный Overpass. GDAL прямо предупреждает, что OSM/PBF driver для больших datasets лучше использовать для импорта в нормальную GIS-базу; его временные индексы можно вынести на диск, а spatial filtering исходного PBF способен терять вершины длинных геометрий, поэтому предпочтительнее сначала импортировать полный региональный extract, затем резать его уже в GeoPackage. citeturn824561search0

Overpass полезен для точечных запросов и проверки актуальности, но не должен быть главным production backend Zone80. Overpass поддерживает time-based/attic querying, однако OSM ориентирован прежде всего на текущую реальность, а давно снесённые здания рекомендуется хранить в OpenHistoricalMap, а не в основной OSM. citeturn824561search2turn824561search38turn852068search5

Для высот базовый SRTM имеет примерно 30 м posting; Copernicus GLO-30 также является 30-метровым продуктом, причём это DSM — он отражает поверхность с инфраструктурой и растительностью, а не чистый bare-earth DTM. Поэтому resample на 20-метровую Arma grid не создаст реальной 20-метровой детализации: это лишь интерполяция. Для Чернобыля этого достаточно для крупного рельефа, но насыпи, дамбы, канавы, железнодорожное полотно и промышленные площадки придётся корректировать отдельными vector rules/manual overrides. citeturn239165search2turn852068search1turn852068search2

Координаты требуют отдельного инженерного решения. Часть предполагаемой 80-километровой области вокруг Чернобыля может пересечь меридиан 30°E — границу UTM zones 35N/36N. GRM использует локальные terrain metres и отдельное преобразование к WGS84, поэтому в проекте лучше хранить исходную географию в WGS84, а для production-area выбрать **единую** метрическую CRS, после чего преобразовать всё только один раз в локальную `Zone80 XY`. citeturn623001view1turn594636search3

Я не рекомендую слепо фиксировать EPSG:32636 до теста. Практический кандидат — UTM 36N, если вся выбранная квадратная область и ошибка масштаба устраивают, либо собственный локальный Transverse Mercator с центральным меридианом около середины проекта. Критерий выбора — не «какой EPSG красивее», а residual error по контрольным точкам на западном/восточном краях. В `terrain_extent.json` должны храниться geographic bbox, production CRS, local origin, world size и forward/inverse transforms.

Для исторических зданий нужен отдельный temporal GIS. OpenHistoricalMap использует `start_date`/`end_date` именно для существования объектов во времени; USGS EarthExplorer хранит Landsat и declassified satellite imagery, включая CORONA/ARGON/LANYARD, которые могут дать дополнительные эпохи для реконструкции. Однако наличие конкретного снимка нужной даты и достаточной детализации для Припяти/ЧАЭС надо проверять по coverage; историческое изображение само по себе не даёт права уверенно восстановить форму здания без геопривязки и визуальной верификации. citeturn852068search3turn852068search4turn239165search16turn239165search20

Для каждого реального объекта следует хранить не только geometry, но и provenance: `source`, `source_id`, `source_date`, `geometry_confidence`, `type_confidence`, `height_confidence`, `historical_state`, `license`, `review_status`. Тогда можно честно отличить «footprint из OSM с точностью порядка нескольких метров» от «контур вручную восстановлен по ортофото 1986 года» и от «дом поставлен приблизительно».

Особенно важно различать **точное положение здания** и **подлинную 3D-модель здания**. OSM building polygon может дать footprint, иногда `building:levels`, `height`, `roof:*` и тип; но он не сообщает, какой P3D из вашего мода является именно этим домом. Автоматический matcher может подобрать proxy по ширине, длине, этажности, типу и ориентации, но это остаётся реконструкцией. В отчётах объект должен иметь, например, `placement_accuracy=A`, но `model_authenticity=C`.

Заборы и wrecks ещё сложнее. OSM иногда содержит `barrier=fence`, но не каждую секцию реального забора; исторические автомобили практически никогда не картографируются с нужной временной точностью. Следовательно, нельзя заявлять «реальное расположение каждого заброшенного автомобиля». Машины следует разделить на `documented` — подтверждены конкретным снимком/источником, и `procedural` — генерируются по семантическим зонам с deterministic seed.

## Инвентаризация вашего мода и автоматическое сопоставление assets

Ваш локальный мод с домами, заборами, wrecks, машинами и техникой должен сначала стать **read-only каталогом assets**. Ничего нельзя распаковывать обратно поверх оригиналов или модифицировать внутри пользовательских PBO. Для PBO существуют официальный BankRev/listing workflow и форматы addon PBO с `config.cpp/bin` и prefix; `CfgConvert` официально умеет переводить `config.bin` в текст для анализа. citeturn834858search19turn834858search1turn834858search2

P3D можно индексировать по path, LOD metadata и bounding box. Документация формата P3D содержит bounding information, а модельные LOD принципиально важны для производительности; Binarize при сборке WRP требует, чтобы использованные модели были доступны по корректным виртуальным путям и чтобы зависимости моделей/config были разрешены. Поэтому каталог должен проверять не только «файл существует», но и `pbo_prefix`, `CfgPatches`, `requiredAddons`, model path и возможные texture/material dependencies. citeturn834858search9turn834858search24turn594636search5

Предлагаемая запись `asset_catalog.sqlite` должна содержать примерно такие поля:

| Поле | Назначение |
|---|---|
| `asset_id` | стабильный внутренний ID |
| `addon` / `pbo` | источник |
| `virtual_path` | путь, используемый Arma |
| `classname` | CfgVehicles/class при наличии |
| `model_path` | P3D |
| `bbox_x/y/z` | реальный размер |
| `footprint_ratio` | отношение сторон |
| `asset_category` | house/fence/wreck/industrial/etc. |
| `floors_guess` | только если можно определить |
| `lod_summary` | visual/geometry/fire/view/etc. |
| `required_addons` | зависимости |
| `license_status` | known/unknown/restricted |
| `provenance` | источник разрешения |
| `quality_tier` | suitability |
| `allowed_for_zone80` | bool |

Лицензионный статус нельзя выводить из факта, что asset уже лежит в вашем Arma mod folder. Некоторые моды разрешают использование как dependency, но запрещают repack/reupload/edit. Поэтому Zone80 предпочтительно должна **ссылаться на оригинальный мод как dependency**, а не включать его P3D/PAA внутрь своего PBO, пока конкретная лицензия не разрешает обратное. Формат PBO и Binarize используют виртуальные addon paths, поэтому такая dependency-архитектура естественна для Arma. citeturn834858search0turn594636search5

Matcher real-building → P3D должен оценивать минимум `(category, width, length, aspect ratio, floors, industrial/residential, orientation constraints)`. Масштабирование P3D нельзя использовать как универсальное средство «подогнать дом под footprint»: масштаб способен менять визуальную геометрию, но не гарантирует корректность всех игровых свойств и взаимодействий, а масштабирование объектов в Arma имеет собственные ограничения поведения. citeturn834858search49

Для длинных ограждений нужен другой механизм: выбрать модель сегмента, получить её реальную длину из bbox, densify исходную line, поставить сегменты по касательной, подрезать последнюю секцию или скрыть расхождение в воротах/углах. Воротам назначаются отдельные classes. Индустриальные площадки лучше описывать composition templates с anchors, а не случайным набором объектов.

Wrecks должны размещаться semantic rules: парковка, двор жилого дома, обочина, территория предприятия, гаражный массив, checkpoint. Seed должен вычисляться из `world_seed + source_feature_id + rule_version`, а не из порядка перебора объектов. Тогда изменение соседнего сектора не переставит тысячи автомобилей по всему миру.

## Производительность, репозиторий и этапы Go/No-Go

На 32 ГБ RAM production process должен иметь **soft budget примерно 18–20 ГБ Private Bytes**, warning около 20 ГБ и abort/controlled checkpoint около 23–24 ГБ. Это не предел Windows или .NET, а проектный safety margin, оставляющий память системе, Global Mapper, filesystem cache и инструментам Arma. Параллелизм тяжёлых builders на первых тестах следует ограничить до одного; только после профилирования можно разрешать два и более. Факт параллельной генерации в современном GRM подтверждён release notes. citeturn157167view0

Рабочий диск должен использоваться как вторичная память. `Pmad.HugeImages` уже поддерживает memory-mapped huge image storage, а GDAL умеет уводить большие OSM temporary indexes на диск. Поэтому разумная архитектура Zone80 — RAM для текущей партии, SSD для raw source/cache/intermediate/object spool. citeturn623001view1turn824561search0

Для диска я бы не резервировал «точное» число до пилота. Практически проект должен вести статистику `raw/cache/intermediate/build/output` отдельно и экстраполировать её из 10,24-км pilot. Полный мир в 64 раза больше такого сектора по площади, но не все данные масштабируются линейно: satellite raster — почти линейно, здания — по реальной плотности, forests — по vegetation density, а caches могут содержать общие региональные данные.

Рабочая структура:

```text
STALKER_Zone80/
  README.md
  docs/
    MASTER_PLAN.md
    ENVIRONMENT_AUDIT.md
    GRM_AUDIT.md
    GIS_PROVENANCE.md
    ASSET_PROVENANCE.md
    PERFORMANCE.md
    GO_NOGO.md

  config/
    terrain_extent.json
    generation_profile.json
    source_registry.yaml
    object_rules.yaml
    asset_mapping.yaml
    stalker_locations.geojson

  tools/
    audit/
    asset_index/
    gis/
    grm_patch/
    validation/

  data/
    raw/             # immutable
    normalized/      # GeoPackage/COG/etc
    historical/
    cache/
    intermediate/
    overrides/

  assets/
    catalog/         # metadata only, not copied mods

  sectors/
    manifests/

  output/
    terrain/
    objects/
    build/

  logs/
  reports/
```

`data/raw` должен быть неизменяемым; каждая загрузка получает checksum и provenance. `normalized` можно полностью пересоздать. `overrides` содержит только ручные исправления. Крупные данные, пользовательские PBO/P3D и build artifacts не должны попадать в Git. Код, конфиги, manifests, небольшие GeoJSON overrides и отчёты — должны.

Pipeline должен иметь стабильные feature IDs. Например `osm:way:123456`, `ohm:way:...`, `manual:pripyat:block12:bldg07`, `procedural:fence:<source_id>:seg0042`. После преобразования координат source ID не меняется. Это позволит обновить OSM, сравнить diff и не уничтожить ручные правки.

Go/No-Go следует проводить поэтапно:

| Gate | Что доказываем | GO только если |
|---|---|---|
| Asset inventory | наши моды пригодны | найдено достаточно легальных и технически валидных assets |
| Microdistrict 1–2 км | реальный placement | дома совпадают с reference imagery/footprints, matcher контролируем |
| Pilot 10,24 км | весь pipeline | DEM + roads + buildings + surfaces + objects → игровой PBO |
| Adjacent sectors | tile architecture | нет seams, дублей и изменения результатов при повторном запуске |
| Density stress | Arma performance | выбранные tiers дают приемлемый FPS/RAM/loading |
| Full world dry-run | data architecture | manifests всех 64 участков строятся без полной генерации |
| Full WRP | финальная осуществимость | writer/Binarize/Arma принимают весь мир |

Для microdistrict я бы выбрал участок Припяти с многоэтажными домами, дворами, дорогами и хотя бы одной промышленной/общественной зоной. Он гораздо полезнее «случайного леса»: сразу проверяет footprint matching, ориентацию, asset coverage, fences, yards и collision.

Перед каждым gate Cursor должен выдавать `PASS`, `PARTIAL` или `FAIL`; слово PASS запрещено, если реальный PBO не запускался в Arma там, где критерием является игровой запуск. Binarize — официальный инструмент преобразования WRP/P3D в представление для engine, поэтому успешная собственная сериализация WRP ещё не равна рабочей карте. citeturn594636search5

## Роли, аудит и стартовое задание для Cursor

**ChatGPT в этом проекте — режиссёр и аудитор.** Моя функция: проектировать этап, проверять отчёт Cursor, искать противоречия, отсекать необоснованные «готово», задавать следующий ограниченный эксперимент и держать архитектуру/источники/лицензии согласованными. Я не должен считать локальный файл существующим, пока Cursor не покажет путь, размер/hash или содержимое.

**Cursor/«Луна» — локальный инженер.** Его функция: исследовать ПК, писать/изменять код только в проектных копиях, запускать Global Mapper/GRM/GDAL/Arma Tools, собирать показатели, индексировать ваши assets без изменения исходных модов и возвращать доказательства: команды, commit SHA, CSV, логи, paths, screenshots и результаты запуска.

**Вы — владелец и художественный директор.** Вы определяете территорию, разрешаете подключение конкретных модов, решаете, какие исторические эпохи считать каноном, выбираете между «реальной географией» и художественным STALKER-изменением, а также вручную утверждаете важные landmark-модели. Автоматический matcher не должен сам решать, чем заменить ЧАЭС или узнаваемый дом в центре Припяти.

Контрольный аудит каждого этапа должен проверять фактическую ОС и железо; исходный GRM commit/version; hashes inputs; CRS и bbox; source dates/licenses; peak Private Bytes/Working Set; число features до и после фильтрации; число объектов каждого класса; duplicate IDs; objects outside world; missing P3D dependencies; Binarize errors; RPT Arma; screenshots контрольных точек; Git diff. Для объектов с реальной привязкой дополнительно фиксируются horizontal residual и provenance.

Стартовый промпт для Cursor я бы дал именно таким:

```text
PROJECT: STALKER_Zone80
ROLE: Local implementation engineer. ChatGPT is project director/auditor.
STAGE: Foundation audit only. Do not generate the full 80 km world.

OBJECTIVE
Prepare a non-destructive, reproducible foundation for an Arma 3
81.92 x 81.92 km exclusion-zone terrain based on real Chernobyl/
Pripyat/CNPP geography and a local user asset collection.

HARD RULES
1. Do not modify, repack, overwrite or delete any existing user mods.
2. Treat all discovered PBO/P3D/PAA/config assets as read-only.
3. Do not assume Zona.grma3m or any addon exists: locate and report it.
4. Do not run a full GameRealisticMap generation.
5. Do not download huge datasets before reporting expected size/source.
6. Do not declare PASS without evidence.
7. Put all new work in the STALKER_Zone80 project/repository.
8. Use Git branch feat/foundation-audit.
9. Preserve original source files; normalize into separate directories.
10. Every generated output must be reproducible from a script/config.

TASK A — ENVIRONMENT
Determine actual:
- Windows edition/version/build
- CPU/cores
- RAM
- pagefile configuration
- disks/free space/filesystem
- Global Mapper executable/version
- Arma 3, Arma 3 Tools, Terrain Builder, Binarize, CfgConvert
- installed .NET SDK/runtime
- GDAL/ogr2ogr availability
Write reports/ENVIRONMENT_AUDIT.md.

TASK B — DISCOVER EXISTING PROJECT
Search safely for:
- Zona.grma3m
- *.grma3m / *.grma3a
- STALKER_Zone80
- existing ArmaRealMap/GameRealisticMap repositories
- likely local STALKER/addon projects
Report paths, sizes, timestamps.
Do not edit them.

TASK C — GRM SOURCE AUDIT
Clone or reuse a clean copy of:
https://github.com/jetelain/ArmaRealMap

Record branch, tag and exact commit SHA.
Build original source unchanged first.

Inspect:
- BuildContext and builder cache lifetime
- BuildersCatalog / IDataBuilder / GetData
- RawSatelliteImageBuilder
- elevation builders
- OSM acquisition/parsing
- Pmad.HugeImages usage
- Arma3 layer generators
- WRP writer/compiler
- CLI genwrp/gentb/genmod/layer
- concurrency settings

Instrument a SMALL existing/demo generation and collect:
stage,start,end,private_bytes,working_set,managed_heap,
available_system_ram,temp_disk_bytes,object_count.

Do not exceed 24 GiB Private Bytes.
Warn at 20 GiB.

Write:
reports/GRM_AUDIT.md
reports/grm_memory_baseline.csv

Do not patch anything until the measured bottleneck is identified.

TASK D — READ-ONLY ASSET INVENTORY PROTOTYPE
Build an inventory tool that can scan selected addon directories
WITHOUT modifying them.

For each PBO collect:
- filesystem path
- hash
- prefix
- file list
- config.cpp/config.bin presence
- CfgPatches
- requiredAddons

Use official/local Arma tools such as CfgConvert where appropriate.
Do not redistribute extracted content.

For each discoverable P3D collect metadata that can be read safely:
- virtual path
- classname/model relationship
- bounding dimensions if available
- LOD summary if available
- dependency information
- category candidate

Store metadata only in:
assets/catalog/assets.sqlite
assets/catalog/assets.csv

Add license fields:
license_status
license_source
redistribution_allowed
dependency_only
notes

Unknown license MUST remain UNKNOWN, never assumed allowed.

TASK E — GIS FOUNDATION
Create config/terrain_extent.json but DO NOT finalize the CRS
until projection tests are performed.

Test candidate full-world transforms around the intended Zone80 area.
Compare WGS84 -> candidate projected CRS -> local XY -> inverse.
Include control points near west/east/north/south edges.

Investigate whether the selected 81.92 km square crosses the
UTM 35N/36N boundary and quantify coordinate distortion.
Recommend either a single UTM CRS or a local Transverse Mercator
based on measured residuals.

Prepare Global Mapper 27 GMS prototypes for:
- loading a DEM
- setting projection
- clipping exact extent
- exporting GeoTIFF
- exporting Arc ASCII Grid

Do not acquire large imagery yet.

Write:
docs/GIS_PIPELINE.md
gis/test_projection.gms

TASK F — DATA MODEL
Create schemas/config examples for:
- source_registry.yaml
- generation_profile.json
- asset_mapping.yaml
- object_rules.yaml
- stalker_locations.geojson

Every real-world feature must support:
source_id
source_dataset
source_date
license
geometry_confidence
type_confidence
historical_state
manual_override
production_feature_id

Do not generate gameplay locations yet.

TASK G — REPORT
Return:
1. facts discovered
2. unresolved assumptions
3. exact bottlenecks measured
4. files created
5. Git diff
6. recommended first 1–2 km Pripyat micro-pilot
7. explicit GO / PARTIAL / NO-GO for proceeding to that micro-pilot

STOP after the foundation audit.
Do not begin the 10.24 km pilot and do not begin full Zone80 generation.
```

Это намеренно **не просит Cursor сразу строить карту**. Первый настоящий результат нам нужен другой: подтверждённая Windows-конфигурация, точная версия GRM, измеренный источник прежнего расхода RAM, найденный `Zona.grma3m` при его фактическом наличии, безопасный каталог ваших модовых assets и доказанная система координат. Только после этого имеет смысл поручать «Луне» реальный микрорайон Припяти.

Лицензирование исходных геоданных необходимо вести столь же строго. OSM распространяется по ODbL с обязательной атрибуцией; GRM сам требует credits OSM/SRTM/Sentinel; Copernicus DEM имеет собственные требования attribution. Следовательно, `source_registry.yaml` должен в итоге автоматически формировать `CREDITS.md` и текст для описания Steam Workshop/PBO документации. citeturn852068search0turn623001view0turn852068search1

Критический критерий успеха всего проекта я бы сформулировал так: **мы не пытаемся доказать, что 81,92 км можно сгенерировать за один запуск; мы доказываем, что любую часть мира можно детерминированно восстановить из исходных данных, а затем собрать все части в один Arma world без роста RAM пропорционально полной площади**. Если эксперимент с двумя соседними секторами подтвердит это свойство и полный WRP writer выдержит потоковую/дисковую сборку, тогда 32 ГБ перестанут быть принципиальным блокером; до этого утверждать достижимость полной карты было бы преждевременно. citeturn623001view1turn594636search0