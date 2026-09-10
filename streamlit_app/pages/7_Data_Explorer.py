import math

import pandas as pd
import streamlit as st
from sqlalchemy import text

from lib import get_engine, map_property_type, sidebar_filters


st.set_page_config(
    page_title="Data Explorer - Housing Explorer",
    page_icon="📋",
    layout="wide",
)

st.title("📋 Data Explorer")
st.write(
    "Browse a representative sample of transaction-level records from the "
    "2019–2025 Price Paid Data used by the dashboard."
)

start, end, type_codes, counties = sidebar_filters()

rows_per_page = st.sidebar.selectbox(
    "Rows per page",
    options=[100, 250, 500, 1000],
    index=1,
)

clauses = ["t.transfer_date BETWEEN :start AND :end"]
params = {
    "start": pd.to_datetime(start),
    "end": pd.to_datetime(end),
}

if type_codes:
    clauses.append("t.property_type = ANY(:pt)")
    params["pt"] = type_codes

if counties:
    clauses.append("t.county = ANY(:cty)")
    params["cty"] = counties

wc = " AND ".join(clauses)

count_query = f"""
SELECT COUNT(*)::BIGINT AS total_rows
FROM serving.transactions_explorer t
WHERE {wc}
"""

with get_engine().begin() as conn:
    total_rows = int(
        pd.read_sql(text(count_query), conn, params=params).iloc[0]["total_rows"]
    )

if total_rows == 0:
    st.warning("No records were found for the selected filters.")
    st.stop()

total_pages = max(1, math.ceil(total_rows / rows_per_page))

page = st.sidebar.number_input(
    "Page",
    min_value=1,
    max_value=total_pages,
    value=1,
    step=1,
)

offset = (page - 1) * rows_per_page

query = f"""
SELECT
    transaction_id,
    transfer_date,
    price,
    postcode,
    property_type,
    old_new,
    duration,
    town_city,
    district,
    county
FROM serving.transactions_explorer t
WHERE {wc}
ORDER BY transfer_date DESC, transaction_id
LIMIT :limit
OFFSET :offset
"""

query_params = {
    **params,
    "limit": int(rows_per_page),
    "offset": int(offset),
}

with get_engine().begin() as conn:
    df = pd.read_sql(text(query), conn, params=query_params)

df["property_type"] = df["property_type"].map(map_property_type)
df["old_new"] = df["old_new"].map({
    "Y": "New build",
    "N": "Existing property",
})
df["duration"] = df["duration"].map({
    "F": "Freehold",
    "L": "Leasehold",
})

df = df.rename(columns={
    "transaction_id": "Transaction ID",
    "transfer_date": "Transfer date",
    "price": "Price",
    "postcode": "Postcode",
    "property_type": "Property type",
    "old_new": "Build status",
    "duration": "Tenure",
    "town_city": "Town / City",
    "district": "District",
    "county": "County",
})

start_row = offset + 1
end_row = offset + len(df)

col1, col2, col3 = st.columns(3)
col1.metric("Matching sample records", f"{total_rows:,}")
col2.metric("Page", f"{page:,} of {total_pages:,}")
col3.metric("Rows shown", f"{len(df):,}")

st.caption(
    f"Showing rows {start_row:,}–{end_row:,}. "
    "This explorer uses the same deterministic sample used for interactive dashboard "
    "analytics. The full transaction dataset remains stored in the serving layer."
)

st.dataframe(
    df,
    use_container_width=True,
    hide_index=True,
    column_config={
        "Transfer date": st.column_config.DateColumn(format="DD MMM YYYY"),
        "Price": st.column_config.NumberColumn(format="£%d"),
    },
)

csv = df.to_csv(index=False).encode("utf-8")

st.download_button(
    label="Download current page as CSV",
    data=csv,
    file_name="transactions_export.csv",
    mime="text/csv",
)
