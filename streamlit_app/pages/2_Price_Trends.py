import pandas as pd
import plotly.express as px
import streamlit as st

from lib import (
    add_monthly_metrics,
    format_currency,
    format_number,
    load_time_series,
    sidebar_filters,
    style_figure,
)

st.set_page_config(
    page_title="Price Trends - Housing Explorer",
    page_icon="📉",
    layout="wide",
)

st.title("📉 Price Trends")
st.write("Track transaction prices, year-on-year movements and longer-term market activity.")

start, end, type_codes, counties = sidebar_filters()

frequency = st.radio(
    "Aggregation",
    ["Monthly", "Quarterly", "Yearly"],
    horizontal=True,
)

frequency_map = {
    "Monthly": "M",
    "Quarterly": "Q",
    "Yearly": "Y",
}

trend_df = load_time_series(
    start, end, type_codes, counties, freq=frequency_map[frequency]
)

# Load an extra year so rolling and YoY calculations work correctly.
history_start = (pd.Timestamp(start) - pd.DateOffset(years=1)).date()
monthly = load_time_series(
    history_start, end, type_codes, counties, freq="M"
)

if trend_df.empty or monthly.empty:
    st.warning("No data is available for the selected filters.")
    st.stop()

monthly = add_monthly_metrics(monthly)
monthly = monthly[monthly["period"] >= pd.Timestamp(start)].copy()

latest = monthly.iloc[-1]
latest_yoy_rows = monthly.dropna(subset=["median_price_yoy_pct"])
latest_yoy = latest_yoy_rows.iloc[-1] if not latest_yoy_rows.empty else None

rolling_rows = monthly.dropna(subset=["transactions_12m"])
rolling_volume = (
    rolling_rows.iloc[-1]["transactions_12m"]
    if not rolling_rows.empty
    else None
)

col1, col2, col3 = st.columns(3)

with col1:
    st.metric("Latest median price", format_currency(latest["median_price"]))

with col2:
    value = (
        f"{latest_yoy['median_price_yoy_pct']:+.1f}%"
        if latest_yoy is not None
        else "—"
    )
    st.metric("Latest YoY price change", value)

with col3:
    st.metric(
        "Rolling 12-month transactions",
        format_number(rolling_volume),
    )

st.markdown("---")
st.subheader("Median vs average price")

price_df = trend_df.rename(
    columns={
        "median_price": "Median price",
        "avg_price": "Average price",
    }
)

fig_price = px.line(
    price_df,
    x="period",
    y=["Median price", "Average price"],
    markers=frequency != "Monthly",
    labels={
        "period": "Period",
        "value": "Price (£)",
        "variable": "Measure",
    },
)

fig_price.update_layout(hovermode="x unified")
fig_price.update_yaxes(tickprefix="£", tickformat=",")
fig_price = style_figure(fig_price, 475)

st.plotly_chart(fig_price, use_container_width=True)

st.caption(
    "Median price is less affected by unusually expensive transactions "
    "than the average."
)

st.markdown("---")
st.subheader("Longer-term movement")

left, right = st.columns(2)

with left:
    rolling_price = monthly.dropna(
        subset=["median_price_12m_avg"]
    ).copy()

    fig_rolling = px.line(
        rolling_price,
        x="period",
        y="median_price_12m_avg",
        title="12-month smoothed price trend",
        labels={
            "period": "Period",
            "median_price_12m_avg": "Price (£)",
        },
    )

    fig_rolling.update_yaxes(tickprefix="£", tickformat=",")
    fig_rolling = style_figure(fig_rolling, 400)

    st.plotly_chart(fig_rolling, use_container_width=True)

with right:
    yoy_df = monthly.dropna(
        subset=["median_price_yoy_pct"]
    ).copy()

    fig_yoy = px.bar(
        yoy_df,
        x="period",
        y="median_price_yoy_pct",
        title="Year-on-year median price change",
        labels={
            "period": "Period",
            "median_price_yoy_pct": "YoY change (%)",
        },
    )

    fig_yoy.add_hline(y=0)
    fig_yoy.update_yaxes(ticksuffix="%", tickformat=".1f")
    fig_yoy.update_traces(
        hovertemplate="%{y:.1f}%<extra></extra>"
    )
    fig_yoy = style_figure(fig_yoy, 400)

    st.plotly_chart(fig_yoy, use_container_width=True)

st.markdown("---")
st.subheader("Rolling transaction activity")

rolling_volume_df = monthly.dropna(
    subset=["transactions_12m"]
).copy()

fig_transactions = px.line(
    rolling_volume_df,
    x="period",
    y="transactions_12m",
    labels={
        "period": "Period",
        "transactions_12m": "Transactions in previous 12 months",
    },
)

fig_transactions.update_layout(hovermode="x unified")
fig_transactions.update_traces(
    hovertemplate="%{y:,.0f} transactions<extra></extra>"
)
fig_transactions = style_figure(fig_transactions, 400)

st.plotly_chart(fig_transactions, use_container_width=True)

st.caption(
    "Rolling 12-month totals reduce normal monthly seasonality "
    "and make longer-term changes easier to see."
)