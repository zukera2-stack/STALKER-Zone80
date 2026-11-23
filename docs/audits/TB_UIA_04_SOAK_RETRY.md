# TB-UIA-04 — повторная верификация SOAK-60

**BLOCKED на Gate 1. Stage 001 / PARTIAL.** [Issue #28](https://github.com/zukera2-stack/STALKER-Zone80/issues/28), [#26](https://github.com/zukera2-stack/STALKER-Zone80/issues/26), [#23](https://github.com/zukera2-stack/STALKER-Zone80/issues/23), [#15](https://github.com/zukera2-stack/STALKER-Zone80/issues/15), [PR #27](https://github.com/zukera2-stack/STALKER-Zone80/pull/27). База `83d86ff676536d0056ec17dccea3c104862fcc14`. Фактическая среда Windows 10.0.19045, Python 3.15.2 и .NET Framework csc 4.8.9232.0 для ранее собранных диагностических инструментов.

## Gate 0 — PASS

Рабочая папка не содержит Git checkout. Базу сверили через GitHub и сравнили git hash-object локальных runner и тестов с blob SHA из PR #27. Lifecycle не менялся. Прежние Windows Job smoke и timeout cleanup сверены по локальным журналам. Статический обзор не выявил управляющих вызовов редактора. Завершение процесса предусмотрено только для созданного runner-ом диагностического ребёнка.

38 исходных + 7 lifecycle/selector тестов прошли локально. Повторный разбор исходного Windows журнала выбрал главное окно и сохранил оригинал. В Foundations discovery добавлен адаптер тестов. [GitHub Actions run 45231733506, job 137892770606](https://github.com/zukera2-stack/STALKER-Zone80/actions/runs/45231733506/job/137892770606), HEAD `308c5b6df2dac01d8d425f6775db6a549f69f86f`: в журнале есть все семь имён с `ok`, всего 49 тестов.

## Gate 1 — BLOCKED

23 ноября 2026 г. выполнена одна пара status/inventory. PID 3856, UTC start ticks 639310429255145876, сеанс 1, ожидаемый образ TB и SHA-256 совпали. HWND 0x30F36, свёрнутый безымянный проект, Ready, модального окна в выборке нет. Оба диагностических дочерних процесса подтвердили Default и завершились с кодом 0. PID диагностики 16980 и 31372 отсутствовали при повторной проверке. Terrain Builder исключён из обоих Job. Время команд 1,179 с и 1,327 с соответственно.

| Программа | SHA-256 |
| --- | --- |
| TerrainBuilder.exe | 69470C7FB029C5D63F849FDDB197DCE715ED219F7AE08BEC132472FF333A7AC7 |
| DefaultLauncher.exe | 3C2362510A6936148A761C18CCD0F16039B49B0118B241A5862ADE0BA1F6E65C |
| UiaInventory.exe | 67F03E72A6E5A6044F08189192A5669A36FF195146E876E37099FFCBEEB2758D |

Команды `DefaultLauncher.exe status 3856 639310429255145876` и `UiaInventory.exe uia-inventory 3856 639310429255145876` выполнены под диагностическими Windows Job. Инвентаризация записала 203 узла и одну включённую кнопку Import terrain с Invoke pattern. Исходный валидатор остановил пробу на `unexpected runtime id serialization`: значение `42.136598.4.-1` не соответствовало regex для неотрицательных компонентов.

Исправление разрешает знаковые десятичные компоненты и отклоняет повреждённые строки. 46 локальных тестов прошли после исправления. Replay сохранённого Windows журнала подтвердил 203 узла, тот же HWND, Ready и ровно один подходящий Import terrain. Runtime ID из журнала служит примером формата. Повторную живую проверку после остановки не выполняли.

## Gate 2 — NOT RUN

Условие запуска SOAK не выполнено. **0/120 циклов и 0/12 снимков в SOAK.** Отдельный preflight-снимок в эти числа не входит. Terrain Builder остался открытым и отвечал. GUI-действий, импорта, перезапуска и merge не было. Точные локальные команды, журналы и replay сохранены в `reports/TB-UIA-04/`.
