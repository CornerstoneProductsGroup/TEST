from __future__ import annotations

import pandas as pd
import streamlit as st

from .shared_core import money


def _fmt_delta(cur: float, prev: float, mode: str = "number") -> str:
    delta = float(cur) - float(prev)
    if delta > 0:
        sign = "+"
    elif delta < 0:
        sign = "-"
    else:
        sign = ""

    abs_delta = abs(delta)
    pct = (abs_delta / abs(float(prev)) * 100.0) if float(prev) != 0 else 0.0

    if mode == "money":
        delta_txt = f"{sign}{money(abs_delta)}"
    elif mode == "int":
        delta_txt = f"{sign}{abs_delta:,.0f}"
    else:
        delta_txt = f"{sign}{abs_delta:,.2f}"

    if float(prev) == 0:
        return f"{delta_txt} vs compare"
    return f"{delta_txt} ({pct:,.1f}%) vs compare"


def _render_kpi_card(title: str, value: str, delta: str | None = None):
    delta_html = f"<div class='kpi-delta'>{delta}</div>" if delta else ""
    st.markdown(
        f"""
        <div class="kpi-card">
            <div class="kpi-title">{title}</div>
            <div class="kpi-value">{value}</div>
            {delta_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def _safe_nunique(df: pd.DataFrame, col: str) -> int:
    if col not in df.columns or df.empty:
        return 0
    return int(df[col].dropna().nunique())


def _weekly_rollup(df: pd.DataFrame) -> pd.DataFrame:
    if "WeekEnd" not in df.columns or df.empty:
        return pd.DataFrame(columns=["WeekEnd", "Sales", "Units"])

    wk = (
        df.groupby("WeekEnd", as_index=False)
        .agg(Sales=("Sales", "sum"), Units=("Units", "sum"))
        .sort_values("WeekEnd")
    )
    return wk


def render(ctx: dict):
    dfA = ctx["dfA"]
    dfB = ctx["dfB"]
    compare_mode = ctx.get("compare_mode", "None")

    if dfA.empty:
        st.info("No data available for the selected filters.")
        return

    sales_a = float(dfA["Sales"].sum()) if "Sales" in dfA.columns else 0.0
    sales_b = float(dfB["Sales"].sum()) if "Sales" in dfB.columns else 0.0
    units_a = float(dfA["Units"].sum()) if "Units" in dfA.columns else 0.0
    units_b = float(dfB["Units"].sum()) if "Units" in dfB.columns else 0.0

    asp_a = (sales_a / units_a) if units_a != 0 else 0.0
    asp_b = (sales_b / units_b) if units_b != 0 else 0.0

    wk_a = _weekly_rollup(dfA)
    wk_b = _weekly_rollup(dfB)

    weeks_a = int(wk_a["WeekEnd"].nunique()) if not wk_a.empty else 0
    weeks_b = int(wk_b["WeekEnd"].nunique()) if not wk_b.empty else 0

    avg_week_sales_a = (sales_a / weeks_a) if weeks_a != 0 else 0.0
    avg_week_sales_b = (sales_b / weeks_b) if weeks_b != 0 else 0.0
    avg_week_units_a = (units_a / weeks_a) if weeks_a != 0 else 0.0
    avg_week_units_b = (units_b / weeks_b) if weeks_b != 0 else 0.0

    active_retailers_a = _safe_nunique(dfA, "Retailer")
    active_retailers_b = _safe_nunique(dfB, "Retailer")
    active_vendors_a = _safe_nunique(dfA, "Vendor")
    active_vendors_b = _safe_nunique(dfB, "Vendor")
    active_skus_a = _safe_nunique(dfA, "SKU")
    active_skus_b = _safe_nunique(dfB, "SKU")

    sales_per_retailer_a = (sales_a / active_retailers_a) if active_retailers_a != 0 else 0.0
    sales_per_retailer_b = (sales_b / active_retailers_b) if active_retailers_b != 0 else 0.0
    units_per_retailer_a = (units_a / active_retailers_a) if active_retailers_a != 0 else 0.0
    units_per_retailer_b = (units_b / active_retailers_b) if active_retailers_b != 0 else 0.0

    best_week_txt = "-"
    latest_week_txt = "-"
    if not wk_a.empty:
        best_row = wk_a.sort_values("Sales", ascending=False).iloc[0]
        latest_row = wk_a.sort_values("WeekEnd").iloc[-1]
        best_week_txt = f"{pd.to_datetime(best_row['WeekEnd']).date()} | {money(best_row['Sales'])}"
        latest_week_txt = f"{pd.to_datetime(latest_row['WeekEnd']).date()} | {money(latest_row['Sales'])}"

    with_compare = compare_mode != "None" and not dfB.empty

    st.markdown("### KPI Dashboard")

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        _render_kpi_card(
            "Total Sales",
            money(sales_a),
            _fmt_delta(sales_a, sales_b, "money") if with_compare else None,
        )
    with c2:
        _render_kpi_card(
            "Total Units",
            f"{units_a:,.0f}",
            _fmt_delta(units_a, units_b, "int") if with_compare else None,
        )
    with c3:
        _render_kpi_card(
            "ASP",
            money(asp_a),
            _fmt_delta(asp_a, asp_b, "money") if with_compare else None,
        )
    with c4:
        _render_kpi_card(
            "Weeks in Period",
            f"{weeks_a:,}",
            _fmt_delta(weeks_a, weeks_b, "int") if with_compare else None,
        )

    c5, c6, c7, c8 = st.columns(4)
    with c5:
        _render_kpi_card(
            "Avg Weekly Sales",
            money(avg_week_sales_a),
            _fmt_delta(avg_week_sales_a, avg_week_sales_b, "money") if with_compare else None,
        )
    with c6:
        _render_kpi_card(
            "Avg Weekly Units",
            f"{avg_week_units_a:,.0f}",
            _fmt_delta(avg_week_units_a, avg_week_units_b, "int") if with_compare else None,
        )
    with c7:
        _render_kpi_card(
            "Sales / Active Retailer",
            money(sales_per_retailer_a),
            _fmt_delta(sales_per_retailer_a, sales_per_retailer_b, "money") if with_compare else None,
        )
    with c8:
        _render_kpi_card(
            "Units / Active Retailer",
            f"{units_per_retailer_a:,.0f}",
            _fmt_delta(units_per_retailer_a, units_per_retailer_b, "int") if with_compare else None,
        )

    c9, c10, c11, c12 = st.columns(4)
    with c9:
        _render_kpi_card(
            "Active Retailers",
            f"{active_retailers_a:,}",
            _fmt_delta(active_retailers_a, active_retailers_b, "int") if with_compare else None,
        )
    with c10:
        _render_kpi_card(
            "Active Vendors",
            f"{active_vendors_a:,}",
            _fmt_delta(active_vendors_a, active_vendors_b, "int") if with_compare else None,
        )
    with c11:
        _render_kpi_card(
            "Active SKUs",
            f"{active_skus_a:,}",
            _fmt_delta(active_skus_a, active_skus_b, "int") if with_compare else None,
        )
    with c12:
        _render_kpi_card("Latest Week", latest_week_txt)

    c13, c14 = st.columns(2)
    with c13:
        _render_kpi_card("Best Week", best_week_txt)
    with c14:
        compare_note = "Comparison enabled" if with_compare else "Comparison disabled"
        _render_kpi_card("Compare Status", compare_note)
