# TB-D3D-02 — проба Direct3D 9 x86 на Default

**Stage 001 / PARTIAL. Графическая проба в терминале агента — BLOCKED. Запуск владельцем на Default ожидается.**

Учтено независимое ревью [PR #20](https://github.com/zukera2-stack/STALKER-Zone80/pull/20). В опубликованном исходнике атрибут `SetLastError = true` у `CreateWindowEx` уже присутствовал. Теперь код считывает Win32-ошибку сразу при возврате NULL, до вызова `IsWindow`, и печатает её десятичное и шестнадцатеричное представление. Если проверка HWND вернула false, программа сообщает об этом отдельно. Логика вызовов Direct3D не менялась.

| Проверка | Результат |
| --- | --- |
| Сборка и самотест x86 | PASS, exit 0 |
| Сборка и самотест x64 | PASS, exit 0 |
| Terrain Builder | Обнаружен только PID 31032, сеанс 1, старт 15:15:30 мск. Процессы оставлены без вмешательства. |
| Проба из терминала агента | BLOCKED, exit 2. WinSta0, сеанс 1, активная локальная консоль. Рабочий стол потока отличается от входного Default. |
| Direct3DCreate9, адаптеры, CheckDeviceType, CreateDevice | NOT RUN. Предпусковая проверка завершила процесс до загрузки D3D9. HRESULT отсутствует. |

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

Первичные данные в `reports/TB-D3D-02/`: журналы самотестов x86/x64, `AGENT_PREFLIGHT.log` и `TB_PROCESSES.json`. Terrain Builder не запускался. P:, драйверы, настройки Windows, реестр и оригинальные ресурсы не менялись.
