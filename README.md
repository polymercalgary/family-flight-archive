# family-flight-archive — опись

Проект «Перелёты»: проверенная история перелётов семьи 2016–2026 (Google Таблицы + PDF на Drive + сайт). Приватный репозиторий. Порядок работы — `CLAUDE.md`.

| путь | что |
|---|---|
| `CLAUDE.md` | инструкция для каждой сессии Claude |
| `STATE.md` | текущая правда (факты, правила R1–R14, текущий шаг) |
| `FUTURE.md` | что ещё сделать, вопросы |
| `HISTORY.md`, `history/` | журнал по месяцам; `2026-09_10-before-git.md` — сводка до репозитория |
| `START-PROMPT.md` | промпты начала и закрытия сессии |
| `docs/LAUNCH-INSTRUCTION.md` | инструкция запуска: куда класть файлы, уборка, порядок проверки |
| `docs/RULES.md` | схема JSON, колонки, имена файлов, исправленные ошибки |
| `app/flights.py` | единая программа (v1.5): добавить перелёт, обновить сайт, проверка |
| `app/1_add_flight.bat`, `app/2_upload_to_site.bat` | запуск `flights.py add` / `flights.py upload` |
| `app/3_tidy_folder.ps1` | разовая уборка папки на ПК: переносит старые файлы в `_archive` (без `-Go` — только список) |
| `app/tests/` | офлайн-тесты (без Google и сервера): `python3 -I app/tests/test_flights.py`, `test_auth.py` |
| `.gitignore` | закрывает ключи, токены, `secrets/`, `HC/`, `_archive/`, отчёты, xlsx/pdf/zip |

Не в Git: ключи и токены (`secrets/`), локальная копия сайта `HC/`, PDF и таблицы (Drive), `flights_state.json`.
Связанные репозитории: `virlab-infra` (серверы, сайт на сервере), `H-C-application`, `leader-machinery-na` — отсюда не меняются.
