# TB-DEFAULT-02 — автономный мониторинг Terrain Builder

База: c601928d1936dbf4478cfe14452e9da5707c2812. 23 ноября 2026 г. **PASS для read-only мониторинга. Stage 001 / PARTIAL.** Учтено [заключение Issue #15](https://github.com/zukera2-stack/STALKER-Zone80/issues/15).

| Критерий | Статус | Доказательство |
| --- | --- | --- |
| Идентичность PID 3856 | PASS | Имя и путь совпали, время создания 18:02:05.5145876 мск, в пределах 9,2 мс от записи запуска. status сверил точное ожидаемое значение UTC ticks. SHA-256 EXE 69470C7FB029C5D63F849FDDB197DCE715ED219F7AE08BEC132472FF333A7AC7. |
| Наблюдение открытого процесса | PASS | Диагностический дочерний процесс на WinSta0\\Default, существующий редактор оставлен открытым. |
| Win32 | PASS | HWND 0x30F36, wxWindowClassNR, Terrain Builder - unamedProject. Visible=True, Enabled=True, Minimized=True. Диалог ошибки в выборке отсутствовал. Working Set 62 963 712 байт, Private Bytes 76 972 032 байт, Responding=True. |
| UI Automation | PASS | Получено дерево Control View. Видны Rasters, Objects, Shapes, Ready и Application initialization finished. Глубина ограничена 5 уровнями, бюджет 120 узлов на окно. |
| Готовность | PASS для инициализации | PID и Responding показывают существование и отзывчивость процесса. HWND показывает наличие окна. Запись завершения инициализации и Ready подтверждают, что интерфейс дошёл до состояния ожидания. Окно было свёрнуто. Готовность к импорту остаётся непроверенной. |
| Повторяемость | PASS | Два probe и один status завершились кодом 0. Каждый создал отдельный каталог GUID. Журналы открываются через CreateNew и сохраняются. |
| Взаимное исключение | PARTIAL | Именованный mutex охватывает проверку EXE, существующих экземпляров и CreateProcessW. Параллельный run не выполнялся. Внешние программы mutex не используют. |
| Отрицательные сценарии | PASS в самотесте | Реальный запрос отсутствующего PID и отказ в перезаписи журнала. Неверный SHA, другое время старта, чужое имя/путь, наличие экземпляра и недоступный desktop проверены на входных данных защитных функций. Реальный отказ Windows при открытии desktop не воспроизводился. |

[DefaultLauncher.cs](../../tools/tb_default/DefaultLauncher.cs) собран штатным Framework csc.exe с /nologo /warnaserror /platform:x64 и ссылками на WPF/UIAutomationClient.dll и WPF/UIAutomationTypes.dll. Команды из каталога с бинарником в reports: DefaultLauncher.exe self-test, DefaultLauncher.exe probe и DefaultLauncher.exe status <PID> <ожидаемые UTC ticks времени старта>. Отсутствующий PID возвращает 3, неполное наблюдение 4, ошибка или недоступность 2. Код 0 в status учитывает окно и доступность UIA. Содержательные признаки готовности сверены по журналу.

SHA-256 исходника 126BCD8BD996C813B28CC74431D8D1C2AD6F2F04E9E535332022E62F0779F5F9, бинарника 3C2362510A6936148A761C18CCD0F16039B49B0118B241A5862ADE0BA1F6E65C. Исходные журналы, полный путь и дерево сохранены локально в reports/TB-DEFAULT-02/. Ветка run не выполнялась. Импорт, изменения P:, WRP/PBO и merge не выполнялись.

[Microsoft EnumDesktopWindows](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-enumdesktopwindows) · [Microsoft AutomationElement.FromHandle](https://learn.microsoft.com/en-us/dotnet/api/system.windows.automation.automationelement.fromhandle)
