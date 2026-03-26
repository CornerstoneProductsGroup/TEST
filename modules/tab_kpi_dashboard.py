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


def _delta_stacked_html(value: float, reference: float, mode: str) -> str:
    """Return two-line HTML: diff value on first line, pct change on second."""
    delta = float(value) - float(reference)
    if delta > 0:
        arrow = "▲"
        color = "#2e7d32"
    elif delta < 0:
        arrow = "▼"
        color = "#c62828"
    else:
        arrow = "•"
        color = "#808080"

    pct = (abs(delta) / abs(float(reference)) * 100.0) if float(reference) != 0 else 0.0
    delta_val = _fmt_value(abs(delta), mode)

    return (
        f"<div style='color:{color};font-weight:800;font-size:13px;line-height:1.3;'>{arrow} {delta_val}</div>"
        f"<div style='color:{color};font-weight:700;font-size:13px;line-height:1.3;'>{pct:,.1f}%</div>"
    )


def _render_entity_kpi_card(
    *,
    title: str,
    sales: float,
    units: float,
    sales_ref: float,
    units_ref: float,
    baseline_name: str,
    align: str = "left",
):
    sales_delta_html = _delta_stacked_html(sales, sales_ref, "money")
    units_delta_html = _delta_stacked_html(units, units_ref, "int")

    card_html = (
        f"<div class='kpi-card kpi-compact-card'>"
        f"<div class='kpi-title'>{title}</div>"
        f"<div style='display:inline-flex;gap:32px;align-items:flex-start;margin-top:6px;'>"
        f"<div><div class='kpi-mini-label'>Sales</div>"
        f"<div class='kpi-mini-value'>{money(sales)}</div>"
        f"<div style='margin-top:4px;'>{sales_delta_html}</div></div>"
        f"<div><div class='kpi-mini-label'>Units</div>"
        f"<div class='kpi-mini-value'>{units:,.0f}</div>"
        f"<div style='margin-top:4px;'>{units_delta_html}</div></div>"
        f"</div></div>"
    )
    if align == "right":
        card_html = f"<div style='display:flex;justify-content:flex-end;'>{card_html}</div>"
    st.markdown(card_html, unsafe_allow_html=True)


def _rollup_by_dim(df: pd.DataFrame, dim: str) -> pd.DataFrame:
    if dim not in df.columns or df.empty:
        return pd.DataFrame(columns=[dim, "Sales", "Units"])

    out = (
        df.groupby(dim, as_index=False)
        .agg(Sales=("Sales", "sum"), Units=("Units", "sum"))
        .sort_values("Sales", ascending=False)
        .reset_index(drop=True)
    )
    return out


def _build_lookup(df_roll: pd.DataFrame, dim: str) -> dict[str, tuple[float, float]]:
    if df_roll.empty:
        return {}
    out: dict[str, tuple[float, float]] = {}
    for _, r in df_roll.iterrows():
        out[str(r[dim])] = (float(r["Sales"]), float(r["Units"]))
    return out



# New header with three centered titles above each card
def _render_split_header(current_label: str, diff_label: str, compare_label: str):
    st.markdown(
        f"""
        <div style='display:flex;justify-content:center;gap:48px;margin-bottom:8px;'>
            <div style='flex:1;text-align:center;'><h3 style='margin:0;font-size:18px;'>{current_label}</h3></div>
            <div style='flex:1;text-align:center;'><h3 style='margin:0;font-size:18px;'>{diff_label}</h3></div>
            <div style='flex:1;text-align:center;'><h3 style='margin:0;font-size:18px;'>{compare_label}</h3></div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_split_cards(
    *,
    left_title: str,
    right_title: str,
    left_sales: float,
    left_units: float,
    right_sales: float,
    right_units: float,
    left_ref_sales: float,
    left_ref_units: float,
    right_ref_sales: float,
    right_ref_units: float,
    left_baseline: str,
    right_baseline: str,
):
    # Centered row of three cards, each with its own title above
    st.markdown(
        "<div style='display:flex;justify-content:center;gap:48px;margin-bottom:0px;'>"
        "<div style='flex:1;max-width:260px;margin:0 8px;'>",
        unsafe_allow_html=True,
    )
    st.markdown(
        f"<div class='kpi-card kpi-compact-card'>"
        f"<div class='kpi-mini-label'>Sales</div>"
        f"<div class='kpi-mini-value'>{money(left_sales)}</div>"
        f"<div class='kpi-mini-label' style='margin-top:8px;'>Units</div>"
        f"<div class='kpi-mini-value'>{left_units:,.0f}</div>"
        f"</div>",
        unsafe_allow_html=True,
    )
    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("<div style='flex:1;max-width:260px;margin:0 8px;'>", unsafe_allow_html=True)
    def diff_html(val_now, val_prev, mode):
        delta = float(val_now) - float(val_prev)
        if delta > 0:
            arrow = "▲"
            color = "#2e7d32"
        elif delta < 0:
            arrow = "▼"
            color = "#c62828"
        else:
            arrow = "•"
            color = "#808080"
        pct = (abs(delta) / abs(float(val_prev)) * 100.0) if float(val_prev) != 0 else 0.0
        if mode == "money":
            val_fmt = money(abs(delta))
        else:
            val_fmt = f"{abs(delta):,.0f}"
        return (
            f"<div style='color:{color};font-weight:800;font-size:18px;line-height:1.3;margin-bottom:2px;'>{arrow} {val_fmt}</div>"
            f"<div style='color:{color};font-weight:700;font-size:15px;line-height:1.3;'>{pct:,.1f}%</div>"
        )
    st.markdown(
        f"<div class='kpi-card kpi-compact-card' style='text-align:center;'>"
        f"<div class='kpi-mini-label'>Sales Diff</div>"
        f"{diff_html(left_sales, right_sales, 'money')}"
        f"<div class='kpi-mini-label' style='margin-top:8px;'>Units Diff</div>"
        f"{diff_html(left_units, right_units, 'int')}"
        f"</div>",
        unsafe_allow_html=True,
    )
    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("<div style='flex:1;max-width:260px;margin:0 8px;'>", unsafe_allow_html=True)
    st.markdown(
        f"<div class='kpi-card kpi-compact-card'>"
        f"<div class='kpi-mini-label'>Sales</div>"
        f"<div class='kpi-mini-value'>{money(right_sales)}</div>"
        f"<div class='kpi-mini-label' style='margin-top:8px;'>Units</div>"
        f"<div class='kpi-mini-value'>{right_units:,.0f}</div>"
        f"</div>",
        unsafe_allow_html=True,
    )
    st.markdown("</div></div>", unsafe_allow_html=True)


def _render_grouped_dim_card(
    *,
    section_label: str,
    dim: str,
    top_roll: pd.DataFrame,
    ref_roll: pd.DataFrame,
    top_n: int,
    align: str = "left",
):
    ref_lookup = _build_lookup(ref_roll, dim)
    top_rows = top_roll.head(top_n)

    rows_html = ""
    for idx, (_, row) in enumerate(top_rows.iterrows(), start=1):
        name = str(row[dim])
        sales = float(row["Sales"])
        units = float(row["Units"])
        ref_sales, ref_units = ref_lookup.get(name, (0.0, 0.0))

        sales_delta = _delta_stacked_html(sales, ref_sales, "money")
        units_delta = _delta_stacked_html(units, ref_units, "int")
        divider = "<div style='border-top:1px solid rgba(128,128,128,0.25);margin:10px 0 8px 0;'></div>" if idx > 1 else ""

        rows_html += (
            f"{divider}"
            f"<div style='margin-bottom:2px;'>"
            f"  <span style='opacity:0.60;font-size:13px;font-weight:700;'>#{idx}</span>"
            f"  <strong style='font-size:16px;margin-left:5px;'>{name}</strong>"
            f"</div>"
            f"<div style='display:inline-flex;gap:32px;align-items:flex-start;'>"
            f"  <div>"
            f"    <div class='kpi-mini-label'>Sales</div>"
            f"    <div class='kpi-mini-value'>{money(sales)}</div>"
            f"    <div style='margin-top:3px;'>{sales_delta}</div>"
            f"  </div>"
            f"  <div>"
            f"    <div class='kpi-mini-label'>Units</div>"
            f"    <div class='kpi-mini-value'>{units:,.0f}</div>"
            f"    <div style='margin-top:3px;'>{units_delta}</div>"
            f"  </div>"
            f"</div>"
        )


    card_html = (
        f"<div class='kpi-card kpi-group-card'>"
        f"<div class='kpi-group-title'>{section_label}</div>"
        f"{rows_html}"
        f"</div>"
    )
    if align == "right":
        card_html = f"<div style='display:flex;justify-content:flex-end;'>{card_html}</div>"
    st.markdown(card_html, unsafe_allow_html=True)

def _render_retailer_vendor_row(
    *,
    retailers_a: pd.DataFrame,
    retailers_b: pd.DataFrame,
    vendors_a: pd.DataFrame,
    vendors_b: pd.DataFrame,
    a_lbl: str,
    b_lbl: str,
):
    c_ret_a, c_vend_a, c_div, c_ret_b, c_vend_b = st.columns([1, 1, 0.04, 1, 1], gap="small")
    with c_ret_a:
        _render_grouped_dim_card(
            section_label=f"Top 3 Vendors — {a_lbl}",
            dim="Vendor",
            top_roll=vendors_a,
            ref_roll=vendors_b,
            top_n=3,
            align="right",
        )
    with c_vend_a:
        _render_grouped_dim_card(
            section_label=f"Top 3 Retailers — {a_lbl}",
            dim="Retailer",
            top_roll=retailers_a,
            ref_roll=retailers_b,
            top_n=3,
            align="right",
        )
    with c_div:
        _render_center_divider(300)
    with c_ret_b:
        _render_grouped_dim_card(
            section_label=f"Top 3 Retailers — {b_lbl}",
            dim="Retailer",
            top_roll=retailers_b,
            ref_roll=retailers_a,
            top_n=3,
        )
    with c_vend_b:
        _render_grouped_dim_card(
            section_label=f"Top 3 Vendors — {b_lbl}",
            dim="Vendor",
            top_roll=vendors_b,
            ref_roll=vendors_a,
            top_n=3,
        )


def _render_dimension_section(
    *,
    section_title: str,
    dim: str,
    top_n: int,
    left_roll: pd.DataFrame,
    right_roll: pd.DataFrame,
    left_label: str,
    right_label: str,
):
    st.markdown(f"### {section_title}")

    left_top = left_roll.head(top_n).copy()
    right_top = right_roll.head(top_n).copy()

    left_lookup = _build_lookup(right_roll, dim)
    right_lookup = _build_lookup(left_roll, dim)

    max_rows = max(len(left_top), len(right_top), top_n)
    for idx in range(max_rows):
        if idx < len(left_top):
            left_row = left_top.iloc[idx]
            left_name = str(left_row[dim])
            left_sales = float(left_row["Sales"])
            left_units = float(left_row["Units"])
        else:
            left_name = "-"
            left_sales = 0.0
            left_units = 0.0

        if idx < len(right_top):
            right_row = right_top.iloc[idx]
            right_name = str(right_row[dim])
            right_sales = float(right_row["Sales"])
            right_units = float(right_row["Units"])
        else:
            right_name = "-"
            right_sales = 0.0
            right_units = 0.0

        left_ref_sales, left_ref_units = left_lookup.get(left_name, (0.0, 0.0))
        right_ref_sales, right_ref_units = right_lookup.get(right_name, (0.0, 0.0))

        _render_split_cards(
            left_title=f"{dim} #{idx + 1}: {left_name}",
            right_title=f"{dim} #{idx + 1}: {right_name}",
            left_sales=left_sales,
            left_units=left_units,
            right_sales=right_sales,
            right_units=right_units,
            left_ref_sales=left_ref_sales,
            left_ref_units=left_ref_units,
            right_ref_sales=right_ref_sales,
            right_ref_units=right_ref_units,
            left_baseline=f"{right_label} match",
            right_baseline=f"{left_label} match",
        )


def render(ctx: dict):
    dfA = ctx["dfA"]
    dfB = ctx["dfB"]
    a_lbl = ctx.get("a_lbl") or "Current"
    b_lbl = ctx.get("b_lbl") or "Compare"

    if dfA.empty:
        st.info("No data available for the selected filters.")
        return

    st.markdown(
        """
        <style>
        .kpi-compact-card{padding:12px 16px !important; border-radius:10px !important; margin-bottom:6px; display:table !important; width:auto !important; min-width:0 !important;}
        .kpi-compact-card .kpi-title{font-size:15px !important; white-space:nowrap;}
        .kpi-mini-label{font-size:13px; font-weight:700; opacity:0.70; text-transform:uppercase; white-space:nowrap;}
        .kpi-mini-value{font-size:28px; font-weight:800; line-height:1.1; white-space:nowrap;}
        .kpi-group-card{padding:12px 16px !important; border-radius:10px !important; margin-bottom:6px; display:inline-block !important; width:auto !important; min-width:0 !important;}
        .kpi-group-title{font-size:13px; font-weight:800; text-transform:uppercase; letter-spacing:0.05em; opacity:0.75; margin-bottom:8px; white-space:nowrap;}
        .kpi-center-line{width:100%;background:rgba(20,20,20,0.82);border-radius:0;}
        </style>
        """,
        unsafe_allow_html=True,
    )

    _render_split_header(a_lbl, "Difference", b_lbl)

    total_sales_a = float(dfA["Sales"].sum()) if "Sales" in dfA.columns else 0.0
    total_units_a = float(dfA["Units"].sum()) if "Units" in dfA.columns else 0.0
    total_sales_b = float(dfB["Sales"].sum()) if "Sales" in dfB.columns else 0.0
    total_units_b = float(dfB["Units"].sum()) if "Units" in dfB.columns else 0.0

    _render_split_cards(
        left_title="Period Total",
        right_title="Period Total",
        left_sales=total_sales_a,
        left_units=total_units_a,
        right_sales=total_sales_b,
        right_units=total_units_b,
        left_ref_sales=total_sales_b,
        left_ref_units=total_units_b,
        right_ref_sales=total_sales_a,
        right_ref_units=total_units_a,
        left_baseline=b_lbl,
        right_baseline=a_lbl,
    )

    retailers_a = _rollup_by_dim(dfA, "Retailer")
    retailers_b = _rollup_by_dim(dfB, "Retailer")
    vendors_a = _rollup_by_dim(dfA, "Vendor")
    vendors_b = _rollup_by_dim(dfB, "Vendor")

    _render_retailer_vendor_row(
        retailers_a=retailers_a,
        retailers_b=retailers_b,
        vendors_a=vendors_a,
        vendors_b=vendors_b,
        a_lbl=a_lbl,
        b_lbl=b_lbl,
    )
