import streamlit as st
import pandas as pd

from sqlalchemy import text

from lib import (
    sidebar_filters,
    where_clause,
    get_engine,
    fqtn,
)


st.set_page_config(
    page_title="Data Explorer - Housing Explorer",
    page_icon="📋",
    layout="wide",
)


st.title("📋 Data Explorer")

st.write(
    "Inspect the underlying transaction-level data using the "
    "same filters applied throughout the dashboard."
)


# FILTERS

start, end, type_codes, counties = sidebar_filters()


# PAGINATION

rows_per_page = st.sidebar.number_input(
    "Rows per page",
    min_value=100,
    max_value=5000,
    value=1000,
    step=100,
)


page = st.sidebar.number_input(
    "Page",
    min_value=1,
    value=1,
    step=1,
)


offset = (
    page - 1
) * rows_per_page


# FILTER SQL

wc, params = where_clause(
    start,
    end,
    type_codes,
    counties,
)


# DATA QUERY

query = f"""
SELECT

    transaction_id,
    transfer_date,
    price,
    postcode,
    property_type,
    duration,
    town_city,
    district,
    county,
    record_status

FROM {fqtn()}

WHERE {wc}

ORDER BY transfer_date DESC

LIMIT :limit

OFFSET :offset
"""


params.update(
    {
        "limit": int(rows_per_page),
        "offset": int(offset),
    }
)


with get_engine().begin() as conn:

    df = pd.read_sql(
        text(query),
        conn,
        params=params,
    )


# DISPLAY

if df.empty:

    st.warning(
        "No records were found for the selected filters."
    )

    st.stop()


st.caption(
    f"Showing rows "
    f"{offset + 1:,}–"
    f"{offset + len(df):,}"
)


st.dataframe(
    df,
    use_container_width=True,
    hide_index=True,
)


# DOWNLOAD

csv = df.to_csv(
    index=False
).encode("utf-8")


st.download_button(
    label="Download current page as CSV",
    data=csv,
    file_name="transactions_export.csv",
    mime="text/csv",
)