"""Minimal Streamlit demo for ToiMatch AI."""

from datetime import date
from pathlib import Path

import streamlit as st

from app.dataset import load_vendors
from app.recommender import recommend
from app.schemas import RecommendationRequest


ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"


def dataset_path() -> Path:
    preferred = DATA_DIR / "hackathon_dataset_anonymized.csv"
    if preferred.exists():
        return preferred
    csv_files = sorted(DATA_DIR.glob("*.csv"))
    if not csv_files:
        raise FileNotFoundError("No CSV dataset found in data/")
    return csv_files[0]


@st.cache_data(show_spinner="Загружаем профили подрядчиков...")
def load_dataset():
    return load_vendors(dataset_path())


def render_badges(card) -> None:
    badges = []
    if card.synthetic:
        badges.append("Синтетический профиль")
    if card.city_imputed:
        badges.append("Город восстановлен")
    if card.price_imputed:
        badges.append("Цена восстановлена")
    if badges:
        st.caption(" · ".join(badges))


def render_debug(response, vendors) -> None:
    debug = response.debug
    st.write(
        "Сначала мы оставляем подрядчиков из выбранных города и категории, "
        "затем проверяем дату, формат, бюджет и длительность. После этого "
        "сравниваем оставшиеся карточки по score и формируем объяснение."
    )

    metrics = st.columns(2)
    metrics[0].metric("Профилей в выбранной категории", debug.get("pool_size", 0))
    metrics[1].metric("Прошли обязательные условия", debug.get("eligible_count", 0))

    request_summary = debug.get("request_summary", {})
    if request_summary:
        st.markdown("**Параметры запроса**")
        st.write(
            f"{request_summary.get('city')} · "
            f"{request_summary.get('category')} · "
            f"{request_summary.get('event_type')} · "
            f"{request_summary.get('date')}"
        )

    rejection_labels = {
        "busy_on_date": "заняты на выбранную дату",
        "unsupported_event_format": "не поддерживают формат мероприятия",
        "over_budget": "выше указанного бюджета",
        "duration_exceeded": "не укладываются в длительность",
    }
    rejection_counts = debug.get("rejection_counts", {})
    rejected = [
        f"{count} — {rejection_labels[reason]}"
        for reason, count in rejection_counts.items()
        if count and reason in rejection_labels
    ]
    if rejected:
        st.markdown("**Почему часть профилей не показана**")
        for item in rejected:
            st.write(f"- {item}")

    names = {vendor.id: vendor.anon_name for vendor in vendors}
    vendors_by_id = {vendor.id: vendor for vendor in vendors}
    ranked_ids = debug.get("ranked_candidate_ids", [])[:3]
    score_breakdowns = debug.get("score_breakdowns", {})
    if ranked_ids:
        st.markdown("**Порядок карточек**")
        for position, vendor_id in enumerate(ranked_ids, start=1):
            breakdown = score_breakdowns.get(vendor_id, {})
            total = breakdown.get("total")
            score_text = "" if total is None else f" · итоговая оценка {total:.0%}"
            st.write(f"{position}. {names.get(vendor_id, vendor_id)}{score_text}")

        score_labels = {
            "budget_fit": "Бюджет",
            "language_fit": "Язык",
            "duration_fit": "Длительность",
            "description_fit": "Описание",
        }
        first_breakdown = score_breakdowns.get(ranked_ids[0], {})
        if first_breakdown:
            st.markdown("**Почему первая карточка получила такую оценку**")
            score_columns = st.columns(4)
            for column, key in zip(score_columns, score_labels):
                value = first_breakdown.get(key)
                column.metric(score_labels[key], "—" if value is None else f"{value:.0%}")

            first_vendor = vendors_by_id.get(ranked_ids[0])
            budget = request_summary.get("budget_kzt")
            price = first_vendor.price_from_kzt if first_vendor else None
            if price is not None and budget is not None:
                st.write(
                    f"**Бюджет — {first_breakdown.get('budget_fit', 0):.0%}.** "
                    f"Цена профиля: {price:,} ₸, ваш бюджет: {budget:,} ₸. "
                    "Оценка ищет разумное соотношение цены и бюджета, поэтому "
                    "самый дешёвый профиль не обязательно получает максимум."
                    .replace(",", " ")
                )

            if request_summary.get("language") is None:
                st.write(
                    f"**Язык — {first_breakdown.get('language_fit', 0):.0%}.** "
                    "Язык не был задан в запросе, поэтому показатель нейтральный "
                    "и не влияет в пользу конкретного профиля."
                )
            else:
                st.write(
                    f"**Язык — {first_breakdown.get('language_fit', 0):.0%}.** "
                    f"Проверено наличие языка «{request_summary['language']}» "
                    "среди языков подрядчика."
                )

            if request_summary.get("duration_hours") is None:
                st.write(
                    f"**Длительность — {first_breakdown.get('duration_fit', 0):.0%}.** "
                    "Длительность не была задана, поэтому показатель нейтральный."
                )
            else:
                max_hours = first_vendor.max_hours if first_vendor else None
                max_label = "без ограничения" if max_hours is None else f"{max_hours} ч"
                st.write(
                    f"**Длительность — {first_breakdown.get('duration_fit', 0):.0%}.** "
                    f"Запрошено {request_summary['duration_hours']} ч, максимум: {max_label}."
                )

            st.write(
                f"**Описание — {first_breakdown.get('description_fit', 0):.0%}.** "
                "Показатель отражает найденные в описании слова, связанные с "
                "форматом события и категорией."
            )


def main() -> None:
    st.set_page_config(page_title="ToiMatch AI", page_icon="🎯", layout="wide")
    vendors = load_dataset()
    cities = sorted({vendor.city for vendor in vendors})
    categories = sorted({category for vendor in vendors for category in vendor.categories})
    event_types = sorted({event for vendor in vendors for event in vendor.event_formats})
    languages = sorted({language for vendor in vendors for language in vendor.languages})

    st.title("ToiMatch AI")
    st.caption("Подбор подрядчиков на основе фильтров, scoring и проверяемых объяснений")

    with st.sidebar:
        st.header("Pipeline")
        st.write("Filter → Score → Evidence → Explain")
        st.caption("Работает локально, без внешних API")
        st.caption(f"Профилей загружено: {len(vendors)}")

    with st.form("recommendation_form"):
        first_row = st.columns(2)
        city = first_row[0].selectbox("Город", cities)
        request_date = first_row[1].date_input(
            "Дата",
            value=date.today(),
            min_value=date.today(),
        )

        second_row = st.columns(2)
        event_type = second_row[0].selectbox("Формат мероприятия", event_types)
        category = second_row[1].selectbox("Категория", categories)

        third_row = st.columns(2)
        budget_kzt = third_row[0].number_input(
            "Бюджет, ₸",
            min_value=1,
            value=200_000,
            step=10_000,
        )
        duration_enabled = third_row[1].checkbox("Указать длительность")
        duration_hours = None
        if duration_enabled:
            duration_hours = st.number_input(
                "Длительность, часов",
                min_value=0.5,
                value=4.0,
                step=0.5,
            )

        language_option = st.selectbox(
            "Язык",
            ["Без предпочтений", *languages],
        )
        language = None if language_option == "Без предпочтений" else language_option
        submitted = st.form_submit_button("Подобрать", type="primary")

    if not submitted:
        return

    request = RecommendationRequest(
        city=city,
        date=request_date,
        event_type=event_type,
        category=category,
        budget_kzt=int(budget_kzt),
        duration_hours=duration_hours,
        language=language,
    )
    response = recommend(vendors, request)

    status_labels = {
        "matched": "Подрядчики найдены",
        "category_not_found": "Категория не найдена в выбранном городе",
        "no_eligible_candidates": "Подходящих подрядчиков не найдено",
    }
    st.subheader(status_labels.get(response.status, response.status))
    st.write(response.message)

    if response.status == "matched":
        if len(response.results) < 3:
            st.info(
                f"Найдено {len(response.results)} из максимум 3 карточек: "
                "остальные кандидаты не прошли hard filters."
            )
        for card in response.results:
            with st.container(border=True):
                st.subheader(card.anon_name)
                st.write(f"Категория: {card.category} · Город: {card.city}")
                st.write(f"Цена от: {card.price_from_kzt:,} ₸".replace(",", " "))
                if card.score is not None:
                    st.write(f"Итоговая оценка: {card.score:.0%}")
                render_badges(card)
                st.markdown(f"**Почему эта карточка показана:** {card.explanation}")
    elif response.status == "category_not_found":
        st.info("Измените город или категорию и повторите поиск.")
    else:
        st.info("Попробуйте увеличить бюджет, изменить дату или формат мероприятия.")

    with st.expander("Как сформирована выдача?"):
        render_debug(response, vendors)


if __name__ == "__main__":
    main()
