# GRM-01 — модульный синтетический экспорт

[Issue #13](https://github.com/zukera2-stack/STALKER-Zone80/issues/13). База Zone80 `e57ab9419b07ba5c56fd662af867d189303cae0a`. Upstream GameRealisticMap v0.11.1, тег и HEAD `2aef2040836daa11a8a368bb0c7f9ecd8f405d65`. **Stage 001 / PARTIAL. Синтетический контракт CSV/ASC и сборка двух наборов — PASS.** Проверка импорта в Terrain Builder остаётся открытой.

## Проверки

| Критерий | Статус | Измерение |
| --- | --- | --- |
| Предусловие GIS-04 | PASS | Все четыре офлайн-теста прошли в [CI PR #12](https://github.com/zukera2-stack/STALKER-Zone80/actions/runs/45081246966), HEAD `178f1abcc61c73d5878078003b03c44bbfac9f7b`. |
| Upstream на Windows | PASS (framework-dependent) | Сборка закреплённых исходников без их правок, SDK 11.0.100, target net10.0. Первичная сборка с настройками проекта вернула NU1101 для отсутствующих runtime packs и ILLink. Отключение single-file/self-contained дало 0 ошибок и 43 предупреждения, 10,51 с. Локальные исходники и установленная Studio не менялись. |
| Два независимых сектора | PASS | W и E созданы отдельными командами, затем собраны чтением сохранённых ASC, CSV и JSON. 15 файлов побайтно воспроизвелись по SHA-256 при сравнении с единым запуском. |
| TB CSV и режимы | PASS | Изолированный .NET probe сравнил шесть файлов, включая пустой W relative, со строками штатного `TerrainBuilderObject.ToTerrainBuilderCSV()`. Проверены обе оси, yaw/pitch/roll 35/−7/12, scale 1,25, дробные и отрицательные высоты и раздельные режимы. Режим задаётся файлом. |
| DEM | PASS | Сектора 32×32 по 8 м, общий ASC 64×32. Угол X 200000, Y 0 в TB, общая граница X=200256. Центры соседних ячеек X=200252/200260. Строки идут с севера на юг, центры Y=252…4. Проверены эквивалентный заголовок center и отказ при сдвиге угла на 4 м. На шве 31 пара равных высот и одна пара NoData (−9999), без заполнения пропусков. |
| ID и части на шве | PASS | Четыре размещения, четыре уникальных ID. Точка на шве принадлежит E, внешний восточный/северный край включён. Дубли ID и неверный owner отклоняются. Горизонтальная линия и прямоугольник разбиты на две части каждый, с устойчивым ID в JSON. Это проверка этих двух фигур. |
| TML | PASS (.NET) | Штатный `TmlGenerator` создал `fixture.tml`. Проверены имя шаблона и совпадение символического model path. Реального P3D у фикстуры нет. |
| satmap/idmap | NOT TESTED | Имена `satmap.png` и `idmap.png` и размещение частей сверены статически. Изображения и PAA не создавались. |
| Штатный gentb, Terrain Builder, Cursor | NOT TESTED | Штатный `gentb` вызывает загрузчик OSM и конвертацию изображений. Изолированный минимальный экспорт и .NET probe их не вызывают. Импорт Terrain Builder, совместимость общего прямоугольного ASC как финального Terrain Builder проекта и загрузка моделей не проверены. |
| Офлайн unit/negative | PASS | 5/5 локально под Python 3.15.2 на Windows. Отдельный шаг Foundation CI запускает их без GRM DLL. |

## Координаты и форматы

`localX = tbX − 200000`, `worldX = localX + sectorOffsetX`, `worldY = localY + sectorOffsetY`. При записи объединённого TB CSV `tbWorldX = worldX + 200000`. Смещения секторов W=(0,0), E=(256,0). Контрольные точки мира (32,48), (480,72), (256,80), (512,256). В отдельном тесте смещение по Y +16 преобразует локальный Y=44 в 60. Проектная CRS не выбиралась.

Части геометрии и ID лежат в JSON. Они не являются файлами дорог Terrain Builder. TML создан только в пробе, размещения используют синтетическое имя `FixtureMarker`. Перед реальным импортом нужна проверка модели, высотного режима и обязательных размеров Terrain Builder. [Закреплённый генератор](https://github.com/jetelain/ArmaRealMap/blob/2aef2040836daa11a8a368bb0c7f9ecd8f405d65/GameRealisticMap.Arma3/Arma3TerrainBuilderGenerator.cs) · [Штатный CSV](https://github.com/jetelain/ArmaRealMap/blob/2aef2040836daa11a8a368bb0c7f9ecd8f405d65/GameRealisticMap.Arma3/TerrainBuilder/TerrainBuilderObject.cs)

## Воспроизведение

```powershell
python -m unittest discover -s tools/grm/grm01 -p "test_*.py" -v
python tools/grm/grm01/export.py grm01-example W
python tools/grm/grm01/export.py grm01-example E
python tools/grm/grm01/export.py grm01-example merge

# $upstream points to a local checkout of the pinned GRM commit.
$r = (New-Item -ItemType Directory -Path reports/grm01-build -Force).FullName
$feed = (New-Item -ItemType Directory -Path (Join-Path $r empty-feed) -Force).FullName
dotnet build "$upstream/GameRealisticMap.Arma3.CommandLine/GameRealisticMap.Arma3.CommandLine.csproj" --artifacts-path "$r/framework-dependent" --source $feed -p:NuGetAudit=false -p:PublishSingleFile=false -p:SelfContained=false
$bin = (Get-ChildItem "$r/framework-dependent/bin" -Recurse -Filter grma3.dll | Select-Object -First 1).DirectoryName
dotnet build tools/grm/grm01/probe/ContractProbe.csproj --artifacts-path "$r/probe" --source $feed -p:NuGetAudit=false "-p:GrmBin=$bin"
$dll = (Get-ChildItem "$r/probe/bin" -Recurse -Filter ContractProbe.dll | Select-Object -First 1).FullName
dotnet $dll (Resolve-Path reports/grm01-example).Path
```

Windows, 23 ноября 2026 года. Единый прогон занял 404 мс от запуска процесса, наблюдаемый пик рабочего набора 16 945 152 байта, 33 901 байт выходов до записи метрики. Ресурсы относятся к Python-фикстуре. Протоколы `reports/GRM-01-tests.log`, `reports/GRM-01-build/{build.log,framework-dependent.log,probe-build.log,probe.log}`; выходы `reports/grm01-b36110fcd1/` и `reports/grm01-independent-dc054352/`. SHA-256 манифеста одинаковый: `927c39a7c44c30bd93386dbcc34e2193a7a51da4ab17152e58607125659af63a`.

Адаптер использует только синтетические входы. Сетевые загрузки данных, полная карта, WRP и PBO не запускались.
