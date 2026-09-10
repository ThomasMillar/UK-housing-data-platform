import streamlit as st
import pandas as pd
import plotly.express as px

from sqlalchemy import text

from lib import (
    sidebar_filters,
    where_clause,
    get_engine,
    fqtn,
    format_currency,
    format_number,
    style_figure,
)


# PAGE CONFIG

st.set_page_config(
    page_title="Price Distribution - Housing Explorer",
    page_icon="💷",
    layout="wide",
)


# PAGE HEADER

st.title("💷 Price Distribution & Affordability")

st.write(
    "Explore how recorded residential property transaction prices "
    "are distributed across England and Wales."
)


# FILTERS

start, end, type_codes, counties = sidebar_filters()

wc, params = where_clause(
    start,
    end,
    type_codes,
    counties,
)


# PERCENTILE QUERY

percentile_query = f"""
SELECT

    COUNT(*) AS transaction_count,

    PERCENTILE_CONT(0.10)
        WITHIN GROUP (ORDER BY price) AS p10,

    PERCENTILE_CONT(0.25)
        WITHIN GROUP (ORDER BY price) AS p25,

    PERCENTILE_CONT(0.50)
        WITHIN GROUP (ORDER BY price) AS p50,

    PERCENTILE_CONT(0.75)
        WITHIN GROUP (ORDER BY price) AS p75,

    PERCENTILE_CONT(0.90)
        WITHIN GROUP (ORDER BY price) AS p90

FROM {fqtn()}

WHERE {wc}
"""


with get_engine().begin() as conn:
    percentile_df = pd.read_sql(
        text(percentile_query),
        conn,
        params=params,
    )


if percentile_df.empty:
    st.warning(
        "No data is available for the selected filters."
    )
    st.stop()


pct = percentile_df.iloc[0]

transaction_count = int(
    pct["transaction_count"]
)


if transaction_count == 0:
    st.warning(
        "No transactions were found for the selected filters."
    )
    st.stop()


p10 = pct["p10"]
p25 = pct["p25"]
p50 = pct["p50"]
p75 = pct["p75"]
p90 = pct["p90"]


# KPI CARDS

st.subheader("Market price distribution")

col1, col2, col3, col4, col5 = st.columns(5)


with col1:
    st.metric(
        "10th percentile",
        format_currency(p10),
    )


with col2:
    st.metric(
        "25th percentile",
        format_currency(p25),
    )


with col3:
    st.metric(
        "Median",
        format_currency(p50),
    )


with col4:
    st.metric(
        "75th percentile",
        format_currency(p75),
    )


with col5:
    st.metric(
        "90th percentile",
        format_currency(p90),
    )


st.caption(
    "A percentile shows the transaction price below which "
    "a given percentage of recorded transactions fall."
)


# MIDDLE 50%

iqr = p75 - p25


st.markdown("---")

st.subheader("Middle 50% of the market")


st.write(
    f"Half of all recorded transactions fall between "
    f"**{format_currency(p25)}** and "
    f"**{format_currency(p75)}**."
)


# Create a simple percentile range visual.
range_df = pd.DataFrame(
    {
        "Measure": ["Price range"],
        "25th percentile": [p25],
        "75th percentile": [p75],
    }
)


fig_range = px.bar(
    range_df,
    x=["25th percentile", "75th percentile"],
    y="Measure",
    orientation="h",
    barmode="group",
    title="Interquartile Price Range",
)


fig_range.update_layout(
    xaxis_title="Transaction price (£)",
    yaxis_title="",
    showlegend=True,
)


fig_range = style_figure(
    fig_range,
    height=250,
)


st.plotly_chart(
    fig_range,
    use_container_width=True,
)


# PRICE BANDS

st.markdown("---")

st.subheader("Transaction price bands")

st.write(
    "Grouping transactions into price bands makes the distribution "
    "easier to interpret than a raw histogram."
)


band_query = f"""
SELECT
    CASE
        WHEN price < 100000
            THEN 'Under £100k'

        WHEN price < 200000
            THEN '£100k–£200k'

        WHEN price < 300000
            THEN '£200k–£300k'

        WHEN price < 500000
            THEN '£300k–£500k'

        WHEN price < 1000000
            THEN '£500k–£1m'

        WHEN price < 2000000
            THEN '£1m–£2m'

        WHEN price < 5000000
            THEN '£2m–£5m'

        ELSE '£5m+'
    END AS price_band,

    COUNT(*) AS transactions

FROM {fqtn()}

WHERE {wc}

GROUP BY 1
"""


with get_engine().begin() as conn:
    bands = pd.read_sql(
        text(band_query),
        conn,
        params=params,
    )


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


# Correct the £2m–£5m label if returned from the database.
bands["price_band"] = bands["price_band"].replace(
    {
        "£2m–£5m": "£2m–£5m",
    }
)


bands["price_band"] = pd.Categorical(
    bands["price_band"],
    categories=[
        "Under £100k",
        "£100k–£200k",
        "£200k–£300k",
        "£300k–£500k",
        "£500k–£1m",
        "£1m–£2m",
        "£2m–£5m",
        "£5m+",
    ],
    ordered=True,
)


bands = bands.sort_values(
    "price_band"
)


# MARKET SHARE

bands["share"] = (
    bands["transactions"]
    / transaction_count
    * 100
)


fig_bands = px.bar(
    bands,
    x="price_band",
    y="transactions",
    title="Recorded Transactions by Price Band",
    labels={
        "price_band": "Transaction price",
        "transactions": "Transactions",
    },
    text="transactions",
)


fig_bands.update_traces(
    texttemplate="%{text:,.0f}",
    textposition="outside",
)


fig_bands = style_figure(
    fig_bands,
    height=500,
)


st.plotly_chart(
    fig_bands,
    use_container_width=True,
)


# INSIGHTS

most_common_band = bands.loc[
    bands["transactions"].idxmax()
]


st.markdown("---")

st.subheader("🔎 Key findings")


col1, col2, col3 = st.columns(3)


with col1:

    st.metric(
        "Most common price band",
        most_common_band["price_band"],
    )

    st.caption(
        f"{format_number(most_common_band['transactions'])} "
        "recorded transactions fall within this band."
    )


with col2:

    st.metric(
        "Interquartile range",
        format_currency(iqr),
    )

    st.caption(
        "The middle 50% of recorded transactions "
        "fall within this range."
    )


with col3:

    five_million = bands[
        bands["price_band"] == "£5m+"
    ]


    if not five_million.empty:

        high_value_count = int(
            five_million["transactions"].iloc[0]
        )

        high_value_share = (
            high_value_count
            / transaction_count
            * 100
        )

    else:

        high_value_count = 0
        high_value_share = 0


    st.metric(
        "£5m+ transactions",
        format_number(high_value_count),
    )

    st.caption(
        f"{high_value_share:.3f}% of all recorded transactions."
    )


# INTERPRETATION

st.markdown("---")

st.subheader("How to interpret this page")


st.write(
    f"""
    The **median transaction price is {format_currency(p50)}**, meaning
    half of recorded transactions were below this price and half were above.

    The middle 50% of transactions fall between
    **{format_currency(p25)}** and **{format_currency(p75)}**.

    The price-band chart groups transactions into ranges so that the main
    housing market is easier to compare, while transactions above
    **£5 million** are grouped separately rather than distorting the visual.
    """
)


st.info(
    "Transaction prices describe recorded property sales. "
    "They do not directly measure household affordability, asking prices "
    "or current market valuations."
)


# DATA NOte

st.caption(
    f"Transactions analysed: {transaction_count:,} | "
    f"Period: {start.strftime('%d %b %Y')} "
    f"to {end.strftime('%d %b %Y')}"
)