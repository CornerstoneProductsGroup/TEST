def render_visual_only(ctx: dict):
    dfA = ctx["dfA"]
    dfB = ctx["dfB"]
    kA = ctx["kA"]
    kB = ctx["kB"]
    a_lbl = ctx["a_lbl"]
    b_lbl = ctx["b_lbl"]
    compare_mode = ctx["compare_mode"]
    driver_level = ctx["driver_level"]

    st.subheader("Standard Intelligence • Visual Analytics")

    if compare_mode == "None":
        st.info("Select a comparison mode to use Standard Intelligence visual analytics.")
        return

    POSITIVE_BAR = "#2e7d32"
    NEGATIVE_BAR = "#c62828"
    NEUTRAL_BAR = "#808080"

    def _totals_df(metric: str) -> pd.DataFrame:
        cur = float(kA.get(metric, 0.0))
        cmpv = float(kB.get(metric, 0.0))

        if cur > cmpv:
            cur_color = POSITIVE_BAR
            cmp_color = NEGATIVE_BAR
        elif cur < cmpv:
            cur_color = NEGATIVE_BAR
            cmp_color = POSITIVE_BAR
        else:
            cur_color = NEUTRAL_BAR
            cmp_color = NEUTRAL_BAR

        label_fmt = money if metric == "Sales" else (lambda x: f"{x:,.0f}")
        out = pd.DataFrame(
            [
                {"Period": a_lbl, "Value": cur, "Label": label_fmt(cur), "Color": cur_color},
                {"Period": b_lbl, "Value": cmpv, "Label": label_fmt(cmpv), "Color": cmp_color},
            ]
        )
        out["MidX"] = out["Value"] / 2.0
        return out

    def _contributors_df(level: str) -> pd.DataFrame:
        drv = drivers(dfA, dfB, level)
        if drv is None or drv.empty:
            return pd.DataFrame()

        out = drv.copy()
        out[level] = out[level].astype(str)
        out["Label"] = out["Sales_Δ"].map(money)
        return out

    def _sku_increase_decline_df() -> pd.DataFrame:
        a = dfA.groupby("SKU", as_index=False).agg(Current=("Sales", "sum"))
        b = dfB.groupby("SKU", as_index=False).agg(Compare=("Sales", "sum"))
        out = a.merge(b, on="SKU", how="outer").fillna(0.0)
        out["Sales_Δ"] = out["Current"] - out["Compare"]
        out["Label"] = out["Sales_Δ"].map(money)
        return out

    def _top2_compare_df(dim: str) -> pd.DataFrame:
        cur = dfA.groupby(dim, as_index=False).agg(Current=("Sales", "sum"))
        cmpv = dfB.groupby(dim, as_index=False).agg(Compare=("Sales", "sum"))
        out = cur.merge(cmpv, on=dim, how="outer").fillna(0.0)
        out["Total"] = out["Current"] + out["Compare"]
        out = out.sort_values(["Total", dim], ascending=[False, True]).head(2).copy()
        out["Entity"] = out[dim].astype(str)
        return out

    def _base_axis_kwargs():
        # Let Streamlit / Vega theme control label colors so they adapt
        # to dark vs light mode automatically.
        return {
            "labelFontSize": 15,
            "titleFontSize": 16,
        }

    def _label_kwargs(font_size: int = 14, color: str = "#222222"):
        return {
            "fontSize": font_size,
            "fontWeight": "normal",
            "color": color,
        }

    def _render_total_bars(df: pd.DataFrame, title: str, x_title: str):
        if df.empty:
            st.info("No total data available.")
            return

        xmax = float(df["Value"].max()) if not df.empty else 0.0
        xmax = xmax * 1.08 if xmax > 0 else 1.0

        # Make sure the two rows are clearly separate
        y_scale = alt.Scale(paddingInner=0.55, paddingOuter=0.35)

        bars = (
            alt.Chart(df)
            .mark_bar(cornerRadiusTopRight=6, cornerRadiusBottomRight=6, size=24)
            .encode(
                y=alt.Y(
                    "Period:N",
                    title="",
                    sort=df["Period"].tolist(),
                    scale=y_scale,
                    axis=alt.Axis(**_base_axis_kwargs()),
                ),
                x=alt.X(
                    "Value:Q",
                    title=x_title,
                    scale=alt.Scale(domain=[0, xmax]),
                    axis=alt.Axis(**_base_axis_kwargs()),
                ),
                color=alt.Color("Color:N", scale=None, legend=None),
                tooltip=[
                    alt.Tooltip("Period:N", title="Period"),
                    alt.Tooltip("Value:Q", title=x_title, format=",.2f" if x_title == "Sales" else ",.0f"),
                ],
            )
            .properties(height=135, title=title)
        )

        # Text is smaller and centered in each bar
        text = (
            alt.Chart(df)
            .mark_text(align="center", baseline="middle", **_label_kwargs(font_size=13, color="#111111"))
            .encode(
                y=alt.Y("Period:N", sort=df["Period"].tolist(), scale=y_scale),
                x=alt.X("MidX:Q", scale=alt.Scale(domain=[0, xmax])),
                text="Label:N",
            )
        )

        st.altair_chart(bars + text, use_container_width=True)

    def _render_positive_lollipop_list(
        df: pd.DataFrame,
        y_col: str,
        value_col: str,
        title: str,
    ):
        if df.empty:
            st.info(f"No data available for {title.lower()}.")
            return

        xmax = float(df[value_col].max()) if not df.empty else 0.0
        xmax = xmax * 1.15 if xmax > 0 else 1.0
        df = df.copy()
        df["Zero"] = 0.0

        rules = (
            alt.Chart(df)
            .mark_rule(strokeWidth=2.5, color=POSITIVE_BAR)
            .encode(
                y=alt.Y(
                    f"{y_col}:N",
                    sort=None,
                    title="",
                    axis=alt.Axis(labelLimit=320, **_base_axis_kwargs()),
                ),
                x=alt.X(
                    "Zero:Q",
                    scale=alt.Scale(domain=[0, xmax]),
                    title="Sales Change",
                    axis=alt.Axis(**_base_axis_kwargs()),
                ),
                x2=f"{value_col}:Q",
            )
        )

        dots = (
            alt.Chart(df)
            .mark_circle(size=150, color=POSITIVE_BAR)
            .encode(
                y=alt.Y(
                    f"{y_col}:N",
                    sort=None,
                    title="",
                    axis=alt.Axis(labelLimit=320, **_base_axis_kwargs()),
                ),
                x=alt.X(
                    f"{value_col}:Q",
                    scale=alt.Scale(domain=[0, xmax]),
                    title="Sales Change",
                    axis=alt.Axis(**_base_axis_kwargs()),
                ),
                tooltip=[
                    alt.Tooltip(f"{y_col}:N", title="Name"),
                    alt.Tooltip(f"{value_col}:Q", title="Change", format=",.2f"),
                ],
            )
        )

        # Value text matches bar color
        text = (
            alt.Chart(df)
            .mark_text(dx=8, align="left", **_label_kwargs(font_size=13, color=POSITIVE_BAR))
            .encode(
                y=alt.Y(
                    f"{y_col}:N",
                    sort=None,
                    title="",
                    axis=alt.Axis(labelLimit=320, **_base_axis_kwargs()),
                ),
                x=alt.X(
                    f"{value_col}:Q",
                    scale=alt.Scale(domain=[0, xmax]),
                    title="Sales Change",
                    axis=alt.Axis(**_base_axis_kwargs()),
                ),
                text="Label:N",
            )
        )

        st.altair_chart(
            (rules + dots + text).properties(height=max(250, len(df) * 36), title=title),
            use_container_width=True,
        )

    def _render_negative_lollipop_list(
        df: pd.DataFrame,
        y_col: str,
        value_col: str,
        title: str,
        show_right_labels: bool = False,
    ):
        if df.empty:
            st.info(f"No data available for {title.lower()}.")
            return

        xmax = float(df[value_col].abs().max()) if not df.empty else 0.0
        xmax = xmax * 1.15 if xmax > 0 else 1.0

        df = df.copy()
        df["RightEdge"] = 0.0

        y_axis = (
            alt.Axis(labels=False, ticks=False, domain=False)
            if show_right_labels
            else alt.Axis(labelLimit=320, **_base_axis_kwargs())
        )

        rules = (
            alt.Chart(df)
            .mark_rule(strokeWidth=2.5, color=NEGATIVE_BAR)
            .encode(
                y=alt.Y(f"{y_col}:N", sort=None, title="", axis=y_axis),
                x=alt.X(
                    "RightEdge:Q",
                    scale=alt.Scale(domain=[-xmax, 0]),
                    title="Sales Change",
                    axis=alt.Axis(**_base_axis_kwargs()),
                ),
                x2=f"{value_col}:Q",
            )
        )

        dots = (
            alt.Chart(df)
            .mark_circle(size=150, color=NEGATIVE_BAR)
            .encode(
                y=alt.Y(f"{y_col}:N", sort=None, title="", axis=y_axis),
                x=alt.X(
                    f"{value_col}:Q",
                    scale=alt.Scale(domain=[-xmax, 0]),
                    title="Sales Change",
                    axis=alt.Axis(**_base_axis_kwargs()),
                ),
                tooltip=[
                    alt.Tooltip(f"{y_col}:N", title="Name"),
                    alt.Tooltip(f"{value_col}:Q", title="Change", format=",.2f"),
                ],
            )
        )

        # Value text matches bar color
        value_text = (
            alt.Chart(df)
            .mark_text(dx=-8, align="right", **_label_kwargs(font_size=13, color=NEGATIVE_BAR))
            .encode(
                y=alt.Y(f"{y_col}:N", sort=None, title="", axis=y_axis),
                x=alt.X(
                    f"{value_col}:Q",
                    scale=alt.Scale(domain=[-xmax, 0]),
                    title="Sales Change",
                    axis=alt.Axis(**_base_axis_kwargs()),
                ),
                text="Label:N",
            )
        )

        layers = [rules, dots, value_text]

        if show_right_labels:
            # Right-side names use normal text and inherit theme via default axis-like styling
            name_text = (
                alt.Chart(df)
                .mark_text(dx=8, align="left", **_label_kwargs(font_size=13, color="#222222"))
                .encode(
                    y=alt.Y(
                        f"{y_col}:N",
                        sort=None,
                        title="",
                        axis=alt.Axis(labels=False, ticks=False, domain=False),
                    ),
                    x=alt.value(0),
                    text=f"{y_col}:N",
                )
            )
            layers.append(name_text)

        st.altair_chart(
            alt.layer(*layers).properties(height=max(250, len(df) * 36), title=title),
            use_container_width=True,
        )

    def _render_compare_lollipop(df: pd.DataFrame, title: str):
        if df.empty:
            st.info(f"No data available for {title.lower()}.")
            return

        long_df = pd.DataFrame(
            [
                {"Entity": row["Entity"], "Period": a_lbl, "Value": float(row["Current"])}
                for _, row in df.iterrows()
            ] + [
                {"Entity": row["Entity"], "Period": b_lbl, "Value": float(row["Compare"])}
                for _, row in df.iterrows()
            ]
        )
        long_df["RowLabel"] = long_df["Entity"] + " • " + long_df["Period"]
        long_df["Label"] = long_df["Value"].map(money)
        long_df["Zero"] = 0.0

        xmax = float(long_df["Value"].max()) if not long_df.empty else 0.0
        xmax = xmax * 1.15 if xmax > 0 else 1.0

        rules = (
            alt.Chart(long_df)
            .mark_rule(strokeWidth=2.5)
            .encode(
                y=alt.Y(
                    "RowLabel:N",
                    sort=None,
                    title="",
                    axis=alt.Axis(labelLimit=420, **_base_axis_kwargs()),
                ),
                x=alt.X(
                    "Zero:Q",
                    scale=alt.Scale(domain=[0, xmax]),
                    title="Sales",
                    axis=alt.Axis(**_base_axis_kwargs()),
                ),
                x2="Value:Q",
                color=alt.Color("Period:N", title="", legend=alt.Legend(labelFontSize=13)),
            )
        )

        dots = (
            alt.Chart(long_df)
            .mark_circle(size=150)
            .encode(
                y=alt.Y(
                    "RowLabel:N",
                    sort=None,
                    title="",
                    axis=alt.Axis(labelLimit=420, **_base_axis_kwargs()),
                ),
                x=alt.X(
                    "Value:Q",
                    scale=alt.Scale(domain=[0, xmax]),
                    title="Sales",
                    axis=alt.Axis(**_base_axis_kwargs()),
                ),
                color=alt.Color("Period:N", title="", legend=None),
                tooltip=[
                    alt.Tooltip("Entity:N", title="Name"),
                    alt.Tooltip("Period:N", title="Period"),
                    alt.Tooltip("Value:Q", title="Sales", format=",.2f"),
                ],
            )
        )

        # Text color matches the line/dot color
        text = (
            alt.Chart(long_df)
            .mark_text(dx=8, align="left", **_label_kwargs(font_size=12, color="#000000"))
            .encode(
                y=alt.Y(
                    "RowLabel:N",
                    sort=None,
                    title="",
                    axis=alt.Axis(labelLimit=420, **_base_axis_kwargs()),
                ),
                x=alt.X(
                    "Value:Q",
                    scale=alt.Scale(domain=[0, xmax]),
                    title="Sales",
                    axis=alt.Axis(**_base_axis_kwargs()),
                ),
                text="Label:N",
                color=alt.Color("Period:N", legend=None),
            )
        )

        st.altair_chart(
            (rules + dots + text).properties(height=max(220, len(long_df) * 34), title=title),
            use_container_width=True,
        )

    st.markdown("### Totals")
    t1, t2 = st.columns(2)
    with t1:
        _render_total_bars(_totals_df("Sales"), "Total Sales • Current vs Compare", "Sales")
    with t2:
        _render_total_bars(_totals_df("Units"), "Total Units • Current vs Compare", "Units")

    st.markdown("### Contributors")
    contrib_df = _contributors_df(driver_level)
    if contrib_df.empty:
        st.info("No contributor data available.")
    else:
        pos = contrib_df[contrib_df["Sales_Δ"] > 0].sort_values("Sales_Δ", ascending=False).head(10).copy()
        neg = contrib_df[contrib_df["Sales_Δ"] < 0].sort_values("Sales_Δ", ascending=True).head(10).copy()

        c1, c2 = st.columns(2)
        with c1:
            _render_positive_lollipop_list(pos, driver_level, "Sales_Δ", "Top Positive Contributors")
        with c2:
            _render_negative_lollipop_list(
                neg,
                driver_level,
                "Sales_Δ",
                "Top Negative Contributors",
                show_right_labels=True,
            )

    st.markdown("### SKU Movers")
    sku_df = _sku_increase_decline_df()
    inc = sku_df[sku_df["Sales_Δ"] > 0].sort_values("Sales_Δ", ascending=False).head(10).copy()
    dec = sku_df[sku_df["Sales_Δ"] < 0].sort_values("Sales_Δ", ascending=True).head(10).copy()

    s1, s2 = st.columns(2)
    with s1:
        _render_positive_lollipop_list(inc, "SKU", "Sales_Δ", "Top Increasing SKUs")
    with s2:
        _render_negative_lollipop_list(
            dec,
            "SKU",
            "Sales_Δ",
            "Top Declining SKUs",
            show_right_labels=True,
        )

    st.markdown("### Top 2 Compared Between Current and Compare")
    r1, r2 = st.columns(2)
    with r1:
        _render_compare_lollipop(_top2_compare_df("Retailer"), "Top 2 Retailers")
    with r2:
        _render_compare_lollipop(_top2_compare_df("Vendor"), "Top 2 Vendors")

    _render_compare_lollipop(_top2_compare_df("SKU"), "Top 2 SKUs")
