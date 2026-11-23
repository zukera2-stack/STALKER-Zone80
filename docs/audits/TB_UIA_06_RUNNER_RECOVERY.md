# TB-UIA-06 — анализ обрыва и устойчивый журнал SOAK

**Stage 001 / PARTIAL. Реальный Windows SOAK-60 после исправлений: NOT RUN.**
Основание: [Issue #32](https://github.com/zukera2-stack/STALKER-Zone80/issues/32), [PR #31](https://github.com/zukera2-stack/STALKER-Zone80/pull/31), отчёт TB_UIA_05_WINDOWS_SOAK.md. Изменения от HEAD d0b9f7935d1ab1804f5bf6bee0ec1195c7fe02d3 в изолированной ветке.

## Причина: доказательства и границы вывода

Из **опубликованного** отчёта PR #31: 50 последовательных записей в cycles.jsonl, 5 UIA снимков (циклы 10,20,30,40,50), последнее elapsedSec=1470.708 (~24 мин 31 с), 55/55 дочерних диагностических процессов exit 0, Terrain Builder после обрыва отвечал. SUMMARY.json отсутствует. Единственное последующее сообщение об окружении — конфигурационная ошибка песочницы file:///workspace. Полные локальные сырые журналы и коды завершения основного Python процесса в этой облачной среде НЕ ПРОВЕРЕНЫ.

**Прямо доказанный дефект протокола:** старый soak60.py создавал SUMMARY.json только в финальном finally. Жёсткая остановка процесса, отключение сеанса или принудительное прекращение контейнера может пропустить finally; тогда причины и итогового статуса не останется.

**Предполагаемая, НЕ доказанная первопричина:** внешнее прекращение основного Python runner или его терминального/агентского окружения примерно через 25 минут. По времени и успешным детям это более правдоподобно, чем падение TB/UIA, но нельзя утверждать наличие фиксированного «лимита Cursor 25 мин» без независимой проверки процесса, его parent/Job и Windows Event Log. Код текущего soak60.py не содержит явного stop на 1500 с — напротив, содержит бюджет ~3630 с. Не исключены потеря доступа к каталогу, отключение сеанса и другие внезапные сбои. Статус причины до форензики: **CAUSE_UNKNOWN**.

## Исправления в коде

- tools/tb_default/soak_evidence.py: stdlib-модуль; уникальный каталог запуска; **SUMMARY.json существует до цикла 1** со статусом RUNNING/PARTIAL; циклы в cycles.jsonl записываются с flush/fsync; после каждого цикла атомарная смена SUMMARY через temporary file + os.replace; EVENTS.jsonl с START, CYCLE_COMMITTED, INVENTORY_COMMITTED, STOP/NORMAL_EXIT, UTC и monotonic. В нормальном завершении PASS только 120/120, 12/12 и >=3600 сек.
- tools/tb_default/soak60.py: интеграция EvidenceSession, read-only recovery CLI и отдельный **lifetime-probe** без Terrain Builder. Никакого UIA Invoke/мыши/SendKeys; Job Object по-прежнему относится только к диагностическим дочерним процессам, не TB. При аварийной остановке Python корректность checkpoint ограничена последним fsynced циклом; сам факт завершения основного процесса при жёстком TerminateProcess внутри него не фиксируется.
- tools/validation/test_tb_soak_evidence.py: автономные тесты на потерю финального SUMMARY, crash между cycle fsync и summary, повреждённую последнюю строку, повтор/пропуск цикла, недостающие снимки, 50/120, восстановление без перезаписи старых файлов, неуспешное атомарное replace, simulated complete и короткий harmless longevity probe. Эти тесты НЕ запускают TB.
- Восстановление формирует новый RECOVERY.json **через FileMode create new («x»)**, не изменяя старые CHILD/PARENT, cycles.jsonl, SUMMARY.json. Если старый summary отсутствует, статус — INTERRUPTED/PARTIAL и CAUSE_UNKNOWN. Сообщение «COMPLETED_RECORDED» формируется только при существующих терминальных событиях/записях и полной непротиворечивой серии; это не свидетельство реально выполненного Windows SOAK без локального происхождения логов.

Атомарная запись и fsync защищают от ряда прерываний процесса, но **не дают абсолютной гарантии сохранности при потере питания или неисправности диска**. Журналы сохраняются в локальном reports/, публичные абсолютные пути не публиковать.

## Предварительная офлайн-проверка

**Проверено независимо на GitHub Actions:** [Foundation validation run #45268502768](https://github.com/zukera2-stack/STALKER-Zone80/actions/runs/45268502768), job #138021727343, HEAD `46da5a44dfd4085b337486b6962d8af3768426b1`: фактический журнал показывает `Ran 75 tests in 0.845s … OK`. Включены 25 новых `test_tb_soak_evidence`, 38 исходных SOAK, 7 lifecycle, 1 signed runtime ID и 4 прочих foundation. В частности `test_historical_50_5_missing_terminal`, `test_simulated_crash_between_cycle_and_checkpoint`, `test_short_synthetic_lifetime_probe` прошли. Успех CI подтверждает только переносимую логику checkpoints/recovery, **не поведение Windows Job, реального Cursor lifecycle или Terrain Builder**.

## Что поручено локальной Луне — без SOAK Terrain Builder

1. Сначала read-only исследовать оригинальную папку reports/TB-UIA-03/a70f3c1a5ab440ecb57ebce46a4947f7, сверить опубликованный SHA cycles.jsonl 481123F4C26BD98579D7EC88AA498CD94FC35058EB4F22ED7DDFE2163225EB18. Оригиналы не менять. Собрать достоверные metadata основного Python процесса из Cursor terminal/Windows Application/System logs за время обрыва без сбора посторонних личных данных. Отсутствие evidence => CAUSE_UNKNOWN.
2. После локального код-review/commit SHA применить новый read-only recovery:

   python tools/tb_default/soak60.py recover --run-dir reports/TB-UIA-03/a70f3c1a5ab440ecb57ebce46a4947f7

   Проверить RECOVERY.json: cycles=50, inventories=5, статус INTERRUPTED/PARTIAL, cause CAUSE_UNKNOWN при отсутствии доказательства. Сравнить SHA старых файлов до/после. Команда пишет **только** новый RECOVERY.json, не повторяет SOAK.
3. Запустить короткий sanity-test чисто синтетического режима:

   python tools/tb_default/soak60.py lifetime-probe --out reports/TB-UIA-06 --probe-seconds 3 --probe-period 0.25

   Этот режим создаёт только тестовые локальные JSONL; не ищет и не запускает Terrain Builder.
4. Затем **одна** синтетическая проба жизненного цикла длительностью **27 минут** (пересекает прежние ~24.5 мин), в той же консоли Cursor и с теми же условиями создания процесса, без фонового daemon/task/scheduler:

   python -u tools/tb_default/soak60.py lifetime-probe --out reports/TB-UIA-06 --probe-seconds 1620 --probe-period 30

   По появлению/исчезновению процесса, checkpoint, событиям и данным Windows различить: нормально дошёл до 27 мин / остановился примерно там же / остановился иначе. **Не утверждать фиксированный лимит, если доказаны лишь часы и отсутствие процесса.**
5. Проверить отсутствие осиротевших собственных диагностических детей, приложить санитизированные логи/exit codes, сделать отдельный отчёт с PASS/PARTIAL/BLOCKED. **Не выполнять ещё один часовой SOAK до отдельного допуска.**

## Приёмка

- **PASS offline** — достоверное раннее сохранение SUMMARY, fsynced cycles, атомарные checkpoints и корректная реконструкция неполных логов проходят тесты.
- **PASS Windows lifetime diagnostic** — результат 27-минутной *синтетической* пробы и коды завершения подтверждены реальными Windows журналами. Это НЕ PASS SOAK.
- **PARTIAL/BLOCKED** — Windows тесты ещё не выполнены; TB-UIA-05 остаётся 50/120 и 5/12.
- **NOT TESTED** — GUI Invoke, импорт ASC/CSV/TML, WRP/PBO, реальный повтор SOAK.

**Ограничения:** не запускать/закрывать TB или менять его окна, не использовать мышь/SendKeys/WM_COMMAND/UIA Invoke, не менять P:, Windows ACL, реестр, службы/автозапуск, не запускать Binarize/Arma, не объединять PR и не переходить к Stage 002.


## Локальная Windows-проверка

**A PASS (восстановление), причина CAUSE_UNKNOWN. B PASS (25 локальных тестов и CI). C PASS (синтетическая проба). D NOT RUN (SOAK Terrain Builder). Stage 001 / PARTIAL.**

Исходники закреплены на `c047cf8aceb61e3af0a744744c7ecb9e6ffc446c`. Локальные Git blob SHA: runner `3591c56f7bfdf628b4966693baa1bc0cb5fac7af`, evidence `056a89c83d9a350453dd716b9750c4b602f6c4da`, тесты `1a2e59c23e966f1fecdd84938753ac6492355a81`. Проверен [CI job 138022289953](https://github.com/zukera2-stack/STALKER-Zone80/actions/runs/45268664092/job/138022289953) на закреплённом HEAD: 75 тестов. На Windows прошли 25 тестов evidence, `python -m unittest discover -s tools/validation -p test_tb_soak_evidence.py -v` из изолированной копии исходников.

### Восстановление предыдущего прогона

50 последовательных JSONL записей, снимки 10/20/30/40/50, единая идентичность Terrain Builder и status exit 0 во всех циклах. Все 55 диагностических запусков сопоставлены с 55 exit 0 по PID и времени создания. Сохранились 55 пар PARENT/CHILD. Последняя запись через 1470,708 с. Код завершения основного Python и терминальная запись отсутствуют.

| Измерение | p50, мс | p95, мс | max, мс |
| --- | ---: | ---: | ---: |
| Status | 850,015 | 975,82 | 1008,75 |
| Снимок, включая status | 1761,24 | 2799,81 | 2799,81 |

От первого до последнего цикла: Working Set +9 711 616 байт, Private Bytes −204 800 байт, handles +3, CPU +5,359375 с. Ошибок в валидных циклах не выявлено.

Вызов `recover_run` из закреплённой локальной копии записал единственный новый RECOVERY.json. Исходный SHA-256 cycles.jsonl совпал с PR #31: `481123F4C26BD98579D7EC88AA498CD94FC35058EB4F22ED7DDFE2163225EB18`. Все 113 исходных файлов до и после имеют одинаковые SHA-256. RECOVERY SHA-256 `C15FB8D5549651C7CEE69DD76E1C58E53F8C85E3DD80ECA061844AD79241BE3A`.

За интервал 21:41–21:47 мск 23 ноября релевантных Application/System событий и подходящих WER ReportArchive/ReportQueue не найдено. Нет доказанного exit code, события краша или внешнего завершения. Ошибка file:///workspace зарегистрирована при последующем чтении. Причина обрыва остаётся **CAUSE_UNKNOWN**.

### Синтетический Windows lifecycle

Из консоли агента выполнены команды `python -u tools/tb_default/soak60.py lifetime-probe --probe-seconds 3 --probe-period .25` и `python -u tools/tb_default/soak60.py lifetime-probe --probe-seconds 1620 --probe-period 30` из закреплённой копии. Путь вывода по умолчанию находится внутри выделенного reports/TB-UIA-06. Отдельная инъекция KeyboardInterrupt во время ожидания сохранила 1 цикл и статус PARTIAL/BLOCKED. Реальная доставка Ctrl+C через терминал в этом сценарии не проверялась.

Длинная проба началась 24 ноября в 00:29:21 мск, PID 30744, сеанс 1. Read-only Toolhelp и IsProcessInJob подтвердили цепочку Python → PowerShell → Codex command runner → Codex, все в Windows Job. Конфигурация лимитов Job недоступна из этих наблюдений. Проба завершилась штатно за **1620,112 с**, **55 синтетических записей и 5 маркеров**, PROBE_COMPLETE, терминальное событие STOP и фактический exit 0. Собственные Python и PowerShell PID после завершения отсутствовали. SHA-256 синтетического cycles.jsonl `90C16B907FC4F69AC3239E5FB1F60BC420C0C0954F71273E41769672B533F496`. В этой пробе обрыв на прежней отметке не воспроизвёлся. Результат не устанавливает причину старого обрыва и не подтверждает 60-минутный лимит среды.

Локальные журналы в reports/TB-UIA-06. Terrain Builder не использовался, новый SOAK-60 не выполнялся. Merge не выполнялся.
