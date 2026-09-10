import pandas as pd
import plotly.express as px
import streamlit as st
from sqlalchemy import text

from lib import (
    format_currency,
    format_number,
    fqtn,
    get_engine,
    sidebar_filters,
    style_figure,
    where_clause,
)


st.set_page_config(
    page_title="Price Distribution - Housing Explorer",
    page_icon="💷",
    layout="wide",
)

st.title("💷 Price Distribution")
st.write(
    "Explore how recorded residential transaction prices are distributed "
    "across the market."
)

start, end, type_codes, counties = sidebar_filters()
wc, params = where_clause(start, end, type_codes, counties)

percentile_query = f"""
    SELECT
        COUNT(*)::BIGINT AS transaction_count,
        PERCENTILE_CONT(0.10) WITHIN GROUP (ORDER BY price) AS p10,
        PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY price) AS p25,
        PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY price) AS p50,
        PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY price) AS p75,
        PERCENTILE_CONT(0.90) WITHIN GROUP (ORDER BY price) AS p90
    FROM {fqtn()}
    WHERE {wc}
"""

with get_engine().begin() as conn:
    pct = pd.read_sql(text(percentile_query), conn, params=params).iloc[0]

transaction_count = int(pct["transaction_count"])

if transaction_count == 0:
    st.warning("No transactions were found for the selected filters.")
    st.stop()

p10 = pct["p10"]
p25 = pct["p25"]
median = pct["p50"]
p75 = pct["p75"]
p90 = pct["p90"]
iqr = p75 - p25

st.subheader("Market price distribution")

col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    st.metric("10th percentile", format_currency(p10))

with col2:
    st.metric("25th percentile", format_currency(p25))

with col3:
    st.metric("Median", format_currency(median))

with col4:
    st.metric("75th percentile", format_currency(p75))

with col5:
    st.metric("90th percentile", format_currency(p90))

st.caption(
    "The 25th percentile, for example, is the price below which "
    "25% of recorded transactions fall."
)

st.markdown("---")
st.subheader("Transaction price bands")

band_query = f"""
    SELECT
        CASE
            WHEN price < 100000 THEN 'Under £100k'
            WHEN price < 200000 THEN '£100k–£200k'
            WHEN price < 300000 THEN '£200k–£300k'
            WHEN price < 500000 THEN '£300k–£500k'
            WHEN price < 1000000 THEN '£500k–£1m'
            WHEN price < 2000000 THEN '£1m–£2m'
            WHEN price < 5000000 THEN '£2m–£5m'
            ELSE '£5m+'
        END AS price_band,
        COUNT(*)::BIGINT AS transactions
    FROM {fqtn()}
    WHERE {wc}
    GROUP BY 1
"""

with get_engine().begin() as conn:
    bands = pd.read_sql(text(band_query), conn, params=params)

band_order = [
    "Under £100k",
    "£100k–£200k",
    "£200k–£300k",
    "£300k–£500k",
    "£500k–£1m",
    "£1m–£2m",
    "£2m–£5m",
    "£5m+",
]

bands["price_band"] = pd.Categorical(
    bands["price_band"],
    categories=band_order,
    ordered=True,
)

bands = bands.sort_values("price_band")
bands["share"] = bands["transactions"] / transaction_count * 100

fig = px.bar(
    bands,
    x="price_band",
    y="transactions",
    labels={"price_band": "Transaction price", "transactions": "Transactions"},
    text="transactions",
)

fig.update_traces(texttemplate="%{text:,.0f}", textposition="outside")
fig = style_figure(fig, 475)
st.plotly_chart(fig, use_container_width=True)

st.markdown("---")
st.subheader("🔎 Key findings")

most_common = bands.loc[bands["transactions"].idxmax()]
high_value = bands[bands["price_band"] == "£5m+"]

high_value_count = (
    int(high_value["transactions"].iloc[0])
    if not high_value.empty
    else 0
)

high_value_share = high_value_count / transaction_count * 100

col1, col2, col3 = st.columns(3)

with col1:
    st.metric("Most common price band", str(most_common["price_band"]))
    st.caption(
        f"{format_number(most_common['transactions'])} transactions "
        "fall within this band."
    )

with col2:
    st.metric("Interquartile range", format_currency(iqr))
    st.caption(
        f"The middle 50% of transactions fall between "
        f"{format_currency(p25)} and {format_currency(p75)}."
    )

with col3:
    st.metric("£5m+ transactions", format_number(high_value_count))
    st.caption(f"{high_value_share:.3f}% of recorded transactions.")

st.markdown("---")
st.subheader("How to interpret this page")

st.markdown(
    f"""
    The median recorded transaction price is **{format_currency(median)}**,
    meaning half of transactions were below this value and half were above.

    The middle 50% of transactions fall between **{format_currency(p25)}**
    and **{format_currency(p75)}**.

    Transactions above **£5 million** remain part of all calculations but are
    grouped into a single band so a very small number of exceptionally
    high-value transactions do not dominate the visualisation.
    """
)

st.info(
    "Transaction prices are completed sale values. They are not a direct "
    "measure of household affordability."
)

st.caption(
    f"Transactions analysed: {transaction_count:,} · "
    f"Selected period: {start:%d %b %Y} to {end:%d %b %Y}"
)