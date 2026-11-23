# TB-DEFAULT-01 — автономный запуск Terrain Builder

23 ноября 2026 г. **PASS для автономного запуска и появления окна редактора. Stage 001 / PARTIAL до независимой проверки.**

Проверено техническое решение [Issue #15](https://github.com/zukera2-stack/STALKER-Zone80/issues/15). Архив в рабочей папке не обнаружен, поэтому собран эквивалент. Исходник: [DefaultLauncher.cs](../../tools/tb_default/DefaultLauncher.cs). Старт дочернего процесса выполнен через CreateProcessW, STARTUPINFOW.lpDesktop = WinSta0\\Default, bInheritHandles=false. Применена [документация Microsoft](https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/ns-processthreadsapi-startupinfow).

| Проверка | Результат |
| --- | --- |
| Сборка | PASS, штатный .NET Framework csc.exe 4.8.9232.0, /nologo /warnaserror /platform:x64. |
| Preflight | PASS, процесс агента на отдельном рабочем столе WinSta0, сеанс 1 совпал с активной консолью. OpenInputDesktop вернул Default. OpenDesktopW с DESKTOP_READOBJECTS успешен. |
| Дочерний тест | PASS, PID 24848 самостоятельно записал WinSta0\\Default и завершился с кодом 0. |
| Идентичность TerrainBuilder.exe | PASS, SHA-256 совпал с TB-D3D-02: 69470C7FB029C5D63F849FDDB197DCE715ED219F7AE08BEC132472FF333A7AC7. |
| Экземпляры Terrain Builder перед запуском | PASS, TerrainBuilder и TerrainBuilderNew отсутствовали. |
| Создание процесса | PASS, один CreateProcessW для Terrain Builder, без аргументов, рабочая папка — каталог установки. PID 3856, 18:02:05 мск. |
| Загрузка окна редактора | PASS, на Default зафиксировано видимое окно PID 3856 класса wxWindowClassNR. Заголовок Terrain Builder, затем Terrain Builder - unamedProject. Последний заголовок появился примерно через 2,1 с и оставался до конца наблюдения. TerrainBuilder Error не зарегистрирован в выборке. |
| Мониторинг | 9,5 с, максимум Working Set 62 251 008 байт, Private Bytes 76 378 112 байт. Responding=True. PID 3856 оставлен открытым и отвечал при повторной проверке. Код завершения запускателя 0. |

В первой попытке безвредный дочерний процесс также записал WinSta0\\Default. Повторное открытие уже завершавшегося PID через .NET не позволило подтвердить его код выхода. Запуск Terrain Builder в той попытке не выполнялся. Исправленный запускатель использует исходный HANDLE из CreateProcessW для ожидания дочернего теста и чтения его кода выхода. Отказ Win32 в доступе не зафиксирован.

Исходник SHA-256 B64515ED1382299DE9A86392C74E669B647480CCFB33C20D634BDAA86CBEBEE5. Бинарник SHA-256 10D44054C4E1DFB944C044CC72B69EAC1E863463A647D9B5FBAF3F50E9BCBE4E. Команда запуска: DefaultLauncher.exe run. Локальные доказательства: reports/TB-DEFAULT-01/RUNTIME.log, CHILD.txt, RUNTIME-first.log и CHILD-first.txt.

Функциональность редактора, импорт ASC/CSV/TML и сборка WRP/PBO не проверялись. Переключения рабочего стола, эмуляции ввода, изменений ACL, записи на P: и завершения процессов не было.
