import streamlit as st
import plotly.express as px

from lib import (
    sidebar_filters,
    load_time_series,
    format_currency,
    pct_change,
    style_figure,
)


st.set_page_config(
    page_title="Price Trends - Housing Explorer",
    page_icon="📉",
    layout="wide",
)


st.title("📉 Price Trends")

st.write(
    "Track how residential transaction prices and activity "
    "have changed over time."
)


# FILTERS

start, end, type_codes, counties = sidebar_filters()


# AGGREGATION

frequency = st.radio(
    "Aggregation",
    [
        "Monthly",
        "Quarterly",
        "Yearly",
    ],
    horizontal=True,
)


frequency_map = {
    "Monthly": "M",
    "Quarterly": "Q",
    "Yearly": "Y",
}


df = load_time_series(
    start,
    end,
    type_codes,
    counties,
    freq=frequency_map[frequency],
)


if df.empty:
    st.warning(
        "No data is available for the selected filters."
    )
    st.stop()


# SUMMARY

first = df.iloc[0]
latest = df.iloc[-1]


price_change = pct_change(
    first["median_price"],
    latest["median_price"],
)


volume_change = pct_change(
    first["n_transactions"],
    latest["n_transactions"],
)


col1, col2, col3 = st.columns(3)


with col1:
    st.metric(
        "Latest median price",
        format_currency(
            latest["median_price"]
        ),
    )


with col2:

    if price_change is not None:

        st.metric(
            "Price change",
            f"{price_change:+.1f}%",
        )

    else:

        st.metric(
            "Price change",
            "—",
        )


with col3:

    if volume_change is not None:

        st.metric(
            "Transaction volume change",
            f"{volume_change:+.1f}%",
        )

    else:

        st.metric(
            "Transaction volume change",
            "—",
        )


# MEDIAN VS AVERAGE

st.markdown("---")

st.subheader("Median vs average transaction price")


fig_price = px.line(
    df,
    x="period",
    y=[
        "median_price",
        "avg_price",
    ],
    markers=True,
    title=(
        f"Median vs Average Transaction Price "
        f"({frequency})"
    ),
    labels={
        "period": "Period",
        "value": "Price (£)",
        "variable": "Measure",
    },
)


fig_price.update_traces(
    hovertemplate="£%{y:,.0f}<extra></extra>"
)


fig_price = style_figure(
    fig_price,
    height=500,
)


st.plotly_chart(
    fig_price,
    use_container_width=True,
)


st.info(
    "Median price represents the midpoint transaction. "
    "Average price can be influenced more heavily by unusually "
    "high-value transactions."
)


# TRANSACTION VOLUME

st.markdown("---")

st.subheader("Transaction volume")


fig_volume = px.bar(
    df,
    x="period",
    y="n_transactions",
    title=(
        f"Transaction Volume ({frequency})"
    ),
    labels={
        "period": "Period",
        "n_transactions": "Transactions",
    },
)


fig_volume = style_figure(
    fig_volume,
    height=400,
)


st.plotly_chart(
    fig_volume,
    use_container_width=True,
)


# FOOTER

st.markdown("---")

st.caption(
    "Use the sidebar to compare different property types "
    "and counties across the selected date range."
)