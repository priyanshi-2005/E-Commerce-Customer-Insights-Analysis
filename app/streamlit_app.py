from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

APP_DIR = Path(__file__).resolve().parent
ROOT = APP_DIR.parent
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from dashboard import render_dashboard
from quest_catalog import QUEST_CATEGORIES

DB_PATH = ROOT / "data" / "queryquest.db"
QUESTS_DIR = ROOT / "quests"


def run_sql(relative_path: str) -> tuple[pd.DataFrame, str]:
    sql_path = QUESTS_DIR / relative_path
    sql = sql_path.read_text(encoding="utf-8")
    with sqlite3.connect(DB_PATH) as conn:
        df = pd.read_sql_query(sql, conn)
    return df, sql


def init_state() -> None:
    defaults = {"stage": "quests", "category_id": None, "question_id": None}
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def pick_category(category_id: str) -> None:
    st.session_state.stage = "questions"
    st.session_state.category_id = category_id
    st.session_state.question_id = None


def pick_question(question_id: str) -> None:
    st.session_state.stage = "answer"
    st.session_state.question_id = question_id


def go_back_to_questions() -> None:
    st.session_state.stage = "questions"
    st.session_state.question_id = None


def go_back_to_quests() -> None:
    st.session_state.stage = "quests"
    st.session_state.category_id = None
    st.session_state.question_id = None


def current_category() -> dict | None:
    if not st.session_state.category_id:
        return None
    return next((c for c in QUEST_CATEGORIES if c["id"] == st.session_state.category_id), None)


def current_question(category: dict) -> dict | None:
    if not st.session_state.question_id:
        return None
    return next((q for q in category["questions"] if q["id"] == st.session_state.question_id), None)


def render_quest_grid() -> None:
    st.subheader("Choose a Quest")
    st.caption("Each quest has 15 business questions you can explore.")

    cols = st.columns(2)
    for idx, category in enumerate(QUEST_CATEGORIES):
        with cols[idx % 2]:
            with st.container(border=True):
                st.markdown(f"### {category['icon']} {category['title']}")
                st.caption(category["lens"])
                st.write(category["description"])
                st.markdown(f"**{len(category['questions'])} questions**")
                if st.button("Open Quest", key=f"open_{category['id']}", use_container_width=True):
                    pick_category(category["id"])
                    st.rerun()


def render_question_list(category: dict) -> None:
    if st.button("← Back to Quests"):
        go_back_to_quests()
        st.rerun()

    st.subheader(f"{category['icon']} {category['title']}")
    st.caption(f"{category['lens']} · Pick one of {len(category['questions'])} questions")

    for i, question in enumerate(category["questions"], start=1):
        with st.container(border=True):
            st.markdown(f"**Q{i}.** {question['text']}")
            if st.button("View Answer", key=f"q_{question['id']}", use_container_width=True):
                pick_question(question["id"])
                st.rerun()


def render_answer(category: dict, question: dict) -> None:
    if st.button("← Back to Questions"):
        go_back_to_questions()
        st.rerun()

    st.subheader(question["text"])
    st.caption(f"{category['title']} · {category['lens']}")

    try:
        df, sql = run_sql(question["sql_file"])
    except Exception as exc:
        st.error(f"Query failed: {exc}")
        return

    render_dashboard(question, df)

    st.markdown("---")
    st.subheader("SQL")
    st.caption("Filters, joins, grouping, and comparisons. This is the full calculation behind the chart.")
    st.code(sql, language="sql")


def main() -> None:
    st.set_page_config(page_title="E-commerce Insights Analysis", page_icon="🧭", layout="wide")
    init_state()

    st.title("E-commerce Insights Analysis")
    st.caption("A SQL project on a real online store — about 100,000 orders.")
    st.write(
        "Pick a topic, then a question. You get a short answer, a chart, and the SQL under it. "
        "The questions are the kind a product, finance, or analyst teammate would ask."
    )

    if not DB_PATH.exists():
        st.error("Database not found. Run: `python scripts/load_olist.py`")
        st.stop()

    stage = st.session_state.stage
    category = current_category()

    if stage == "quests" or category is None:
        render_quest_grid()
        return

    if stage == "questions":
        render_question_list(category)
        return

    question = current_question(category)
    if question is None:
        st.session_state.stage = "questions"
        st.rerun()
    render_answer(category, question)


if __name__ == "__main__":
    main()
