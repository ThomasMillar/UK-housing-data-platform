import os
import pandas as pd
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import streamlit as st

load_dotenv()

def get_engine():
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    db   = os.getenv("POSTGRES_DB", "housing_db")
    user = os.getenv("POSTGRES_USER", "housing_user")
    pwd  = os.getenv("POSTGRES_PASSWORD", "housing_password")
    return create_engine(f"postgresql+psycopg2://{user}:{pwd}@{host}:{port}/{db}")

def fqtn():
    schema = os.getenv("SCHEMA", "housing_data")
    table = os.getenv("TABLE", "transactions")
    return f'{schema}.{table}'

@st.cache_data(show_spinner=False, ttl=600)
def load_date_range():
    sql = f"SELECT MIN(transfer_date) AS min_d, MAX(transfer_date) AS max_d FROM {fqtn()}"
    with get_engine().begin() as conn:
        return pd.read_sql(sql, conn).iloc[0].to_dict()

@st.cache_data(show_spinner=False, ttl=600)
def load_filter_values():
    sql = f"""
    SELECT DISTINCT property_type FROM {fqtn()} WHERE property_type IS NOT NULL
    UNION SELECT DISTINCT NULL AS property_type
    """
    sql_region = f"""
    SELECT DISTINCT county FROM {fqtn()} WHERE county IS NOT NULL
    ORDER BY 1
    """
    with get_engine().begin() as conn:
        types = pd.read_sql(sql, conn)["property_type"].dropna().sort_values().tolist()
        counties = pd.read_sql(sql_region, conn)["county"].dropna().tolist()
    return types, counties

def map_property_type(code):
    return {
        "D": "Detached",
        "S": "Semi-Detached",
        "T": "Terraced",
        "F": "Flats/Maisonettes",
        "O": "Other"
    }.get(code, code)

def sidebar_filters():
    dr = load_date_range()
    st.sidebar.markdown("### Filters")
    start, end = st.sidebar.date_input(
        "Date range",
        value=(pd.to_datetime(dr["min_d"]).date(), pd.to_datetime(dr["max_d"]).date()),
        min_value=pd.to_datetime(dr["min_d"]).date() if dr["min_d"] else None,
        max_value=pd.to_datetime(dr["max_d"]).date() if dr["max_d"] else None,
        format="YYYY-MM-DD"
    )

    types, counties = load_filter_values()
    type_sel = st.sidebar.multiselect("Property type", [map_property_type(t) for t in types])
    county_sel = st.sidebar.multiselect("County", counties)

    # Codes for SQL
    type_codes = [k for k, v in {
        "D": "Detached", "S": "Semi-Detached", "T": "Terraced", "F": "Flats/Maisonettes", "O": "Other"
    }.items() if v in type_sel]

    return start, end, type_codes, county_sel

def where_clause(start, end, type_codes, counties):
    clauses = ["transfer_date BETWEEN :start AND :end", "record_status <> 'D'"]
    params = {"start": pd.to_datetime(start), "end": pd.to_datetime(end)}
    if type_codes:
        clauses.append("property_type = ANY(:pt)")
        params["pt"] = type_codes
    if counties:
        clauses.append("county = ANY(:cty)")
        params["cty"] = counties
    return " AND ".join(clauses), params

@st.cache_data(show_spinner=True, ttl=600)
def load_kpis(start, end, type_codes, counties):
    wc, p = where_clause(start, end, type_codes, counties)
    q = f"""
    WITH base AS (
      SELECT price, transfer_date FROM {fqtn()}
      WHERE {wc}
    )
    SELECT
      COUNT(*)::BIGINT as n_transactions,
      PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY price) AS median_price,
      AVG(price) AS avg_price,
      SUM(price)::BIGINT AS total_value
    FROM base
    """
    with get_engine().begin() as conn:
        return pd.read_sql(text(q), conn, params=p).iloc[0].to_dict()

@st.cache_data(show_spinner=True, ttl=600)
def load_time_series(start, end, type_codes, counties, freq="M"):
    wc, p = where_clause(start, end, type_codes, counties)
    # Group by month by default
    date_trunc = {"D":"day", "M":"month", "Q":"quarter", "Y":"year"}[freq]
    q = f"""
    SELECT date_trunc('{date_trunc}', transfer_date)::date AS period,
           PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY price) AS median_price,
           AVG(price) AS avg_price,
           COUNT(*)::BIGINT AS n_transactions
    FROM {fqtn()}
    WHERE {wc}
    GROUP BY 1
    ORDER BY 1
    """
    with get_engine().begin() as conn:
        return pd.read_sql(text(q), conn, params=p)

@st.cache_data(show_spinner=True, ttl=600)
def load_property_mix(start, end, type_codes, counties):
    wc, p = where_clause(start, end, type_codes, counties)
    q = f"""
    SELECT property_type,
           COUNT(*)::BIGINT AS n,
           PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY price) AS median_price
    FROM {fqtn()}
    WHERE {wc}
    GROUP BY 1
    ORDER BY n DESC
    """
    with get_engine().begin() as conn:
        df = pd.read_sql(text(q), conn, params=p)
    df["Property"] = df["property_type"].map(map_property_type)
    return df

@st.cache_data(show_spinner=True, ttl=600)
def load_geo_summary(start, end, type_codes, counties, geo="county"):
    wc, p = where_clause(start, end, type_codes, counties)
    geo = "county" if geo not in {"county", "district", "town_city"} else geo
    q = f"""
    SELECT {geo} AS region,
           COUNT(*)::BIGINT AS n,
           PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY price) AS median_price,
           AVG(price) AS avg_price
    FROM {fqtn()}
    WHERE {wc}
    GROUP BY {geo}
    HAVING {geo} IS NOT NULL
    ORDER BY n DESC
    """
    with get_engine().begin() as conn:
        return pd.read_sql(text(q), conn, params=p)