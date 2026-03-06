import streamlit as st

st.set_page_config(
    page_title="UK Housing Dashboard",
    page_icon="🏠",
    layout="wide",
)

st.title("🏠 UK Housing Dashboard")
st.markdown(
    """
Welcome! Use the sidebar filters on each page to explore UK Land Registry price paid data:
- **Overview**: KPIs and quick stats  
- **Price Trends**: Median/average over time  
- **Geography**: Hotspots by county/district  
- **Property Mix**: Composition & pricing by type  
- **Affordability**: Percentiles & distribution  
- **Data Explorer**: Tabular view + CSV export
"""
)
st.info("Navigate using the left sidebar **Pages** menu.")