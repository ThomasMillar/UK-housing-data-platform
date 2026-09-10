import streamlit as st
import plotly.express as px

from lib import (
    sidebar_filters,
    load_property_mix,
    format_currency,
    format_number,
    style_figure,
)


st.set_page_config(
    page_title="Property Mix - Housing Explorer",
    page_icon="🏘️",
    layout="wide",
)


st.title("🏘️ Property Mix")

st.write(
    "Understand which property types make up the market "
    "and how their transaction prices differ."
)


# FILTERS

start, end, type_codes, counties = sidebar_filters()


# LOAD DATA

df = load_property_mix(
    start,
    end,
    type_codes,
    counties,
)


if df.empty:
    st.warning(
        "No data is available for the selected filters."
    )
    st.stop()


# CALCULATE MARKET SHARE

total_transactions = df["n"].sum()


df["share"] = (
    df["n"]
    / total_transactions
    * 100
)


# SUMMARY

highest_price = df.loc[
    df["median_price"].idxmax()
]


highest_volume = df.loc[
    df["n"].idxmax()
]


col1, col2, col3 = st.columns(3)


with col1:
    st.metric(
        "Most common property type",
        highest_volume["Property"],
    )


with col2:
    st.metric(
        "Highest median price",
        highest_price["Property"],
    )


with col3:
    st.metric(
        "Total transactions",
        format_number(
            total_transactions
        ),
    )


# CHARTS

st.markdown("---")


left, right = st.columns(2)


with left:

    st.subheader("Transactions by property type")

    mix_df = (
        df
        .sort_values(
            "n",
            ascending=True,
        )
    )

    fig_mix = px.bar(
        mix_df,
        x="n",
        y="Property",
        orientation="h",
        title="Transaction Volume",
        labels={
            "n": "Transactions",
            "Property": "Property type",
        },
        text="n",
    )

    fig_mix.update_traces(
        texttemplate="%{text:,.0f}",
        textposition="outside",
    )

    fig_mix = style_figure(
        fig_mix,
        height=450,
    )

    st.plotly_chart(
        fig_mix,
        use_container_width=True,
    )


with right:

    st.subheader("Median price by property type")

    price_df = (
        df
        .sort_values(
            "median_price",
            ascending=True,
        )
    )

    fig_price = px.bar(
        price_df,
        x="median_price",
        y="Property",
        orientation="h",
        title="Median Transaction Price",
        labels={
            "median_price": "Median price (£)",
            "Property": "Property type",
        },
        text="median_price",
    )

    fig_price.update_traces(
        texttemplate="£%{text:,.0f}",
        textposition="outside",
    )

    fig_price = style_figure(
        fig_price,
        height=450,
    )

    st.plotly_chart(
        fig_price,
        use_container_width=True,
    )


# MARKET SHARE

st.markdown("---")

st.subheader("Market share")


share_df = (
    df[
        [
            "Property",
            "share",
        ]
    ]
    .sort_values(
        "share",
        ascending=False,
    )
)


fig_share = px.bar(
    share_df,
    x="Property",
    y="share",
    title="Share of Recorded Transactions",
    labels={
        "Property": "Property type",
        "share": "Share of transactions (%)",
    },
    text="share",
)


fig_share.update_traces(
    texttemplate="%{text:.1f}%",
    textposition="outside",
)


fig_share.update_yaxes(
    ticksuffix="%",
)


fig_share = style_figure(
    fig_share,
    height=400,
)


st.plotly_chart(
    fig_share,
    use_container_width=True,
)


# COMPARISON TABLE

st.markdown("---")

st.subheader("📊 Property type comparison")


comparison = df[
    [
        "Property",
        "n",
        "share",
        "median_price",
    ]
].copy()


comparison["Transactions"] = (
    comparison["n"]
    .apply(format_number)
)


comparison["Market Share"] = (
    comparison["share"]
    .map(
        lambda value: f"{value:.1f}%"
    )
)


comparison["Median Price"] = (
    comparison["median_price"]
    .apply(format_currency)
)


comparison = comparison[
    [
        "Property",
        "Transactions",
        "Market Share",
        "Median Price",
    ]
]


st.dataframe(
    comparison,
    use_container_width=True,
    hide_index=True,
)