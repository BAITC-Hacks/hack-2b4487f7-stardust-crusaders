# Safe Cleanup Report

Дата: 2026-09-23.

## Итог

Проект после cleanup остаётся рабочим и готовым к локальной демонстрации.
Основная логика recommendation engine, API, Streamlit UI, tests, demo cases и
README сохранены.

## Что удалено

- `app/scoring.py::score_candidate` — неиспользуемый compatibility alias; в
  проекте используется `score_vendor`, внешних вызовов alias не найдено.
- `pandas` из `requirements.txt` — пакет не импортируется в `app/`, `scripts/`,
  `tests/` или `streamlit_app.py`.
- `demo/.gitkeep` — пустой marker стал избыточным, поскольку в `demo/` уже есть
  `demo_cases.json` и `README.md`.

Исходный CSV не изменялся. Тесты и demo cases не удалялись.

## Что оставлено намеренно

- `app/` — все модули составляют pipeline загрузки, фильтрации, scoring,
  explanations, orchestration и API.
- `scripts/audit_dataset.py` — используется для проверки dataset и README.
- `scripts/find_demo_cases.py` — генерирует `demo/demo_cases.json`.
- `tests/` — покрывает loader, filters, scoring, recommender, explanations и
  API.
- `demo/demo_cases.json` и `demo/README.md` — воспроизводимые сценарии защиты.
- `streamlit_app.py` — локальный демонстрационный UI.
- `README.md` — инструкции для установки, запуска и demo.
- `pytest.ini` — задаёт `tests/` как test path и добавляет корень проекта в
  `pythonpath`.
- `AGENT_PROMPTS.md` и `TEAM_TASKS.md` — командные инструкции и acceptance
  criteria, не runtime-код.
- `COMPLIANCE_REVIEW.md` — предыдущий итоговый compliance review.

## Зависимости

Оставлены только используемые runtime/test-зависимости:

- `fastapi` и `uvicorn` — локальный API;
- `pydantic` — input model API;
- `streamlit` — локальный UI;
- `pytest` и `httpx` — тесты;
- стандартный Python `csv` используется для dataset loader.

Удалён неиспользуемый `pandas`. В проекте нет OpenAI, NVIDIA, LangChain,
embeddings, внешних API или секретов.

## Проверка слоёв

- `dataset.py` отвечает за поиск CSV, parsing и создание `Vendor`;
- `filters.py` отвечает за city/category pool и hard filters;
- `scoring.py` отвечает за deterministic scoring;
- `explanations.py` отвечает за evidence и тексты сообщений;
- `recommender.py` координирует pipeline;
- `main.py` отвечает только за FastAPI;
- `streamlit_app.py` вызывает существующий локальный recommender.

## Команды проверки

В текущем Windows-окружении использовался эквивалент `py -3`, потому что
`python` указывает на системный launcher без рабочей установки.

- `py -3 -m pytest -q` — **35 passed**;
- `py -3 -m compileall app scripts tests` — **PASS**;
- `py -3 scripts/audit_dataset.py` — **PASS**, 66 профилей;
- `py -3 scripts/find_demo_cases.py` — **PASS**, найдено 4 demo cases;
- `py -3 -c "from app.main import app; print(app.title)"` — `ToiMatch AI`;
- `git diff --check` — **PASS**.

Dataset audit подтвердил 3 города, 17 категорий, 6 event formats, 3 языка,
среднее 50.56 busy dates на профиль и диапазон 44–58.

## Remaining technical debt

- Нет отдельного browser-level regression test для Streamlit.
- Зависимости не закреплены версиями; воспроизводимость окружения можно
  усилить lock-файлом.
- `AGENT_PROMPTS.md` и `TEAM_TASKS.md` полезны для команды, но не нужны для
  runtime и могут быть вынесены в отдельную документацию после хакатона.
- `pandas` удалён из requirements, потому что фактически не используется;
  если появится pandas-based analytics, зависимость следует вернуть вместе с
  кодом, который её импортирует.

## Status

**READY WITH MINOR TECHNICAL DEBT** — cleanup не меняет business logic, все
обязательные проверки проходят, runtime/API/UI/demo остаются на месте.
