import streamlit as st
import requests
import pandas as pd

st.set_page_config(
    page_title="UK Housing Dashboard",
    layout="wide"
)

st.title("UK Housing Market Dashboard")
st.markdown("Interactive analytics powered by FastAPI + PostgreSQL")

# Fetch data from API
@st.cache_data
def load_data():
    try:
        response = requests.get("http://127.0.0.1:8000/monthly-average-prices")
        response.raise_for_status()
        
        df = pd.DataFrame(response.json())
        
        df["month"] = pd.to_datetime(df["month"])
        df["year"] = df["month"].dt.year
        
        # Format month for display
        df["month_label"] = df["month"].dt.strftime("%B %Y")
        
        # Round prices to 2 decimal places
        df["avg_price"] = df["avg_price"].round(2)

        return df

    except Exception:
        st.error("API is not running. Please start FastAPI server.")
        st.stop()

df = load_data()

# Sidebar filters
st.sidebar.header("Filters")

selected_years = st.sidebar.multiselect(
    "Select Year(s)",
    options=sorted(df["year"].unique()),
    default=sorted(df["year"].unique())
)

filtered_df = df[df["year"].isin(selected_years)]

# KPI Section
col1, col2, col3 = st.columns(3)

col1.metric(
    "Average Price (Overall)",
    f"£{filtered_df['avg_price'].mean():,.2f}"
)

col2.metric(
    "Highest Monthly Avg",
    f"£{filtered_df['avg_price'].max():,.2f}"
)

col3.metric(
    "Lowest Monthly Avg",
    f"£{filtered_df['avg_price'].min():,.2f}"
)

st.divider()

# Line Chart
st.subheader("Monthly Average Prices")

st.line_chart(
    filtered_df.set_index("month")["avg_price"]
)

st.divider()

# Data Table
st.subheader("Monthly Average Prices")

chart_df = filtered_df.copy()
#chart_df = chart_df.set_index("month_label")

st.dataframe(filtered_df, use_container_width=True)