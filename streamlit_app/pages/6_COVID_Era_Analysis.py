import pandas as pd
import plotly.express as px
import streamlit as st

from lib import (
    format_currency,
    load_geo_summary,
    load_property_mix,
    load_time_series,
    sidebar_filters,
    style_figure,
)

st.set_page_config(
    page_title="COVID-Era Analysis - Housing Explorer",
    page_icon="🦠",
    layout="wide",
)

st.title("🦠 COVID-Era Housing Market Analysis")
st.write(
    "Explore how recorded housing transactions changed around the COVID-era period. "
    "The analysis is descriptive and does not assume COVID alone caused the changes."
)

start, end, type_codes, counties = sidebar_filters()

analysis_start = max(pd.Timestamp(start), pd.Timestamp("2019-01-01"))
analysis_end = min(pd.Timestamp(end), pd.Timestamp("2022-12-31"))

if analysis_start > analysis_end:
    st.info("Select a date range that overlaps 2019–2022 to use this page.")
    st.stop()

monthly = load_time_series(
    analysis_start.date(), analysis_end.date(), type_codes, counties, freq="M"
)

if monthly.empty:
    st.warning("No data is available for the selected filters.")
    st.stop()

monthly["period"] = pd.to_datetime(monthly["period"])
monthly["year"] = monthly["period"].dt.year

yearly = (
    monthly.groupby("year", as_index=False)
    .agg(
        median_price=("median_price", "median"),
        transactions=("n_transactions", "sum"),
    )
)

available_years = set(yearly["year"].tolist())

st.subheader("Headline comparison")

baseline = yearly[yearly["year"] == 2019]
rebound = yearly[yearly["year"] == 2021]

baseline_price = baseline["median_price"].iloc[0] if not baseline.empty else None
baseline_transactions = baseline["transactions"].iloc[0] if not baseline.empty else None
rebound_price = rebound["median_price"].iloc[0] if not rebound.empty else None
rebound_transactions = rebound["transactions"].iloc[0] if not rebound.empty else None

price_change = (
    ((rebound_price - baseline_price) / baseline_price) * 100
    if baseline_price and rebound_price
    else None
)

transaction_change = (
    ((rebound_transactions - baseline_transactions) / baseline_transactions) * 100
    if baseline_transactions and rebound_transactions
    else None
)

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("2019 median price", format_currency(baseline_price))

with col2:
    st.metric("2021 median price", format_currency(rebound_price))

with col3:
    st.metric(
        "2019 → 2021 price change",
        f"{price_change:+.1f}%" if price_change is not None else "—",
    )

with col4:
    st.metric(
        "2019 → 2021 transaction change",
        f"{transaction_change:+.1f}%" if transaction_change is not None else "—",
    )

st.caption(
    "2019 is used as a pre-COVID baseline and 2021 as a rebound comparison year. "
    "These figures describe association over time rather than causation."
)

st.markdown("---")
st.subheader("Monthly median price")

fig_price = px.line(
    monthly,
    x="period",
    y="median_price",
    labels={"period": "Month", "median_price": "Median price (£)"},
)

fig_price.add_vrect(
    x0="2020-03-01",
    x1="2021-07-19",
    fillcolor="grey",
    opacity=0.12,
    line_width=0,
    annotation_text="COVID-era restrictions",
    annotation_position="top left",
)

fig_price.update_layout(hovermode="x unified")
fig_price.update_yaxes(tickprefix="£", tickformat=",")
fig_price.update_traces(
    hovertemplate="%{x|%b %Y}<br>Median: £%{y:,.0f}<extra></extra>"
)
fig_price = style_figure(fig_price, 450)

st.plotly_chart(fig_price, use_container_width=True)

st.markdown("---")
st.subheader("Monthly transaction volume")

fig_volume = px.bar(
    monthly,
    x="period",
    y="n_transactions",
    labels={"period": "Month", "n_transactions": "Transactions"},
)

fig_volume.add_vrect(
    x0="2020-03-01",
    x1="2021-07-19",
    fillcolor="grey",
    opacity=0.12,
    line_width=0,
)

fig_volume.update_layout(hovermode="x unified")
fig_volume.update_traces(
    hovertemplate="%{x|%b %Y}<br>%{y:,.0f} transactions<extra></extra>"
)
fig_volume = style_figure(fig_volume, 425)

st.plotly_chart(fig_volume, use_container_width=True)

st.markdown("---")
st.subheader("Year-by-year comparison")

comparison = yearly[yearly["year"].isin([2019, 2020, 2021, 2022])].copy()
left, right = st.columns(2)

with left:
    fig_year_price = px.bar(
        comparison,
        x="year",
        y="median_price",
        text="median_price",
        title="Median transaction price",
        labels={"year": "Year", "median_price": "Median price (£)"},
    )

    fig_year_price.update_traces(
        texttemplate="£%{text:,.0f}",
        textposition="inside",
        hovertemplate="%{x}<br>Median: £%{y:,.0f}<extra></extra>",
    )
    fig_year_price.update_yaxes(tickprefix="£", tickformat=",")
    fig_year_price.update_xaxes(type="category")
    fig_year_price = style_figure(fig_year_price, 375)
    st.plotly_chart(fig_year_price, use_container_width=True)

with right:
    fig_year_volume = px.bar(
        comparison,
        x="year",
        y="transactions",
        text="transactions",
        title="Transaction volume",
        labels={"year": "Year", "transactions": "Transactions"},
    )

    fig_year_volume.update_traces(
        texttemplate="%{text:,.0f}",
        textposition="inside",
        hovertemplate="%{x}<br>%{y:,.0f} transactions<extra></extra>",
    )
    fig_year_volume.update_xaxes(type="category")
    fig_year_volume = style_figure(fig_year_volume, 375)
    st.plotly_chart(fig_year_volume, use_container_width=True)

st.markdown("---")
st.subheader("Property type changes")

if 2019 in available_years and 2021 in available_years:
    property_2019 = load_property_mix(
        pd.Timestamp("2019-01-01").date(),
        pd.Timestamp("2019-12-31").date(),
        type_codes,
        counties,
    )
    property_2021 = load_property_mix(
        pd.Timestamp("2021-01-01").date(),
        pd.Timestamp("2021-12-31").date(),
        type_codes,
        counties,
    )

    property_compare = property_2019[
        ["property_type", "Property", "median_price", "n"]
    ].merge(
        property_2021[["property_type", "median_price", "n"]],
        on="property_type",
        how="inner",
        suffixes=("_2019", "_2021"),
    )

    property_compare["price_change_pct"] = (
        (property_compare["median_price_2021"] - property_compare["median_price_2019"])
        / property_compare["median_price_2019"]
        * 100
    )
    property_compare["change_label"] = property_compare["price_change_pct"].map(
        lambda x: f"{x:+.1f}%"
    )

    fig_property = px.bar(
        property_compare.sort_values("price_change_pct"),
        x="price_change_pct",
        y="Property",
        orientation="h",
        text="change_label",
        labels={
            "price_change_pct": "Median price change (%)",
            "Property": "Property type",
        },
    )

    fig_property.update_traces(
        textposition="inside",
        hovertemplate="<b>%{y}</b><br>Price change: %{x:.1f}%<extra></extra>",
    )
    fig_property.update_xaxes(ticksuffix="%", tickformat=".1f")
    fig_property = style_figure(fig_property, 400)
    st.plotly_chart(fig_property, use_container_width=True)

    strongest_property = property_compare.loc[
        property_compare["price_change_pct"].idxmax()
    ]

    st.info(
        f"{strongest_property['Property']} recorded the largest median price increase "
        f"between 2019 and 2021 at {strongest_property['price_change_pct']:.1f}%."
    )
else:
    st.info("2019 and 2021 data are both required for the property-type comparison.")

st.markdown("---")
st.subheader("Regional changes")

if 2019 in available_years and 2021 in available_years:
    geo_2019 = load_geo_summary(
        pd.Timestamp("2019-01-01").date(),
        pd.Timestamp("2019-12-31").date(),
        type_codes,
        counties,
        geo="county",
    )
    geo_2021 = load_geo_summary(
        pd.Timestamp("2021-01-01").date(),
        pd.Timestamp("2021-12-31").date(),
        type_codes,
        counties,
        geo="county",
    )

    geo_compare = geo_2019[
        ["region", "n", "median_price"]
    ].merge(
        geo_2021[["region", "n", "median_price"]],
        on="region",
        how="inner",
        suffixes=("_2019", "_2021"),
    )

    geo_compare = geo_compare[
        (geo_compare["n_2019"] >= 500) & (geo_compare["n_2021"] >= 500)
    ].copy()

    geo_compare["price_change_pct"] = (
        (geo_compare["median_price_2021"] - geo_compare["median_price_2019"])
        / geo_compare["median_price_2019"]
        * 100
    )

    top_regions = (
        geo_compare.nlargest(10, "price_change_pct")
        .sort_values("price_change_pct")
        .copy()
    )

    top_regions["change_label"] = top_regions["price_change_pct"].map(
        lambda x: f"{x:+.1f}%"
    )

    fig_regions = px.bar(
        top_regions,
        x="price_change_pct",
        y="region",
        orientation="h",
        text="change_label",
        labels={"price_change_pct": "Median price change (%)", "region": "County"},
    )

    fig_regions.update_traces(
        textposition="inside",
        hovertemplate="<b>%{y}</b><br>Price change: %{x:.1f}%<extra></extra>",
    )
    fig_regions.update_xaxes(ticksuffix="%", tickformat=".1f")
    fig_regions = style_figure(fig_regions, 450)
    st.plotly_chart(fig_regions, use_container_width=True)

    st.caption(
        "Shows the 10 counties with the largest 2019–2021 median price increases. "
        "Counties require at least 500 transactions in both years."
    )

st.markdown("---")
st.subheader("What this page shows")

if price_change is not None and transaction_change is not None:
    price_direction = "higher" if price_change >= 0 else "lower"
    volume_direction = "higher" if transaction_change >= 0 else "lower"

    st.markdown(
        f'''
        - The 2021 median transaction price was **{abs(price_change):.1f}% {price_direction}**
          than the 2019 baseline.
        - 2021 transaction volume was **{abs(transaction_change):.1f}% {volume_direction}**
          than in 2019.
        - The charts show how prices and transaction activity changed through the
          disruption and rebound period rather than attributing those changes to one cause.
        '''
    )

st.info(
    "Housing-market conditions during this period were also affected by factors such as "
    "interest rates, stamp-duty policy, supply constraints and changing buyer behaviour."
)

st.caption(f"Displayed period: {analysis_start:%d %b %Y} to {analysis_end:%d %b %Y}")
