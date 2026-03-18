from __future__ import annotations

import pandas as pd
import streamlit as st

from .shared_core import money


def _fmt_value(value: float, mode: str) -> str:
    if mode == "money":
        return money(value)
    if mode == "int":
        return f"{value:,.0f}"
    return f"{value:,.2f}"


def _delta_html(value: float, reference: float, mode: str, baseline_name: str) -> str:
    delta = float(value) - float(reference)
    if delta > 0:
        arrow = "▲"
        color = "#2e7d32"
        direction = "up"
    elif delta < 0:
        arrow = "▼"
        color = "#c62828"
        direction = "down"
    else:
        arrow = "•"
        color = "#808080"
        direction = "flat"

    pct = (abs(delta) / abs(float(reference)) * 100.0) if float(reference) != 0 else 0.0
    delta_val = _fmt_value(abs(delta), mode)

    return (
        f"<span style='color:{color};font-weight:800;'>{arrow} {direction} {delta_val} ({pct:,.1f}%)</span>"
        f" <span style='opacity:0.75;'>vs {baseline_name}</span>"
    )


def _render_kpi_card(title: str, value: str, delta_html: str):
    delta_block = f"<div class='kpi-delta'>{delta_html}</div>" if delta_html else ""
    st.markdown(
        f"""
        <div class="kpi-card">
            <div class="kpi-title">{title}</div>
            <div class="kpi-value">{value}</div>
            {delta_block}
        </div>
        """,
        unsafe_allow_html=True,
    )


def _safe_nunique(df: pd.DataFrame, col: str) -> int:
    if col not in df.columns or df.empty:
        return 0
    return int(df[col].dropna().nunique())


def render(ctx: dict):
    dfA = ctx["dfA"]
    dfB = ctx["dfB"]
    a_lbl = ctx.get("a_lbl") or "Current"
    b_lbl = ctx.get("b_lbl") or "Compare"

    if dfA.empty:
        st.info("No data available for the selected filters.")
        return

    sales_a = float(dfA["Sales"].sum()) if "Sales" in dfA.columns else 0.0
    sales_b = float(dfB["Sales"].sum()) if "Sales" in dfB.columns else 0.0
    units_a = float(dfA["Units"].sum()) if "Units" in dfA.columns else 0.0
    units_b = float(dfB["Units"].sum()) if "Units" in dfB.columns else 0.0

    asp_a = (sales_a / units_a) if units_a != 0 else 0.0
    asp_b = (sales_b / units_b) if units_b != 0 else 0.0

    active_retailers_a = _safe_nunique(dfA, "Retailer")
    active_retailers_b = _safe_nunique(dfB, "Retailer")
    active_vendors_a = _safe_nunique(dfA, "Vendor")
    active_vendors_b = _safe_nunique(dfB, "Vendor")
    active_skus_a = _safe_nunique(dfA, "SKU")
    active_skus_b = _safe_nunique(dfB, "SKU")
    st.markdown(
        f"<div style='margin-bottom:8px;opacity:0.8;'>Current: <strong>{a_lbl}</strong> &nbsp; | &nbsp; Compare: <strong>{b_lbl}</strong></div>",
        unsafe_allow_html=True,
    )

    metric_pairs = [
        ("Total Sales", sales_a, sales_b, "money"),
        ("Total Units", units_a, units_b, "int"),
        ("Average Sale Price", asp_a, asp_b, "money"),
        ("Active SKUs", float(active_skus_a), float(active_skus_b), "int"),
        ("Active Retailers", float(active_retailers_a), float(active_retailers_b), "int"),
        ("Active Vendors", float(active_vendors_a), float(active_vendors_b), "int"),
    ]

    for title, current_val, compare_val, mode in metric_pairs:
        c1, c2 = st.columns(2)
        with c1:
            _render_kpi_card(
                f"{title} Current",
                _fmt_value(current_val, mode),
                _delta_html(current_val, compare_val, mode, "compare"),
            )
        with c2:
            _render_kpi_card(
                f"{title} Compare",
                _fmt_value(compare_val, mode),
                _delta_html(compare_val, current_val, mode, "current"),
            )
