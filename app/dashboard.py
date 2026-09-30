from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st


def format_value(value: Any, fmt: str) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return "—"
    if fmt == "currency":
        return f"R$ {float(value):,.2f}"
    if fmt == "pct":
        return f"{float(value):.2f}%"
    if fmt == "int":
        return f"{int(round(float(value))):,}"
    if fmt == "float":
        return f"{float(value):.2f}"
    return str(value)


def aggregate(df: pd.DataFrame, column: str, agg: str) -> Any:
    if df.empty or column not in df.columns:
        return None
    series = df[column]
    if agg == "sum":
        return series.sum()
    if agg == "mean":
        return series.mean()
    if agg == "median":
        return series.median()
    if agg == "max":
        return series.max()
    if agg == "min":
        return series.min()
    if agg == "count":
        return len(df)
    if agg == "last":
        return series.iloc[-1]
    if agg == "first":
        return series.iloc[0]
    if agg == "p90":
        return series.quantile(0.9)
    return series.iloc[0]


def render_chart(df: pd.DataFrame, chart: dict[str, str] | None) -> None:
    if not chart or df.empty:
        return
    x, y, title = chart["x"], chart["y"], chart["title"]
    if x not in df.columns or y not in df.columns:
        return

    st.markdown(f"**{title}**")
    plot_df = df[[x, y]].copy()
    if chart["type"] == "line":
        plot_df = plot_df.set_index(x)
        st.line_chart(plot_df[y])
    else:
        if len(plot_df) > 15:
            plot_df = plot_df.sort_values(y, ascending=False).head(15)
        plot_df = plot_df.set_index(x)
        st.bar_chart(plot_df[y])


def render_dashboard(question: dict[str, Any], df: pd.DataFrame) -> None:
    st.subheader("Answer")

    metrics = question.get("metrics", [])
    if metrics:
        cols = st.columns(min(len(metrics), 4))
        for idx, metric in enumerate(metrics[:4]):
            val = aggregate(df, metric["column"], metric["agg"])
            cols[idx].metric(metric["label"], format_value(val, metric["format"]))

    st.markdown("---")
    chart_cols = st.columns(2)
    with chart_cols[0]:
        render_chart(df, question.get("chart"))
    with chart_cols[1]:
        render_chart(df, question.get("chart2"))

    st.markdown("**Detailed Results**")
    st.dataframe(df, use_container_width=True, hide_index=True)

    rec = question.get("recommendations", {})
    st.markdown("---")
    st.markdown("**How to use this**")
    r1, r2, r3 = st.columns(3)
    with r1:
        st.markdown("**Product**")
        st.write(rec.get("product", "—"))
    with r2:
        st.markdown("**Finance**")
        st.write(rec.get("finance", "—"))
    with r3:
        st.markdown("**Analyst**")
        st.write(rec.get("analyst", "—"))
