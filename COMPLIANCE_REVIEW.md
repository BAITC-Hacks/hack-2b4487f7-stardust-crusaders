# Compliance Review: ToiMatch AI

Дата проверки: 2026-09-23.

## 1. Executive Summary

**Итог: READY WITH MINOR ISSUES.** Проект локально запускается, использует
анонимизированный CSV, не требует внешних API и проходит полный набор из 35
тестов. Реализованы loader, hard filters, deterministic scoring, evidence-based
explanations, три статуса ответа, FastAPI API, Streamlit UI и воспроизводимые
сценарии demo.

Основной остаточный риск — UI проверен запуском Streamlit, но не отдельным
browser-level regression test. Это не блокирует демонстрацию: форма и выдача
проверены статическим review и запуском приложения.

## 2. Таблица соответствия

| Требование | Статус | Где реализовано | Комментарий | Что исправить |
|---|---|---|---|---|
| Загрузка 66 профилей из CSV | PASS | `app/dataset.py`, `tests/test_dataset.py` | `load_vendors()` возвращает 66 профилей и поддерживает fallback CSV | Ничего |
| Поля loader: lists, dates, booleans, `max_hours` | PASS | `app/dataset.py` | Pipe-поля, `set[date]`, пустой float и boolean нормализуются | Ничего |
| Город и категория в pool | PASS | `app/filters.py` | Строгое совпадение города и категории | Ничего |
| Hard filter по занятости | PASS | `app/filters.py` | Дата из `busy_dates` исключает подрядчика | Ничего |
| Hard filter по формату | PASS | `app/filters.py` | `event_type` должен быть в `event_formats` | Ничего |
| Hard filter по бюджету | PASS | `app/filters.py` | Цена не выше бюджета | Ничего |
| Hard filter по длительности | PASS | `app/filters.py` | `max_hours=None` не отбрасывает кандидата | Ничего |
| Язык не является hard filter | PASS | `app/filters.py`, `app/scoring.py` | Язык влияет на score, но несовпадение не исключает профиль | Ничего |
| Площадки обрабатываются как остальные профили | PASS | `app/filters.py`, `app/recommender.py` | Нет отдельного исключающего пути для категорий | Ничего |
| Deterministic scoring | PASS | `app/scoring.py` | Фиксированные веса, без random и внешних сервисов | Ничего |
| Стабильная сортировка и tie-break | PASS | `app/recommender.py` | `total DESC`, `price ASC`, `id ASC` | Ничего |
| Максимум 3 карточки | PASS | `app/recommender.py`, `tests/test_recommender.py` | `results` ограничен первыми тремя | Ничего |
| Пояснение для выдачи меньше 3 | PASS | `app/recommender.py` | Message содержит найденное количество и причины отсечения | Ничего |
| Три исхода recommender | PASS | `app/recommender.py` | `matched`, `category_not_found`, `no_eligible_candidates` | Ничего |
| Понятный empty result | PASS | `app/explanations.py` | `build_empty_result_message()` выводит pool и 4 rejection counts | Ничего |
| Evidence-based explanations | PASS | `app/explanations.py` | Цена, бюджет, формат, язык/длительность и проверяемые поля | Ничего |
| Demo dense/rare/no-result/date | PASS | `scripts/find_demo_cases.py`, `demo/demo_cases.json` | Найдены все 4 сценария и проверены через текущий recommender | Ничего |
| API | PASS | `app/main.py`, `tests/test_api.py` | `/health` и `/recommend`, тот же `recommend()` | Ничего |
| Streamlit UI | PASS | `streamlit_app.py` | Форма, status, message, карточки и debug expander | Добавить browser-level тест при наличии времени |
| README и локальный запуск | PASS | `README.md` | Есть установка, команды API/UI, demo, данные и ограничения | Ничего |
| Отсутствие секретов | PASS | `.gitignore`, весь код | `.env` и ключи не tracked; API внешних сервисов нет | Ничего |

## 3. Результаты команд

Команды выполнялись через `py -3`, потому что в текущем Windows-окружении
команда `python` указывает на launcher без рабочей установки.

- `py -3 -m pytest -q` — **35 passed**;
- `py -3 -m compileall app scripts tests` — **PASS**;
- `py -3 scripts/audit_dataset.py` — **PASS**;
- `py -3 scripts/find_demo_cases.py` — **PASS**, найдено 4 сценария;
- `py -3 -c "from app.main import app; print(app.title)"` — `ToiMatch AI`;
- `py -3 -m streamlit run streamlit_app.py --server.headless true --server.port 8501` — **PASS**, локальный URL `http://localhost:8501`.

Demo finder выполняется примерно за `0.273 s`, что существенно меньше ориентира
в 10 секунд.

## 4. Demo Cases

`demo/demo_cases.json` содержит и повторно подтверждает:

- `dense_category` — `matched`, категория `Ведущий`, 3 top results;
- `rare_category` — `matched`, категория `Флорист`, 2 results;
- `no_result` — `no_eligible_candidates`, категория существует, бюджет ниже
  минимальной цены pool;
- `date_comparison` — оба запроса `matched`, одинаковые параметры кроме даты,
  состав results меняется из-за `busy_dates`.

Отдельная replay-проверка сравнила фактические `status` и `expected_result_ids`
из JSON с текущим `recommend()` — все значения совпали.

## 5. Explanations

`build_evidence()` собирает только данные профиля и запроса:

- цену, бюджет и запас бюджета;
- формат, категорию и языки;
- requested language и факт совпадения;
- длительность и `max_hours`;
- найденные description keywords/snippets;
- `synthetic`, `city_imputed`, `price_imputed`;
- score breakdown.

`build_card_explanation()` формирует 1–2 русских предложения с конкретными
числами и фактами. Запрещённые общие формулировки не используются. Empty-result
message содержит числовые значения pool и всех rejection reasons.

## 6. Deterministic Behavior

Проверено:

- один и тот же запрос повторён 100 раз — порядок ID одинаковый;
- random, timestamps и внешние API в ranking отсутствуют;
- tie-break использует цену и ID;
- date comparison меняет выдачу только при изменении даты и соответствующих
  `busy_dates`.

## 7. README

README описывает назначение проекта, pipeline, архитектуру, технологии,
установку, запуск API и UI, dataset, demo cases, ограничения и локальный режим
без внешних API. Команды `pytest`, audit, demo finder, Uvicorn и Streamlit
приведены явно.

## 8. Секреты и внешние сервисы

Проверено:

- `.env` не tracked и исключён в `.gitignore`;
- `.venv/`, `__pycache__`, `.pytest_cache` и `*.pyc` исключены;
- реальные `OPENAI_API_KEY`, `NVIDIA_API_KEY`, tokens или `.pem/.key` файлы не
  найдены;
- код использует только локальный CSV и Python-библиотеки.

В API-тесте есть только отрицательная проверка отсутствия имён внешних ключей;
значений ключей в проекте нет.

## 9. Оценка для жюри

| Критерий | Баллы | Обоснование |
|---|---:|---|
| Соответствие задаче и работоспособность | 24/25 | Все основные сценарии и 35 тестов проходят |
| Техническая реализация | 24/25 | Модульный локальный pipeline, typed schemas, deterministic ranking |
| README и воспроизводимость | 24/25 | Есть команды запуска, audit и реальные demo cases |
| Ценность и применимость | 13/15 | Практичный подбор с объяснимыми отказами и evidence |
| Потенциал развития и оригинальность | 8/10 | Хорошая база для заявок, уведомлений и расширения ranking |
| **Итого** | **93/100** | Готово к локальной демонстрации |

## 10. Final Action List

### Must fix before submission

- Ничего блокирующего не найдено.

### Should fix if time remains

- Добавить browser-level smoke test для Streamlit формы и отображения карточки.
- Уточнить в CI использование конкретной версии Python вместо системного
  launcher.

### Nice to have

- Добавить отдельный demo runner, который печатает карточки и explanations в
  консоль без UI.
- Добавить визуальное сравнение двух дат из `date_comparison`.
- Разделить optional зависимости UI/API, если проект будет развиваться.

## Итог

Проект **READY WITH MINOR ISSUES** для хакатонной защиты. Все критичные
требования локального recommendation engine, API, UI, explanations, audit и
demo-сценариев выполнены и проверены.
