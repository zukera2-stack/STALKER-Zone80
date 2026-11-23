# TB-UIA-05 — Windows SOAK-60

**PARTIAL: 50/120 циклов, 5/12 снимков UIA. Stage 001 / PARTIAL.** [Issue #30](https://github.com/zukera2-stack/STALKER-Zone80/issues/30), [PR #29](https://github.com/zukera2-stack/STALKER-Zone80/pull/29), [#28](https://github.com/zukera2-stack/STALKER-Zone80/issues/28), [#26](https://github.com/zukera2-stack/STALKER-Zone80/issues/26), [#23](https://github.com/zukera2-stack/STALKER-Zone80/issues/23), [#15](https://github.com/zukera2-stack/STALKER-Zone80/issues/15).

- **Gate 0 PASS.** HEAD базы 562752de6387287657a5a685ebb2b817e06e6894. Blob SHA локальных runner и тестов совпали с GitHub. Локально 46 тестов OK. [CI job 137894041068](https://github.com/zukera2-stack/STALKER-Zone80/actions/runs/45232093705/job/137894041068) показал 50 тестов. Сохранённые Windows Job smoke и timeout cleanup сверены. Исходники runner не менялись.
- **Gate 1 PASS.** Windows, Python 3.15.2. PID 3856, UTC creation ticks 639310429255145876, образ и SHA проверены. Одно главное окно 0x30F36, свёрнутый безымянный проект, Ready и завершение инициализации, без обнаруженного модального окна. Одна пара помощников на WinSta0/Default: status 1,099 с (PID 28308), inventory 1,505 с (PID 28744), оба exit 0. Приняты 203 узла, один Runtime ID со знаковым компонентом и один включённый Import terrain с InvokePattern. Диагностических процессов после проверки не осталось.
- **Gate 2 PARTIAL.** Один старт 23 ноября 2026 в 21:18:46 мск. 50 последовательных записей в cycles.jsonl, снимки на циклах 10, 20, 30, 40, 50. Последняя запись через 1470,708 с. Для 55 диагностических созданий есть 55 exit 0 и 55 CHILD.log. При последующей проверке процессов runner и диагностических помощников не обнаружено. Terrain Builder PID 3856 отвечал. SUMMARY.json отсутствует. Наблюдение было прервано, а первая попытка прочитать итог вернула ошибку конфигурации песочницы Windows file:///workspace. Причина прекращения записи runner напрямую не зафиксирована. Повтор не выполнялся, GUI действий не было.

| Метрика Terrain Builder | Цикл 1 | Цикл 50 |
| --- | ---: | ---: |
| Working Set, байт | 35016704 | 44728320 |
| Private Bytes, байт | 77602816 | 77398016 |
| Handles | 331 | 334 |
| CPU, 100 нс | 48057343750 | 48110937500 |

Команды короткой пробы: `DefaultLauncher.exe status 3856 639310429255145876` и `UiaInventory.exe uia-inventory 3856 639310429255145876`.

```text
python -u tools/tb_default/soak60.py soak --pid 3856 --start-ticks 639310429255145876 --tb-exe <verified-local-exe> --launcher-bin reports/TB-DEFAULT-02/DefaultLauncher.exe --launcher-sha 3C2362510A6936148A761C18CCD0F16039B49B0118B241A5862ADE0BA1F6E65C --inventory-bin reports/TB-UIA-01/UiaInventory.exe --inventory-sha 67F03E72A6E5A6044F08189192A5669A36FF195146E876E37099FFCBEEB2758D --out reports/TB-UIA-03
```

SHA-256 Terrain Builder: `69470C7FB029C5D63F849FDDB197DCE715ED219F7AE08BEC132472FF333A7AC7`. Runner: `841CDDE22C36CB8C83F56069C0F059E039C30D11B48E91BFE456066A9B467BB7`. cycles.jsonl: `481123F4C26BD98579D7EC88AA498CD94FC35058EB4F22ED7DDFE2163225EB18`.

Сырые доказательства локально в reports/TB-UIA-05 и reports/TB-UIA-03/a70f3c1a5ab440ecb57ebce46a4947f7.
