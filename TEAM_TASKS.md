# Командный план на 3 участников

## Участник 1 — Core backend

Ответственность:
- `app/dataset.py`
- `app/schemas.py`
- `app/filters.py`
- `app/scoring.py`
- `app/recommender.py`
- unit tests для hard filters и deterministic ranking

Acceptance criteria:
- занятый подрядчик не попадает в выдачу;
- подрядчик выше бюджета не попадает в выдачу;
- неподходящий формат не попадает в выдачу;
- максимум 3 результата;
- одинаковый запрос возвращает одинаковый порядок.

## Участник 2 — Explanations + QA

Ответственность:
- `app/explanations.py`
- `scripts/audit_dataset.py`
- `scripts/find_demo_cases.py`
- `demo/demo_cases.json`
- edge-case tests

Acceptance criteria:
- каждая карточка имеет объяснение с фактами: бюджет, язык, длительность, description evidence;
- пустой результат объясняется словами;
- demo включает плотную категорию, редкую категорию, no result и сравнение дат.

## Участник 3 — UI + README + сдача

Ответственность:
- `streamlit_app.py`
- `README.md`
- `requirements.txt`
- GitHub cleanup
- финальный demo script

Acceptance criteria:
- проект запускается по README;
- UI показывает три статуса: matched, category_not_found, no_eligible_candidates;
- debug panel показывает pool size, eligible count, reasons;
- README понятен жюри.

## Порядок работы

1. Сначала не трогать UI: проверить `pytest -q`.
2. Запустить `python scripts/audit_dataset.py`.
3. Запустить `python scripts/find_demo_cases.py`.
4. Проверить Streamlit UI.
5. Сделать финальный commit.
6. Отправить GitHub repo через форму хакатона.
