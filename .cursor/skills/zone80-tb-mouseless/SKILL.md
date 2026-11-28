---
name: zone80-tb-mouseless
description: Управление Arma 3 Terrain Builder stable 1.32 и Buldozer из локального Cursor/Codex через PowerShell, Win32 read-only inspection и Windows UI Automation без мыши, клавиатуры или Desktop Commander.
---

# Terrain Builder без мыши — Zone80

**Действующий регламент передачи (28.11.2026):** [AI_WORKSPACE / Google Drive](../../../docs/AI_WORKSPACE.md). ChatGPT ведёт разработку, анализ и доступные тесты, Cursor/Codex исполняет локально через PowerShell и разрешённые нативные API. GitHub — код и задания; Drive — разрешённые архивы и доказательства с уникальным именем, манифестом и SHA256. Library — историческая справка, Desktop Commander не использовать. Локальная sandbox и технические ограничения сохраняются.

## 1. Область применения и приоритет

Применять при работе с Terrain Builder, импортом, экспортом, Save/Reopen, Mapframe и Buldozer. Это узкое дополнение к существующему skill arma3-tools-zone80, не новый конвейер и не новый контракт. Прочитать AGENT_START.md, AGENTS.md, активную Issue #42, ../zone80-luna-autonomous/SKILL.md, ../zone80-map003-gm-tb/SKILL.md и ../arma3-tools-zone80/SKILL.md. Справочник команд: ../arma3-tools-zone80/references/TERRAIN_BUILDER_COMMANDS.md. Приоритет у последнего решения владельца: локальный Cursor/Codex, **не Desktop Commander**, даже если старые инструкции предписывают обратное. Stage001 PARTIAL, текущий допуск TB-RECOVER-02. Не разрешает новые операции сам по себе.

## 2. Канал управления

- Терминал локального Windows Cursor/Codex в интерактивной пользовательской сессии. Сначала подтвердить настоящий Git checkout, ветку, HEAD, доступ к проектному sandbox на запись и текущий допуск.
- PowerShell/.NET UIAutomationClient + UIAutomationTypes; Win32 только для чтения окна, процесса, HWND, иерархии/ID HMENU и проверки состояния. Предпочитать уже проверенные локальные helpers, а не создавать конкурирующие.
- UIA: InvokePattern для кнопок/пунктов, ExpandCollapsePattern для меню, ValuePattern для полей, SelectionItemPattern для выбора, TogglePattern для флагов только при необходимости и с readback. Использовать реально объявленные и доступные паттерны. Не выдумывать AutomationId, PID, HWND или командные номера.
- **Измеренный guard TB-RECOVER-02 (2026-11-28):** `IUIAutomation2::put_AutoSetFocus(FALSE)` вернул `S_OK` с readback `FALSE`, но прямые UIA `Invoke` на собственной безопасной кнопке и `ExpandCollapse.Expand` на собственном ComboBox оба изменили foreground. Это не подтвердило no-focus маршрут. Не считать `AutoSetFocus=FALSE` разрешением раскрывать/вызывать контролы TB в неактивном окне; сначала проверять тот же паттерн на собственном безопасном контроле с неизменным foreground. Замер относится к этим двум контролам; после результата TB-меню не вызывалось.
- Никаких SendKeys, SendInput, mouse_event, keybd_event, pyautogui, координатных кликов, виртуальных клавиш, raw WM_COMMAND, обхода UAC, разблокировки чужой сессии или перехода на другой канал после отмены. Скриншот окна для чтения и доказательств, не средство ввода. Escape/STOP владельца немедленно прекращает управление; до нового явного разрешения не продолжать другими инструментами.
- Stable TB 1.32.0.153956 — подтверждённая версия; не переключаться на Dev. Перед действием сверить фактическую версию. CLI открытия tv4p в этой stable версии ранее проигнорирован; не считать запуск с аргументом открытием. Подтверждённого headless CLI импорта/сохранения нет.

## 3. Read-only preflight и discovery

Пример PowerShell (инвентаризация, не автоматический выбор или запуск):

```powershell
Get-Process TerrainBuilder -ErrorAction SilentlyContinue |
  Select-Object Id, StartTime, Path, MainWindowHandle, MainWindowTitle, Responding
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes
# $ownedHwnd: HWND уже проверенного собственного экземпляра
# не использовать первый найденный процесс и не управлять чужим проектом
$root = [System.Windows.Automation.AutomationElement]::FromHandle([IntPtr]$ownedHwnd)
$root.FindAll([System.Windows.Automation.TreeScope]::Descendants,
  [System.Windows.Automation.Condition]::TrueCondition) |
  ForEach-Object {
    [pscustomobject]@{
      Name = $_.Current.Name
      Id = $_.Current.AutomationId
      Type = $_.Current.ControlType.ProgrammaticName
      Enabled = $_.Current.IsEnabled
      Patterns = ($_.GetSupportedPatterns() | ForEach-Object ProgrammaticName) -join ','
    }
  }
```

Перепроверять PID, время запуска, HWND, заголовок, путь открытого проекта, принадлежность, modal/dirty state после открытия меню и перед каждой мутацией. Если несколько совпадений, элемент устарел, выбран не тот проект, владелец работает в редакторе, есть неожиданный modal или происхождение процесса неизвестно — не действовать. Не закрывать GRMAUTO04 или чужие окна; новый собственный экземпляр через реально появившийся Start New Instance при разрешении. Сверить ресурсы и свободную память. Существующий Save disabled подтверждает только состояние кнопки; чистый проект подтверждать совокупностью признаков.

## 4. Цикл каждой нативной операции

DISCOVER → PRECONDITION → INTENT → INVOKE → READBACK → QC → CHECKPOINT.

1. Найти актуальное меню по семантике и типу, сверить native HMENU hierarchy и фактический ID при нестабильном UIA. Не исполнять ID через WM_COMMAND. ID динамические: прежний Save менялся 2017→2144.
2. Expand, сразу получить свежий popup (лишняя задержка уничтожает временный элемент), выбрать ровно один подходящий Enabled пункт. Принимая UIA Invoke, считать его только попыткой. На toolbar уже наблюдался no-op.
3. Для текстового поля проверить ValuePattern, отсутствие read-only, установить значение, перечитать; для выбора подтвердить IsSelected, для Toggle сверить состояние. Убедиться в правильном владельце диалога, пути и режиме импорта до OK. Не нажимать OK повторно вслепую.
4. После Invoke дождаться наблюдаемого результата в пределах бюджета существующего autonomy skill: диалог/сообщение, изменение count, активный проект, файл или readback. Не использовать неподтверждённый повтор. При таймауте сначала заново прочитать состояние.
5. Изменения только в проектном isolated sandbox, durable intent до мутации, хеши входов/last-good, собственный процесс. Логи и screenshots в локальный evidence bundle для передачи через Google Drive / AI_WORKSPACE/STALKER-Zone80/QA; в GitHub код, отчёт, SHA и краткая сводка, не сырые файлы.

## 5. Проверенные маршруты (история проекта)

| Операция | Штатный маршрут | Независимая проверка |
|---|---|---|
| Открытие проекта | Поддерживаемый native Open Project, точный путь к подготовленной копии | Заголовок/путь, слои, count, контрольные хеши |
| Добавление объектов | File → Import → Objects, реальный picker, Relative(default) для проверенного fixture | Native count 4562→4563; свежий экспорт всех объектов |
| Сохранение | File → Save Project, актуальный semantic Invoke | Файл и sidecars, чистый reopen, свежий export |
| Экспорт объектов | File → Export → Objects, все нужные templates, Document, TB format | Полный независимый parse; ID/anchor, координаты, yaw modulo, pitch/roll, scale, relative Z |
| Экспорт высот | Native XYZ export, фактический выбор XYZ | Для прежнего fixture 4096/4096, max rounding 0.005 m; не выдавать за 1 mm или внутреннюю точность |
| Навигация | Tools → Goto position, Expand/Invoke/Value, readback E/N | Фактический CONN/Pos в Buldozer и screenshot |

Подготовка/копирование native template допускается только ранее проверенным ограниченным способом на pin-совместимой отдельной копии. Не изобретать сериализацию TV4P/TV4L/TV4S/TML. Для Mapframe/импорта растров/shapes пользоваться существующим справочником и измеренными native helpers; названия меню в справочнике не равны доказанному успешному вызову каждой операции. Полный native shape/template QC ещё не подтверждён.

## 6. Buldozer без мыши

Проверенный маршрут TB-P-NATIVE-06: EXE P:\buldozer_x64.exe, cwd и Data Directory P:\, общий P:\buldozer.cfg read-only, отдельное имя/профиль на D:. Аргументы карты:
```text
-buldozer -name=<unique-name> -window -exThreads=0 -disableSteam -noAsserts -cfg=P:\buldozer.cfg -profiles="<owned-D-profile>" -showScriptErrors -noPause
```
Запуск только штатным Connect TB; pipe генерирует TB, не подставлять самостоятельно. Не добавлять -noLand. Подтвердить отсутствие modal, свой viewer PID/parent/pipe/профиль, CONN, реальные координаты и RPT. В Goto position для доказанного synthetic mapframe E=200000+X, N=Z; например E200960/N960 → Pos=(960,109,960). Для TBGEN0002 probe E200240/N240; это не универсальный CRS/offset. Сравнить фактическую камеру и отображение, не считать OK доказательством. Закрывать только собственный viewer штатно; вернуть временные настройки. P: не менять; существующий dta восстановлен ранее по отдельному разрешению, не повторять копирование.

## 7. Recovery и приёмка

Продолжать существующий worker-v02 (prepare_change, verify_change, checkpoint_change, recover_change, resume_gate); не дублировать scheduler/schema/ZPB. До нативной записи подтвердить baseline и durable intent, удерживать существующий lock. После прерывания сначала fresh native readback, dirty/clean и ownership, затем:
- Exact applied: NO_REIMPORT; подтвердить save/reopen/export и checkpoint.
- Exact clean base: один допустимый повтор только в новой тестовой копии и после доказанного отсутствия эффекта.
- Mixed/unknown/dirty uncertain: BLOCKED, сохранить состояние без replay.

Не убивать TB принудительно без отдельного разрешения. Отличать сбой supervisor от crash самого TB. Не трогать accepted v01/v02, GRMAUTO04, TBGEN0001/0002, общий cfg и исходники. При недоступных паттернах проверить существующие проверенные helpers и безопасные native маршруты, не бесконечно сканировать UI; завершить независимые проверки и отчёт. Отсутствие свежего native readback не PASS. Не запускать WRP/PBO, реальные геоданные, P writes, merge, stage promotion или autostart.

## Источники измеренных результатов

- Issue #42 TB-P-NATIVE-06: https://github.com/zukera2-stack/STALKER-Zone80/issues/42#issuecomment-7234714536
- TB-OPEN-02: https://github.com/zukera2-stack/STALKER-Zone80/issues/42#issuecomment-7237840391
- TB-CHANGE-01: https://github.com/zukera2-stack/STALKER-Zone80/issues/42#issuecomment-7238366618
- TB-RECOVER-01: https://github.com/zukera2-stack/STALKER-Zone80/issues/42#issuecomment-7238766930
- Активный TB-RECOVER-02: https://github.com/zukera2-stack/STALKER-Zone80/issues/42#issuecomment-7238916467
- Канал работы (решение владельца): https://github.com/zukera2-stack/STALKER-Zone80/issues/42#issuecomment-7238823748

Статус этого skill: документационное извлечение из измеренных отчётов. Новый Windows/UIA прогон не проводился. Пример PowerShell — read-only шаблон, не готовый проверенный универсальный драйвер.
