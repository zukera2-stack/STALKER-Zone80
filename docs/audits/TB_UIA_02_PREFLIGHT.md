# TB-UIA-02 / SOAK-60 — независимый offline preflight

**Stage 001 / PARTIAL. Реальный 60-минутный Terrain Builder UIA soak: NOT RUN.**

Основание: [GitHub Issue #23](https://github.com/zukera2-stack/STALKER-Zone80/issues/23), комментарий SOAK-60, [PR #22](https://github.com/zukera2-stack/STALKER-Zone80/pull/22) HEAD 77ae76045eec5f022c4d6e01cba995e447823e7a и документ docs/audits/TB_UIA_01.md. Данная работа выполнена в изолированной Linux-среде ChatGPT, **без доступа к работающей Windows**, сеансу WinSta0\Default и процессу PID 3856. Актуальные PID/UTC ticks/HWND/SHA на Windows и первичные Windows-журналы **не проверены здесь**.

## Выполнено независимо

- python -m unittest discover -s tools/validation -p 'test_*.py' -v: **38/38 PASS** в отдельном Linux тестовом пакете; проверены выбор единственного Import terrain, отсутствие Invoke, чужой PID/HWND, модальные ошибки, отсутствие Ready, повреждение JSONL, подмена данных, выход за reports, ASC 64×32, шов, NoData, неправильные координаты и ID, расписание 120/12, отсутствие или неотзывчивость процесса. Обязательно сверить результат GitHub CI на HEAD данной ветки.
- python tools/tb_default/soak60.py offline: **PASS** в независимой среде, синтетический набор секторов записан только внутри reports/TB-UIA-02/. Геометрия воспроизводит опубликованный GRM-01 контракт из [PR #14](https://github.com/zukera2-stack/STALKER-Zone80/pull/14); **не свидетельствует об импорте в Terrain Builder**.
- Вызов python tools/tb_default/soak60.py soak --pid 3856 без обязательных Windows-путей, SHA помощников и UTC ticks: **BLOCKED ожидаемо**; Terrain Builder не запускался.
- Изучение исходника: runner не содержит вызовов InvokePattern.Invoke, SelectionItem.Select, SendKeys/SendInput, WM_COMMAND, изменения P:, ввода или действий GUI. Допускаются только режимы DefaultLauncher.exe status и UiaInventory.exe uia-inventory; режим run не вызывается.

## Подготовленная Windows-runtime верификация — NOT RUN здесь

[soak60.py](../../tools/tb_default/soak60.py) рассчитан на **120 циклов через 30 секунд** и **12 полных UIA-снимков**. Использует монотонные часы и завершает положительный прогон после 3600 секунд. Каждый цикл read-only сверяет PID, UTC start ticks, путь EXE и SHA-256 установленного TerrainBuilder.exe, CPU, Handle Count, отклик, память, HWND, статус Ready и завершённую инициализацию. Каждый десятый цикл сверяет уникальный включённый Import terrain... и доступный InvokePattern, **не вызывая его**.

Диагностические дочерние процессы помещаются в собственный Windows Job Object: CREATE_SUSPENDED → AssignProcessToJobObject → ResumeThread, JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE. При timeout прекращаются только контролируемые диагностические процессы в этом Job. **Terrain Builder не включается в Job**: runner не запускает и не закрывает редактор. Windows ABI, ACL, вложенность Job и фактическое поведение UIA-провайдера пока **NOT RUN**.

### Обязательный Windows Job gate без Terrain Builder

До начала SOAK из терминала Cursor:

~~~powershell
python tools/tb_default/soak60.py job-smoke
~~~

Этот режим создаёт исключительно системный whoami.exe через собственный Windows Job Object, проверяет код завершения и не обращается к Terrain Builder. При ACCESS_DENIED, ошибке вложенного Job или другой ошибке — STOP/BLOCKED, без изменения разрешений Windows и без реального SOAK. На Linux этот режим выдаёт ожидаемый BLOCKED/NOT RUN.

### Команда для локального Cursor на проверенной Windows

Из корня STALKER-Zone80, после сверки **того же** работающего экземпляра TB и локально собранных диагностических EXE:

~~~powershell
python tools/tb_default/soak60.py soak 
~~~

Основные обязательные параметры Windows-прогона: --pid 3856, --start-ticks (из подтверждённого локального журнала), --tb-exe, --launcher-bin, --launcher-sha, --inventory-bin, --inventory-sha. Полную справку выдаёт --help.

**Не подставлять старый PID автоматически:** при закрытии/повторном использовании 3856 остановиться. До реального испытания проверить процесс, момент старта и отсутствие другой работы владельца. Не запускать новый TB ради теста. Исходные бинарники инструментов из локального reports не публиковать в Git.

## Отдельная приёмка

| Проверка | Статус |
| --- | --- |
| Offline код и 38 negative/regression tests | PASS в независимой Linux-среде; GitHub CI — проверить |
| Синтетический ASC 32×32 + 32×32 → 64×32, XShift 200000, NoData/шов | PASS offline |
| Порядок 120/12, уникальные каталоги журналов, hash pinning | PASS на уровне кода/mock |
| Windows Job Object isolation / timeout failure | NOT RUN на Windows |
| Актуальные PID 3856, HWND, SHA, Ready | NOT RUN из этой среды |
| 120 фактических Windows UIA циклов / 12 снимков | NOT RUN |
| 60-минутный read-only SOAK | NOT RUN |
| Реальный GUI Invoke / импорт ASC/CSV/TML / Mapframe | NOT TESTED / запрещён |

Не объявлять memory leak только из-за отличия Working Set; необходимы контекст и повторное доказательство. Если локальная проба остановлена safety guard, указать первый триггер и фактически завершённые циклы, **не** выдавать план 120 циклов за результаты. Сырые журналы только в reports/TB-UIA-02/.

**Дальнейший gate:** испытать Windows Job на безвредном дочернем процессе, затем один SOAK-60 в локальном Cursor. Успех должен быть подтверждён полным cycles.jsonl, SUMMARY.json, SHA и 0 оставшихся диагностических процессов. До реального InvokePattern.Invoke требуется отдельное разрешение владельца согласно Issue #23.

**Никакой merge или Stage 002.**
