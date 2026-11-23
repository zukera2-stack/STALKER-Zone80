# TB-D3D-01 — Direct3D 9 без запуска Terrain Builder

23 ноября 2026 г. **Итог BLOCKED для создания устройства. Stage 001 / PARTIAL.** Предпусковая проверка в обеих архитектурах обнаружила несовпадение рабочего стола процесса с активным пользовательским рабочим столом. Программа завершилась кодом 2 до загрузки D3D9.

| Проверка | Статус | Доказательство |
| --- | --- | --- |
| Предыдущий тестовый процесс | PASS | PID 31032, TerrainBuilder, сеанс 1, запущен в 15:15:30 мск. Заголовок главного окна в выборке пуст. Процесс оставлен без вмешательства. |
| Сеанс Windows | PASS | WTS protocol 0 (локальная консоль), state 0 (Active), сеанс процесса и активной консоли — 1. Агент работал на отдельном рабочем столе в WinSta0. |
| Рабочий стол | BLOCKED | OpenInputDesktop успешно вернул Default. Поток принадлежал отдельному рабочему столу агента, поэтому проба остановилась. |
| NVIDIA | PARTIAL | Предыдущий dxdiag на этом Windows-хосте увидел RTX 3060, драйвер 32.0.16.2101. Перечисление через D3D9 в этой пробе не выполнялось. |
| EXE и библиотеки | PASS | TerrainBuilder.exe 1.32.0.153956, PE32, machine 0x014C (x86), SHA-256 `69470c7fb029c5d63f849fddb197dce715ed219f7ae08bec132472ff333a7ac7`. Прямые импорты включают d3d9.dll и d3dx9_32.dll. Обе найдены в System32 и SysWOW64. Рядом с EXE найдена d3dx9_32.dll 9.16.843.0000, d3d9.dll рядом отсутствует. GDAL DLL найдены рядом с EXE, MSVCP140, MSVCP140_ATOMIC_WAIT и VCRUNTIME140 — в SysWOW64. Проверено наличие файлов. Загрузка транзитивных зависимостей Terrain Builder не проверялась. |
| Автоматические самотесты | PASS | x86 и x64 прошли проверку размеров и смещений нативных структур и форматирования 32-битного HRESULT. |
| Direct3DCreate9, GetAdapterCount | BLOCKED | API не вызывались. Эти функции возвращают указатель и число соответственно. |
| GetAdapterIdentifier, CheckDeviceType, CreateDevice | BLOCKED | Вызовов не было, HRESULT отсутствуют. Код процесса 2 отражает условие остановки программы. |

[Исходник и самотест](../../tools/tb_d3d/D3D9Probe.cs). Проба создаёт собственный HWND без показа окна, перечисляет адаптеры и запрашивает оконное HAL-устройство с программной обработкой вершин. COM-объекты и окно освобождаются в том же потоке. Программа не меняет режим дисплея и не записывает настройки. Проверка исходника и выполненные ветви не выявили операций записи в реестр, смены драйвера или доступа к P:. Terrain Builder и Buldozer не запускались.

Для воспроизведения из корня репозитория на Windows с установленным .NET Framework 4.x:

```powershell
$out = New-Item -ItemType Directory -Force reports/TB-D3D-01
$csc = Join-Path $env:WINDIR 'Microsoft.NET\Framework\v4.0.30319\csc.exe'
foreach ($arch in 'x86', 'x64') {
    $bin = Join-Path $out.FullName "D3D9Probe-$arch.exe"
    & $csc /nologo "/platform:$arch" "/out:$bin" tools/tb_d3d/D3D9Probe.cs
    if ($LASTEXITCODE -ne 0) { throw "Compile failed: $arch" }
    & $bin --self-test
    if ($LASTEXITCODE -ne 0) { throw "Self-test failed: $arch" }
}
& (Join-Path $out.FullName 'D3D9Probe-x86.exe')
$LASTEXITCODE
```

Коды пробы: 0 — получено хотя бы одно HAL-устройство, 2 — предпусковое условие не выполнено, 3 — попытка D3D9 не дала устройства. Следующее измерение требует запуска x86-пробы из терминала на активном Default. Открытие устройства там не установит причину отказа в других условиях.

Первичные данные локально в reports/TB-D3D-01 (x86.log, x64.log, журналы самотестов, PID.json, INVENTORY.json, PE_IMPORTS.json, DEPENDENCIES.json). Сопоставление с [PR #19](https://github.com/zukera2-stack/STALKER-Zone80/pull/19) показывает, что текст ошибки Terrain Builder сам по себе не раскрывает HRESULT. [Документация CreateDevice](https://learn.microsoft.com/en-us/windows/win32/api/d3d9/nf-d3d9-idirect3d9-createdevice).
