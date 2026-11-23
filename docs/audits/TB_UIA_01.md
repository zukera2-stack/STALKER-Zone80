# TB-UIA-01 — инвентаризация Terrain Builder

**PASS для read-only инвентаризации. PARTIAL для пути к импорту. Stage 001 / PARTIAL.** [Issue #21](https://github.com/zukera2-stack/STALKER-Zone80/issues/21). База: `5d8c827e58471cb80a11e7e1eff6d46ac0ffb914`.

DefaultLauncher status подтвердил PID 3856, путь, SHA-256, точное время старта и HWND `0x30F36`. Инспектор запущен из консоли агента дочерним процессом на WinSta0\\Default через CreateProcessW. Terrain Builder 1.32 остался на прежнем PID, окно свёрнуто. 203 узла Raw View, 1223 мс, 0 ошибок чтения свойств patterns, exit 0. Диалог в наблюдении не найден. Записаны Runtime ID, родитель, HWND, PID, свойства элемента и перечисленные провайдером patterns. Runtime ID приведены для этой выборки.

| Операция | Обнаруженный элемент и Runtime ID | Pattern и свойства | Потенциал без ввода |
| --- | --- | --- | --- |
| File | File, 1.200502.10947137.0 | ExpandCollapse, enabled, Collapsed | Кандидат для раскрытия. Подпункты File в выборке отсутствуют. |
| Создать или открыть проект | Create new project / Open project, 42.136576.4.0 / .1 | Invoke, enabled | Кандидаты. Результат вызова и диалог не проверялись. |
| Импорт рельефа | Import terrain..., 42.136570.4.0 | Invoke, enabled | Кандидат для первой отдельной пробы. Типы файлов и диалог ещё не инвентаризированы. |
| Импорт объектов | Import objects..., 42.136570.4.5 | Invoke, disabled | В текущем состоянии путь заблокирован. Поддержка CSV и условия активации не проверены. |
| Импорт фигур | Import shapes..., 42.136570.4.4 | Invoke, disabled | В текущем состоянии путь заблокирован. |
| Переключение слоёв | Rasters / Objects / Shapes, 42.136658.4.0 / .1 / .2 | SelectionItem, ScrollItem, enabled. Rasters selected | Кандидаты для переключения. Objects и Shapes не открывались. |
| Mapframe | Mapframes, 1.200502.10947137.3, Add mapframe, 42.136674.4.2 | ExpandCollapse / Invoke, enabled. Lock/Unlock — Toggle, disabled | Создание mapframe и диалог требуют отдельной проверки. |
| Библиотеки шаблонов | Create new template library / Load template library, 42.136692.4.3 / .4 | Invoke, disabled | TML на этом экране не подтверждён. |
| Состояние | Ready, 42.136598.4.0 | Value, read-only, enabled | Статус доступен для чтения. |

Указанные управляющие элементы были offscreen. Дополнительно найдены меню Edit, View, Objects, Shapes, Keypoints, Roads, Terrain, Tools, SVN, Window, Help, панели импорта, библиотеки и Mapframe. Всего 14 видов patterns, включая Window и Text. LegacyIAccessible не обнаружен через используемый managed UIA API. Скрытые подпункты и содержимое диалогов остаются вне выборки.

Следующий отдельный эксперимент может проверить один разрешённый Invoke над изолированным синтетическим проектом. Для ASC наиболее прямой кандидат — Import terrain. После появления диалога сначала нужно проверить его HWND, владельца, типы файлов и read-only свойства полей. Сквозной путь ASC/CSV/TML пока не подтверждён. Управляющие методы UIA не вызывались, проекты и данные не изменялись.

## Воспроизведение и тесты

[UiaInventory.cs](../../tools/tb_default/UiaInventory.cs) собран Framework 4.x csc.exe с /nologo /warnaserror /platform:x64 и ссылками System.Web.Extensions.dll, WPF/UIAutomationClient.dll, WPF/UIAutomationTypes.dll. Собранный EXE хранится в локальном каталоге отчётов. Режимы: `self-test`, `uia-inventory <PID> <UTC start ticks>`.

Самотест exit 0: JSON round trip, чужой PID и нулевой HWND, повторное использование PID, отображение результатов ожидания. Статическая проверка подтвердила единственный путь создания процесса — диагностический дочерний EXE — и отсутствие API передачи ввода. Границы: 500 узлов, глубина до 10, 9 с мягкий бюджет обхода, 12 с ожидание дочернего процесса. При зависании отдельного UIA-вызова родитель прекращает ожидание. Отдельного жёсткого таймаута на каждый вызов нет. Реальный зависший провайдер не воспроизводился. Чтение прекращается на границах PID и HWND, древовидные ID сохраняются в JSONL-строках журнала. Сырые логи и результаты тестов находятся в `reports/TB-UIA-01/`.

[Microsoft UI Automation Tree Overview](https://learn.microsoft.com/en-us/windows/win32/winauto/uiauto-treeoverview)
