import streamlit as st
import plotly.express as px
from lib import sidebar_filters, load_kpis, load_time_series

st.set_page_config(page_title="Overview - UK Housing", page_icon="📈", layout="wide")
st.title("📈 Overview")

start, end, type_codes, counties = sidebar_filters()

kpis = load_kpis(start, end, type_codes, counties)

c1, c2, c3, c4 = st.columns(4)
c1.metric("Transactions", f"{int(kpis['n_transactions']):,}")
c2.metric("Median Price", f"£{kpis['median_price']:,.0f}" if kpis['median_price'] else "—")
c3.metric("Average Price", f"£{kpis['avg_price']:,.0f}" if kpis['avg_price'] else "—")
c4.metric("Total Value", f"£{int(kpis['total_value']):,}" if kpis['total_value'] else "—")

st.markdown("---")

ts = load_time_series(start, end, type_codes, counties, freq="M")
if ts.empty:
    st.warning("No data for selected filters.")
else:
    fig = px.line(ts, x="period", y=["median_price", "avg_price"],
                  labels={"value": "Price (£)", "period": "Period", "variable": "Measure"},
                  title="Average vs Median Price Over Time")
    st.plotly_chart(fig, use_container_width=True)

    fig2 = px.bar(ts, x="period", y="n_transactions", title="Transactions Over Time")
    st.plotly_chart(fig2, use_container_width=True)