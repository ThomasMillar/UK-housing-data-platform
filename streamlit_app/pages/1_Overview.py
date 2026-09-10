import streamlit as st
import plotly.express as px

from lib import (
    sidebar_filters,
    load_kpis,
    load_time_series,
    format_currency,
    format_number,
    pct_change,
    style_figure,
)


st.set_page_config(
    page_title="Overview - Housing Explorer",
    page_icon="📈",
    layout="wide",
)


st.title("📈 Market Overview")

st.caption(
    "Explore housing market activity across England and Wales. "
    "Use the sidebar to filter the analysis."
)

# FILTERS

start, end, type_codes, counties = sidebar_filters()


# LOAD DATA

kpis = load_kpis(
    start,
    end,
    type_codes,
    counties,
)

ts = load_time_series(
    start,
    end,
    type_codes,
    counties,
    freq="M",
)


if ts.empty:
    st.warning(
        "No data is available for the selected filters."
    )
    st.stop()


# PREPARE SUMMARY VALUES

latest = ts.iloc[-1]
first = ts.iloc[0]


price_change = pct_change(
    first["median_price"],
    latest["median_price"],
)


volume_change = pct_change(
    first["n_transactions"],
    latest["n_transactions"],
)


# KPI CARDS

st.subheader("Market snapshot")


col1, col2, col3, col4 = st.columns(4)


with col1:
    st.metric(
        "Transactions",
        format_number(
            kpis["n_transactions"]
        ),
    )


with col2:
    st.metric(
        "Median price",
        format_currency(
            kpis["median_price"]
        ),
    )


with col3:
    st.metric(
        "Average price",
        format_currency(
            kpis["avg_price"]
        ),
    )


with col4:
    st.metric(
        "Total transaction value",
        format_currency(
            kpis["total_value"]
        ),
    )


# KEY FINDINGS

st.markdown("---")
st.subheader("🔎 Key findings")


insight1, insight2, insight3 = st.columns(3)


with insight1:

    if price_change is not None:

        direction = (
            "increase"
            if price_change >= 0
            else "decrease"
        )

        st.metric(
            "Median price change",
            f"{price_change:+.1f}%",
        )

        st.caption(
            f"Median transaction price changed by "
            f"{abs(price_change):.1f}% between the first "
            f"and latest available periods."
        )

    else:

        st.info(
            "Not enough data to calculate price change."
        )


with insight2:

    if volume_change is not None:

        direction = (
            "increase"
            if volume_change >= 0
            else "decrease"
        )

        st.metric(
            "Transaction volume change",
            f"{volume_change:+.1f}%",
        )

        st.caption(
            f"Transaction volume changed by "
            f"{abs(volume_change):.1f}% between the first "
            f"and latest available periods."
        )

    else:

        st.info(
            "Not enough data to calculate volume change."
        )


with insight3:

    st.metric(
        "Latest monthly median",
        format_currency(
            latest["median_price"]
        ),
    )

    latest_period = latest["period"]

    st.caption(
        "Latest available period: "
        f"{latest_period.strftime('%B %Y')}"
    )


# MEDIAN PRICE TREND

st.markdown("---")

st.subheader("Median transaction price")


fig_price = px.line(
    ts,
    x="period",
    y="median_price",
    markers=True,
    title="Median Transaction Price Over Time",
    labels={
        "period": "Period",
        "median_price": "Median price (£)",
    },
)


fig_price.update_traces(
    hovertemplate="£%{y:,.0f}<extra></extra>"
)


fig_price = style_figure(
    fig_price,
    height=450,
)


st.plotly_chart(
    fig_price,
    use_container_width=True,
)


st.caption(
    "Median price represents the middle recorded transaction "
    "and is less affected by unusually high-value transactions "
    "than the average."
)


# TRANSACTION VOLUME

st.markdown("---")

st.subheader("Transaction activity")


fig_volume = px.bar(
    ts,
    x="period",
    y="n_transactions",
    title="Transaction Volume Over Time",
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


st.caption(
    "Transaction volume shows the number of recorded residential "
    "property transactions in each period."
)


# FOOTER

st.markdown("---")

st.caption(
    "Analysis period: "
    f"{start.strftime('%d %b %Y')} "
    f"to {end.strftime('%d %b %Y')}"
)