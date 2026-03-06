import streamlit as st
import plotly.express as px
from lib import sidebar_filters, load_time_series

st.set_page_config(page_title="Price Trends - UK Housing", page_icon="📉", layout="wide")
st.title("📉 Price Trends")

start, end, type_codes, counties = sidebar_filters()

freq = st.radio("Aggregation", ["Monthly", "Quarterly", "Yearly"], horizontal=True)
freq_map = {"Monthly": "M", "Quarterly": "Q", "Yearly": "Y"}
df = load_time_series(start, end, type_codes, counties, freq=freq_map[freq])

if df.empty:
    st.warning("No data for selected filters.")
else:
    c1, c2 = st.columns(2)
    fig_median = px.line(df, x="period", y="median_price",
                         title=f"Median Price ({freq})", labels={"median_price": "£", "period": "Period"})
    c1.plotly_chart(fig_median, use_container_width=True)

    fig_avg = px.line(df, x="period", y="avg_price",
                      title=f"Average Price ({freq})", labels={"avg_price": "£", "period": "Period"})
    c2.plotly_chart(fig_avg, use_container_width=True)

    fig_vol = px.bar(df, x="period", y="n_transactions", title=f"Transactions ({freq})",
                     labels={"n_transactions": "Count", "period": "Period"})
    st.plotly_chart(fig_vol, use_container_width=True)