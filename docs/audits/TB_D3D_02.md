# TB-D3D-02 — проба Direct3D 9 x86 на Default

**Stage 001 / PARTIAL. Графическая проба в терминале агента — BLOCKED. Проба владельца на Default — PASS для минимального D3D9 x86.**

Учтено независимое ревью [PR #20](https://github.com/zukera2-stack/STALKER-Zone80/pull/20). В опубликованном исходнике атрибут `SetLastError = true` у `CreateWindowEx` уже присутствовал. Теперь код считывает Win32-ошибку сразу при возврате NULL, до вызова `IsWindow`, и печатает её десятичное и шестнадцатеричное представление. Если проверка HWND вернула false, программа сообщает об этом отдельно. Логика вызовов Direct3D не менялась.

| Проверка | Результат |
| --- | --- |
| Сборка и самотест x86 | PASS, exit 0 |
| Сборка и самотест x64 | PASS, exit 0 |
| Terrain Builder | Обнаружен только PID 31032, сеанс 1, старт 15:15:30 мск. Процессы оставлены без вмешательства. |
| Проба из терминала агента | BLOCKED, exit 2. WinSta0, сеанс 1, активная локальная консоль. Рабочий стол потока отличается от входного Default. |
| Проба владельца | PASS, exit 0. Локальный журнал совпал с выводом владельца. Direct3DCreate9 вернул ненулевой указатель. Оконное HAL-устройство создано на обоих перечисленных адаптерах. |

Самотесты проверяют размеры и смещения структур и форматирование HRESULT. Ветвь ошибки Win32 при создании окна в этой среде не выполнялась.

## Однократный запуск владельцем

В обычном PowerShell на активном `WinSta0\Default` перейти в локальный каталог `reports/TB-D3D-02` с подготовленным бинарным файлом и выполнить:

```powershell
if (Test-Path -LiteralPath .\OWNER_X86.log) { throw "Owner probe already recorded" }
New-Item -ItemType File -Path .\OWNER_X86.log -ErrorAction Stop | Out-Null
& .\D3D9Probe-x86.exe 2>&1 | Tee-Object -FilePath .\OWNER_X86.log -Append
$code = $LASTEXITCODE
"exit=$code" | Tee-Object -FilePath .\OWNER_X86.log -Append
```

SHA-256 локальной x86-сборки: `CCE829190588DAB38459EF8ED53B789CA52C0E53567B6A7F782531E1788B5658`.

Успешный `CreateDevice` с ненулевым устройством и exit 0 подтверждает только минимальную оконную HAL-пробу. При отказе фиксируется фактический HRESULT вызванного метода. Код 2 при несовпадении рабочего стола означает BLOCKED.

Первичные данные в `reports/TB-D3D-02/`: журналы самотестов x86/x64, `AGENT_PREFLIGHT.log` `TB_PROCESSES.json` и `OWNER_X86.log`. Terrain Builder не запускался. P:, драйверы, настройки Windows, реестр и оригинальные ресурсы не менялись.


## Фактический вывод x86 на активном Default

```text
bits=32; session=1; consoleSession=1; protocol=0; state=0; station=WinSta0; threadDesktop=Default; inputDesktop=Default; inputError=0
ownHwnd=0xA0FBC
Direct3DCreate9=non-NULL (pointer API, no HRESULT)
GetAdapterCount=2 (count API, no HRESULT)
adapter=0; GetAdapterIdentifier=0x00000000; name=NVIDIA GeForce RTX 3060; driver=nvldumd.dll; vendor=0x10DE; device=0x2504
adapter=0; GetAdapterDisplayMode=0x00000000; format=22
adapter=0; CheckDeviceType(HAL)=0x00000000
adapter=0; CreateDevice(HAL, windowed, software vertex processing)=0x00000000; device=non-NULL
adapter=1; GetAdapterIdentifier=0x00000000; name=NVIDIA GeForce RTX 3060; driver=nvldumd.dll; vendor=0x10DE; device=0x2504
adapter=1; GetAdapterDisplayMode=0x00000000; format=22
adapter=1; CheckDeviceType(HAL)=0x00000000
adapter=1; CreateDevice(HAL, windowed, software vertex processing)=0x00000000; device=non-NULL
exit=0
```

Оба индекса сообщают одинаковый идентификатор GPU. Число 2 относится к записям D3D9, число физических видеокарт этим тестом не установлено. `CheckDeviceType` и `CreateDevice` вернули `0x00000000` для каждого индекса. Минимальный оконный тест прошёл на `WinSta0\Default`. Проба агента остановилась до загрузки D3D9, поэтому сравнить HRESULT между рабочими столами невозможно. Причина ошибки Terrain Builder и работоспособность редактора остаются неподтверждёнными.
