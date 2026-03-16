from __future__ import annotations

import re

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

from .shared_core import (
    money,
    pct_fmt,
    rename_ab_columns,
    render_df,
    count_sales_card,
    kpi_card,
    selection_total_card,
    top_two_card,
    biggest_increase_card,
)


POSITIVE_BAR = "#2e7d32"
NEGATIVE_BAR = "#c62828"
TOTAL_BAR = "#4e79a7"
NEUTRAL_BAR = "#808080"

PERIOD_RANGE = ["#1f77b4", "#ff7f0e"]

Q_DOMAIN = ["Q1", "Q2", "Q3", "Q4"]
Q_RANGE = ["#dbe7f5", "#a8c4e5", "#6f9fd1", "#2f6fb3"]

BLOCK_VALUE = 10000.0


def render(ctx: dict):
    _inject_css()
    render_standard_view(
        dfA=ctx["dfA"],
        dfB=ctx["dfB"],
        kA=ctx["kA"],
        kB=ctx["kB"],
        a_lbl=ctx["a_lbl"],
        b_lbl=ctx["b_lbl"],
        compare_mode=ctx["compare_mode"],
        min_sales=ctx["min_sales"],
    )


def render_visual_only(ctx: dict):
    _inject_css()
    render_visual_executive_dashboard(
        dfA=ctx["dfA"],
        dfB=ctx["dfB"],
        kA=ctx["kA"],
        kB=ctx["kB"],
        a_lbl=ctx["a_lbl"],
        b_lbl=ctx["b_lbl"],
        min_sales=ctx["min_sales"],
    )


def _inject_css():
    st.markdown(
        """
        <style>
        .kpi-card .kpi-title{font-size:13px !important;}
        .kpi-card .kpi-value{font-size:31px !important;}
        .kpi-card .kpi-delta{font-size:15px !important;}
        .kpi-card .kpi-sub{font-size:15px !important;}
        .kpi-card .top-two-item .kpi-big-name{font-size:22px !important;}
        .kpi-card .top-two-item .kpi-value{font-size:30px !important;}
        .kpi-card .top-two-item .kpi-delta{font-size:14px !important;}
        .kpi-card .top-two-item .kpi-sub{font-size:14px !important;}
        </style>
        """,
        unsafe_allow_html=True,
    )


def _is_year_label(lbl: str) -> bool:
    return bool(re.fullmatch(r"\d{4}", str(lbl or "").strip()))


def _year_compare_mode(a_lbl: str, b_lbl: str) -> bool:
    return _is_year_label(a_lbl) and _is_year_label(b_lbl)


def _pct_change(cur: float, prev: float):
    if prev == 0:
        return np.nan if cur == 0 else np.inf
    return (cur - prev) / prev


def _delta_html(cur: float, prev: float, is_money: bool):
    d = float(cur) - float(prev)
    pc = _pct_change(float(cur), float(prev))
    color = POSITIVE_BAR if d > 0 else (NEGATIVE_BAR if d < 0 else "var(--text-color)")
    arrow = "▲ " if d > 0 else ("▼ " if d < 0 else "")
    abs_s = money(d) if is_money else f"{d:,.0f}"
    return (
        f"<span class='delta-abs' style='color:{color}'>{arrow}{abs_s}</span>"
        f"<span class='delta-pct' style='color:{color}'>({pct_fmt(pc)})</span>"
    )


def _prep_compare_metric(
    df_cur: pd.DataFrame,
    df_cmp: pd.DataFrame,
    level: str,
    metric: str = "Sales",
    top_n: int = 10,
) -> pd.DataFrame:
    cur = df_cur.groupby(level, dropna=False, as_index=False).agg(Current=(metric, "sum"))
    cmp = df_cmp.groupby(level, dropna=False, as_index=False).agg(Compare=(metric, "sum"))
    out = cur.merge(cmp, on=level, how="outer").fillna(0.0)
    out[level] = out[level].astype(str)
    out["Delta"] = out["Current"] - out["Compare"]
    out["Total"] = out["Current"] + out["Compare"]
    return out.sort_values(["Total", level], ascending=[False, True]).head(top_n).copy()


def _prep_quarter_stacked(
    df_cur: pd.DataFrame,
    df_cmp: pd.DataFrame,
    metric: str,
    a_lbl: str,
    b_lbl: str,
) -> pd.DataFrame:
    if "Quarter" not in df_cur.columns or "Quarter" not in df_cmp.columns:
        return pd.DataFrame()

    cur = df_cur.copy()
    cmp = df_cmp.copy()
    cur["Quarter"] = cur["Quarter"].astype(str).str.upper().str.strip()
    cmp["Quarter"] = cmp["Quarter"].astype(str).str.upper().str.strip()

    cur = cur[cur["Quarter"].isin(Q_DOMAIN)]
    cmp = cmp[cmp["Quarter"].isin(Q_DOMAIN)]
    if cur.empty or cmp.empty:
        return pd.DataFrame()

    a = cur.groupby("Quarter", as_index=False)[metric].sum()
    b = cmp.groupby("Quarter", as_index=False)[metric].sum()

    a["Period"] = a_lbl
    b["Period"] = b_lbl
    a.rename(columns={metric: "Value"}, inplace=True)
    b.rename(columns={metric: "Value"}, inplace=True)

    out = pd.concat([a, b], ignore_index=True)
    out["Quarter"] = pd.Categorical(out["Quarter"], categories=Q_DOMAIN, ordered=True)
    out = out.sort_values(["Period", "Quarter"]).copy()

    out["Label"] = out["Value"].map(lambda v: f"{v:,.0f}" if metric == "Units" else money(v))
    out["Start"] = out.groupby("Period")["Value"].cumsum() - out["Value"]
    out["LabelX"] = out["Start"] + (out["Value"] * 0.08)

    total_by_period = out.groupby("Period")["Value"].transform("sum")
    out["ShowLabel"] = np.where(
        (out["Value"] > 0) & (out["Value"] / total_by_period >= 0.08),
        out["Label"],
        "",
    )
    return out


def _stacked_total_chart(
    metric_name: str,
    df_cur: pd.DataFrame,
    df_cmp: pd.DataFrame,
    fallback_cur: float,
    fallback_cmp: float,
    a_lbl: str,
    b_lbl: str,
):
    metric = "Units" if metric_name == "Units" else "Sales"

    stacked = pd.DataFrame()
    if _year_compare_mode(a_lbl, b_lbl):
        stacked = _prep_quarter_stacked(df_cur, df_cmp, metric, a_lbl, b_lbl)

    if stacked.empty:
        chart_df = pd.DataFrame(
            [
                {"Period": a_lbl, "Value": float(fallback_cur)},
                {"Period": b_lbl, "Value": float(fallback_cmp)},
            ]
        )

        xmax = float(chart_df["Value"].max()) if not chart_df.empty else 0.0
        xmax = xmax * 1.20 if xmax > 0 else 1.0

        color_enc = alt.Color(
            "Period:N",
            scale=alt.Scale(domain=[a_lbl, b_lbl], range=PERIOD_RANGE),
            legend=None,
        )

        bars = (
            alt.Chart(chart_df)
            .mark_bar(cornerRadiusTopRight=5, cornerRadiusBottomRight=5)
            .encode(
                y=alt.Y("Period:N", title="", sort=[a_lbl, b_lbl]),
                x=alt.X("Value:Q", title=metric_name, scale=alt.Scale(domain=[0, xmax])),
                color=color_enc,
                tooltip=[
                    alt.Tooltip("Period:N", title="Period"),
                    alt.Tooltip("Value:Q", title=metric_name, format=",.0f" if metric == "Units" else ",.2f"),
                ],
            )
            .properties(height=150)
        )

        labels_df = chart_df.copy()
        labels_df["Label"] = labels_df["Value"].map(lambda v: f"{v:,.0f}" if metric == "Units" else money(v))

        labels = (
            alt.Chart(labels_df)
            .mark_text(dx=8, align="left", fontSize=14, fontWeight="bold")
            .encode(
                y=alt.Y("Period:N", sort=[a_lbl, b_lbl]),
                x=alt.X("Value:Q", scale=alt.Scale(domain=[0, xmax])),
                text="Label:N",
                color=color_enc,
            )
        )
        return bars + labels

    bars = (
        alt.Chart(stacked)
        .mark_bar(cornerRadiusTopRight=5, cornerRadiusBottomRight=5)
        .encode(
            y=alt.Y("Period:N", title="", sort=[a_lbl, b_lbl]),
            x=alt.X("Value:Q", title=metric_name),
            color=alt.Color(
                "Quarter:N",
                scale=alt.Scale(domain=Q_DOMAIN, range=Q_RANGE),
                sort=Q_DOMAIN,
                legend=alt.Legend(orient="top", direction="horizontal", title=""),
            ),
            order=alt.Order("Quarter:N", sort="ascending"),
            tooltip=[
                alt.Tooltip("Period:N", title="Period"),
                alt.Tooltip("Quarter:N", title="Quarter"),
                alt.Tooltip("Value:Q", title=metric_name, format=",.0f" if metric == "Units" else ",.2f"),
            ],
        )
        .properties(height=165)
    )

    labels = (
        alt.Chart(stacked[stacked["ShowLabel"] != ""])
        .mark_text(
            align="left",
            baseline="middle",
            dx=0,
            fontSize=12,
            fontWeight="bold",
            color="#111111",
        )
        .encode(
            y=alt.Y("Period:N", sort=[a_lbl, b_lbl]),
            x=alt.X("LabelX:Q", title=metric_name),
            text="ShowLabel:N",
            detail="Quarter:N",
        )
    )
    return bars + labels


def _prep_grouped_share(df: pd.DataFrame, dim_name: str, a_lbl: str, b_lbl: str) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(
            columns=[dim_name, "Series", "Value", "SharePct", "Label", "SortTotal", "Start", "RowColor"]
        )

    long_df = df[[dim_name, "Current", "Compare", "Total"]].melt(
        id_vars=[dim_name, "Total"],
        value_vars=["Current", "Compare"],
        var_name="Series",
        value_name="Value",
    )

    color_base = df[[dim_name, "Current", "Compare", "Total"]].copy()
    color_base["CurrentColor"] = np.where(
        color_base["Current"] > color_base["Compare"],
        "green",
        np.where(color_base["Current"] < color_base["Compare"], "red", "neutral"),
    )
    color_base["CompareColor"] = np.where(
        color_base["Compare"] > color_base["Current"],
        "green",
        np.where(color_base["Compare"] < color_base["Current"], "red", "neutral"),
    )

    long_df = long_df.merge(
        color_base[[dim_name, "CurrentColor", "CompareColor"]],
        on=dim_name,
        how="left",
    )

    long_df["Series"] = long_df["Series"].replace({"Current": a_lbl, "Compare": b_lbl})
    long_df["RowColor"] = np.where(
        long_df["Series"] == a_lbl,
        long_df["CurrentColor"],
        long_df["CompareColor"],
    )

    long_df["SharePct"] = np.where(long_df["Total"] > 0, long_df["Value"] / long_df["Total"], 0.0)
    long_df["Label"] = long_df.apply(
        lambda r: f'{money(r["Value"])} • {r["SharePct"]:.0%}' if r["Value"] > 0 else "",
        axis=1,
    )
    long_df["SortTotal"] = long_df["Total"]
    long_df["Start"] = 0.0
    return long_df


def _grouped_lollipop_chart(long_df: pd.DataFrame, dim_name: str, a_lbl: str, b_lbl: str, height: int = 560):
    if long_df.empty:
        return None

    xmax = float(long_df["Value"].max()) if not long_df.empty else 0.0
    xmax = xmax * 1.40 if xmax > 0 else 1.0

    color_enc = alt.Color(
        "RowColor:N",
        scale=alt.Scale(
            domain=["green", "red", "neutral"],
            range=[POSITIVE_BAR, NEGATIVE_BAR, NEUTRAL_BAR],
        ),
        legend=None,
    )

    y_enc = alt.Y(
        f"{dim_name}:N",
        sort=alt.SortField(field="SortTotal", order="descending"),
        title="",
        scale=alt.Scale(paddingInner=0.55, paddingOuter=0.22),
    )

    yoff_enc = alt.YOffset(
        "Series:N",
        sort=[a_lbl, b_lbl],
        scale=alt.Scale(paddingInner=0.48),
    )

    rules = (
        alt.Chart(long_df)
        .mark_rule(strokeWidth=2.5)
        .encode(
            y=y_enc,
            yOffset=yoff_enc,
            x=alt.X("Start:Q", scale=alt.Scale(domain=[0, xmax], nice=True), title="Sales"),
            x2="Value:Q",
            color=color_enc,
            tooltip=[
                alt.Tooltip(f"{dim_name}:N", title=dim_name),
                alt.Tooltip("Series:N", title="Series"),
                alt.Tooltip("Value:Q", title="Sales", format=",.2f"),
