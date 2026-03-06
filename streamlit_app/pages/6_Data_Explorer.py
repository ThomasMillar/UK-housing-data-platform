import streamlit as st
import pandas as pd
from sqlalchemy import text
from lib import sidebar_filters, where_clause, get_engine, fqtn

st.set_page_config(page_title="Data Explorer - UK Housing", page_icon="📋", layout="wide")
st.title("📋 Data Explorer")

start, end, type_codes, counties = sidebar_filters()

# Simple pagination
limit = st.sidebar.number_input("Rows per page", min_value=100, max_value=5000, value=1000, step=100)
page = st.sidebar.number_input("Page", min_value=1, value=1, step=1)
offset = (page - 1) * limit

wc, p = where_clause(start, end, type_codes, counties)

q = f"""
SELECT transaction_id, transfer_date, price, postcode, property_type,
       duration, town_city, district, county, record_status
FROM {fqtn()}
WHERE {wc}
ORDER BY transfer_date DESC
LIMIT :limit OFFSET :offset
"""
p.update({"limit": int(limit), "offset": int(offset)})

with get_engine().begin() as conn:
    df = pd.read_sql(text(q), conn, params=p)

st.dataframe(df, use_container_width=True)

# Export Button
if not df.empty:
    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button("Download CSV", data=csv, file_name="transactions_export.csv", mime="text/csv")