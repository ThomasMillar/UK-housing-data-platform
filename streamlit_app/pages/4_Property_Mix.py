import streamlit as st
import plotly.express as px
from lib import sidebar_filters, load_property_mix, map_property_type

st.set_page_config(page_title="Property Mix - UK Housing", page_icon="🏘️", layout="wide")
st.title("🏘️ Property Mix")

start, end, type_codes, counties = sidebar_filters()

df = load_property_mix(start, end, type_codes, counties)

if df.empty:
    st.warning("No data for selected filters.")
else:
    df["Property"] = df["property_type"].map(map_property_type)
    c1, c2 = st.columns(2)

    fig = px.pie(df, names="Property", values="n",
                 title="Transactions by Property Type")
    c1.plotly_chart(fig, use_container_width=True)

    fig2 = px.bar(df.sort_values("median_price", ascending=True),
                  x="median_price", y="Property", orientation="h",
                  labels={"median_price": "Median Price (£)"},
                  title="Median Price by Property Type")
    c2.plotly_chart(fig2, use_container_width=True)