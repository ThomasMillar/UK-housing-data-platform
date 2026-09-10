import pandas as pd
import plotly.express as px
import streamlit as st

from lib import (
    add_monthly_metrics,
    format_currency,
    format_number,
    load_date_range,
    load_kpis,
    load_time_series,
    sidebar_filters,
    style_figure,
)


st.set_page_config(
    page_title="Overview - Housing Explorer",
    page_icon="📈",
    layout="wide",
)

st.title("📈 Market Overview")
st.caption(
    "A high-level view of prices and transaction activity across England and Wales."
)

start, end, type_codes, counties = sidebar_filters()

kpis = load_kpis(start, end, type_codes, counties)

# Pull an extra year so YoY calculations still work near the start of the selected range.
history_start = (pd.Timestamp(start) - pd.DateOffset(years=1)).date()
monthly = load_time_series(history_start, end, type_codes, counties, freq="M")
monthly = add_monthly_metrics(monthly)
monthly_display = monthly[monthly["period"] >= pd.Timestamp(start)].copy()

if monthly_display.empty:
    st.warning("No data is available for the selected filters.")
    st.stop()

latest = monthly_display.iloc[-1]
yoy_rows = monthly_display.dropna(
    subset=["median_price_yoy_pct", "transactions_yoy_pct"]
)

latest_yoy = yoy_rows.iloc[-1] if not yoy_rows.empty else None

st.subheader("Market snapshot")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Transactions", format_number(kpis["n_transactions"]))

with col2:
    st.metric("Median price", format_currency(kpis["median_price"]))

with col3:
    value = (
        f"{latest_yoy['median_price_yoy_pct']:+.1f}%"
        if latest_yoy is not None
        else "—"
    )
    st.metric("Latest YoY price change", value)

with col4:
    value = (
        f"{latest_yoy['transactions_yoy_pct']:+.1f}%"
        if latest_yoy is not None
        else "—"
    )
    st.metric("Latest YoY transaction change", value)

st.caption(
    f"Average transaction price: {format_currency(kpis['avg_price'])} · "
    f"Total transaction value: {format_currency(kpis['total_value'])}"
)

st.markdown("---")
st.subheader("🔎 Key findings")

insight1, insight2, insight3 = st.columns(3)

with insight1:
    if latest_yoy is not None:
        change = latest_yoy["median_price_yoy_pct"]
        direction = "higher" if change >= 0 else "lower"

        st.info(
            f"Median prices were **{abs(change):.1f}% {direction}** than "
            f"the same month a year earlier."
        )
    else:
        st.info("Select at least one year of comparable data to calculate YoY change.")

with insight2:
    if latest_yoy is not None:
        change = latest_yoy["transactions_yoy_pct"]
        direction = "higher" if change >= 0 else "lower"

        st.info(
            f"Transaction volume was **{abs(change):.1f}% {direction}** "
            f"than the same month a year earlier."
        )
    else:
        st.info("Not enough data is available to compare transaction volumes year on year.")

with insight3:
    if kpis["median_price"]:
        mean_gap = ((kpis["avg_price"] - kpis["median_price"]) / kpis["median_price"]) * 100

        st.info(
            f"The average price is **{mean_gap:.1f}% above the median**, "
            "showing the effect of higher-value transactions."
        )

st.markdown("---")
st.subheader("Median transaction price")

price_df = monthly_display.rename(columns={
    "median_price": "Monthly median",
    "median_price_12m_avg": "12-month rolling average",
})

fig_price = px.line(
    price_df,
    x="period",
    y=["Monthly median", "12-month rolling average"],
    labels={"period": "Period", "value": "Price (£)", "variable": "Measure"},
)

fig_price.update_layout(hovermode="x unified")
fig_price.update_yaxes(tickprefix="£", tickformat=",")
fig_price = style_figure(fig_price, 450)

st.plotly_chart(fig_price, use_container_width=True)

st.caption(
    "The rolling line is the 12-month average of monthly median prices, "
    "which reduces short-term monthly noise."
)

st.markdown("---")
st.subheader("Transaction activity")

fig_volume = px.bar(
    monthly_display,
    x="period",
    y="n_transactions",
    labels={"period": "Period", "n_transactions": "Transactions"},
)

fig_volume.update_layout(hovermode="x unified")
fig_volume = style_figure(fig_volume, 400)

st.plotly_chart(fig_volume, use_container_width=True)

data_range = load_date_range()
st.caption(
    f"Selected period: {start:%d %b %Y} to {end:%d %b %Y} · "
    f"Dataset currently available through {data_range['max_d']:%d %b %Y}"
)