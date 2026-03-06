import streamlit as st
import pandas as pd
import plotly.express as px
from lib import sidebar_filters, where_clause, get_engine, fqtn
from sqlalchemy import text

st.set_page_config(page_title="Affordability - UK Housing", page_icon="💷", layout="wide")
st.title("💷 Affordability")

start, end, type_codes, counties = sidebar_filters()

wc, p = where_clause(start, end, type_codes, counties)

q = f"""
WITH base AS (
  SELECT price FROM {fqtn()}
  WHERE {wc}
)
SELECT
  PERCENTILE_CONT(0.10) WITHIN GROUP (ORDER BY price) AS p10,
  PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY price) AS p25,
  PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY price) AS p50,
  PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY price) AS p75,
  PERCENTILE_CONT(0.90) WITHIN GROUP (ORDER BY price) AS p90
FROM base
"""
with get_engine().begin() as conn:
    pct = pd.read_sql(text(q), conn, params=p).iloc[0].to_dict()

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("P10", f"£{pct['p10']:,.0f}" if pct['p10'] else "—")
c2.metric("P25", f"£{pct['p25']:,.0f}" if pct['p25'] else "—")
c3.metric("Median", f"£{pct['p50']:,.0f}" if pct['p50'] else "—")
c4.metric("P75", f"£{pct['p75']:,.0f}" if pct['p75'] else "—")
c5.metric("P90", f"£{pct['p90']:,.0f}" if pct['p90'] else "—")

st.markdown("---")

# Pulled sample to avoid plotting millions of points
sample_q = f"""
SELECT price FROM {fqtn()}
WHERE {wc}
LIMIT 100000
"""
with get_engine().begin() as conn:
    prices = pd.read_sql(text(sample_q), conn, params=p)

if prices.empty:
    st.warning("No data for selected filters.")
else:
    fig = px.histogram(prices, x="price", nbins=60,
                       title="Price Distribution (sampled)",
                       labels={"price":"Price (£)"})
    fig.update_layout(bargap=0.02)
    st.plotly_chart(fig, use_container_width=True)