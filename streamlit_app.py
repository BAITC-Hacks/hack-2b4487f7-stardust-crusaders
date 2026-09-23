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
        badges.append("Synthetic")
    if card.city_imputed:
        badges.append("City imputed")
    if card.price_imputed:
        badges.append("Price imputed")
    if badges:
        st.caption(" · ".join(badges))


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
        request_date = first_row[1].date_input("Дата", value=date.today())

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

    st.subheader(f"Статус: `{response.status}`")
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
                    st.write(f"Score: {card.score:.3f}")
                render_badges(card)
                st.write(card.explanation)
    elif response.status == "category_not_found":
        st.info("Измените город или категорию и повторите поиск.")
    else:
        st.info("Попробуйте увеличить бюджет, изменить дату или формат мероприятия.")

    with st.expander("Как сформирована выдача?"):
        st.json(response.debug)


if __name__ == "__main__":
    main()
