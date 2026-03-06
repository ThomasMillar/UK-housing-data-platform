import streamlit as st
import plotly.express as px
from lib import sidebar_filters, load_geo_summary

st.set_page_config(page_title="Geography - UK Housing", page_icon="🗺️", layout="wide")
st.title("🗺️ Geography")

start, end, type_codes, counties = sidebar_filters()

geo = st.radio("Geography", ["county", "district", "town_city"], horizontal=True)
df = load_geo_summary(start, end, type_codes, counties, geo=geo)

if df.empty:
    st.warning("No data for selected filters.")
else:
    c1, c2 = st.columns(2)

    topn = st.slider("Top N regions by transactions", 5, 50, 20)
    top_df = df.head(topn)

    fig1 = px.bar(top_df.sort_values("n", ascending=True),
                  x="n", y="region", orientation="h",
                  title=f"Top {topn} {geo.replace('_',' ').title()} by Transactions",
                  labels={"n":"Transactions","region":"Region"})
    c1.plotly_chart(fig1, use_container_width=True)

    fig2 = px.bar(top_df.sort_values("median_price", ascending=True),
                  x="median_price", y="region", orientation="h",
                  title=f"Top {topn} {geo.replace('_',' ').title()} by Median Price",
                  labels={"median_price":"Median Price (£)","region":"Region"})
    c2.plotly_chart(fig2, use_container_width=True)