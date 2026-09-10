import streamlit as st
from lib import load_date_range


st.set_page_config(
    page_title="England & Wales Housing Explorer",
    page_icon="🏠",
    layout="wide",
)

st.title("🏠 England & Wales Housing Explorer")

st.markdown(
    """
    Explore residential property transactions recorded by HM Land Registry
    across England and Wales.

    Use the pages in the sidebar to explore market trends, regional differences,
    property characteristics and transaction price distributions.
    """
)

date_range = load_date_range()

if date_range["min_d"] and date_range["max_d"]:
    st.caption(
        f"Data coverage: {date_range['min_d']:%d %b %Y} "
        f"to {date_range['max_d']:%d %b %Y}"
    )

st.markdown("---")

col1, col2, col3 = st.columns(3)

with col1:
    st.subheader("📈 Market Trends")
    st.write(
        "Track median prices, year-on-year growth and transaction activity "
        "through time."
    )

with col2:
    st.subheader("🗺️ Geography")
    st.write(
        "Compare counties, districts and towns, including the areas seeing "
        "the largest recent price changes."
    )

with col3:
    st.subheader("🏘️ Property Market")
    st.write(
        "Compare property types, new builds, tenure and transaction price bands."
    )

st.markdown("---")
st.subheader("About the data")

st.markdown(
    """
    **Source:** HM Land Registry Price Paid Data  
    **Coverage:** England and Wales  
    **Measure:** Recorded residential property transactions

    Transaction prices are completed sale values. They are not asking prices,
    current valuations or a direct measure of household affordability.
    """
)