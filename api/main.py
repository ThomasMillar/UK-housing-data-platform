from fastapi import FastAPI, Query, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, text
import pandas as pd
import os
from datetime import date
from typing import List, Optional

# .env config
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
POSTGRES_DB   = os.getenv("POSTGRES_DB", "housing_db")
POSTGRES_USER = os.getenv("POSTGRES_USER", "housing_user")
POSTGRES_PWD  = os.getenv("POSTGRES_PASSWORD", "housing_password")

SCHEMA = os.getenv("SCHEMA", "housing_data")
TABLE  = os.getenv("TABLE", "transactions")

ADMIN_API_KEY = os.getenv("ADMIN_API_KEY")

DATABASE_URL = f"postgresql://{POSTGRES_USER}:{POSTGRES_PWD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"

engine = create_engine(DATABASE_URL, pool_pre_ping=True, pool_size=5, max_overflow=5)

app = FastAPI(title="UK Housing Data API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Helpers

def df_to_records(sql: str, params: dict | None = None):
    with engine.begin() as conn:
        df = pd.read_sql(text(sql), conn, params=params or {})
    for col in df.select_dtypes(include=["datetime64[ns]", "datetime64[ns, UTC]", "datetime64[ns, tzutc]"]).columns:
        df[col] = df[col].dt.date.astype(str)
    if "month" in df.columns and pd.api.types.is_datetime64_any_dtype(df["month"]):
        df["month"] = pd.to_datetime(df["month"]).dt.date.astype(str)
    return df.to_dict(orient="records")

def parse_csv(values: Optional[str]) -> Optional[List[str]]:
    if not values:
        return None
    return [v.strip() for v in values.split(",") if v.strip()]


# Root / Health

@app.get("/")
def root():
    return {"message": "UK Housing Data API running", "schema": SCHEMA, "table": TABLE}


# Trends - Monthly Prices

@app.get("/trends/monthly-prices")
def monthly_prices(
    start: Optional[date] = Query(None, description="Start month (YYYY-MM-DD)"),
    end: Optional[date]   = Query(None, description="End month (YYYY-MM-DD)"),
):
    # View reads from v_monthly_prices
    sql = f"SELECT * FROM {SCHEMA}.v_monthly_prices"
    params = {}
    if start and end:
        sql += " WHERE month BETWEEN :start AND :end"
        params = {"start": start, "end": end}
    sql += " ORDER BY month"
    return df_to_records(sql, params)


# Trends - Monthly Affordability

@app.get("/trends/monthly-affordability")
def monthly_affordability(
    start: Optional[date] = Query(None),
    end: Optional[date]   = Query(None),
):
    sql = f"SELECT * FROM {SCHEMA}.v_monthly_affordability"
    params = {}
    if start and end:
        sql += " WHERE month BETWEEN :start AND :end"
        params = {"start": start, "end": end}
    sql += " ORDER BY month"
    return df_to_records(sql, params)


# Geo summaries

@app.get("/geo/county")
def county_summary(top: Optional[int] = Query(None, ge=1, le=500)):
    sql = f"SELECT * FROM {SCHEMA}.v_county_summary ORDER BY n_transactions DESC"
    if top:
        sql += " LIMIT :top"
        return df_to_records(sql, {"top": top})
    return df_to_records(sql)

@app.get("/geo/district")
def district_summary(top: Optional[int] = Query(None, ge=1, le=500)):
    sql = f"SELECT * FROM {SCHEMA}.v_district_summary ORDER BY n_transactions DESC"
    if top:
        sql += " LIMIT :top"
        return df_to_records(sql, {"top": top})
    return df_to_records(sql)

@app.get("/geo/town")
def town_summary(top: Optional[int] = Query(None, ge=1, le=500)):
    sql = f"SELECT * FROM {SCHEMA}.v_town_summary ORDER BY n_transactions DESC"
    if top:
        sql += " LIMIT :top"
        return df_to_records(sql, {"top": top})
    return df_to_records(sql)


# Property Mix
@app.get("/property-mix")
def property_mix():
    sql = f"SELECT * FROM {SCHEMA}.v_property_mix ORDER BY n_transactions DESC"
    return df_to_records(sql)


# KPIs / Overview

@app.get("/stats/overview")
def stats_overview(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date]   = Query(None),
    counties: Optional[str]    = Query(None, description="Comma separated list"),
    property_types: Optional[str] = Query(None, description="Comma separated e.g. D,S,T,F,O"),
    min_price: Optional[int]   = Query(None),
    max_price: Optional[int]   = Query(None),
):
    conds = ["record_status <> 'D'"]
    params = {}

    if start_date and end_date:
        conds.append("transfer_date BETWEEN :start AND :end")
        params.update({"start": start_date, "end": end_date})
    if counties := parse_csv(counties):
        conds.append("county = ANY(:cty)")
        params["cty"] = counties
    if pts := parse_csv(property_types):
        conds.append("property_type = ANY(:pt)")
        params["pt"] = pts
    if min_price is not None:
        conds.append("price >= :minp")
        params["minp"] = min_price
    if max_price is not None:
        conds.append("price <= :maxp")
        params["maxp"] = max_price

    where = " AND ".join(conds) if conds else "TRUE"
    sql = f"""
    WITH base AS (
        SELECT price FROM {SCHEMA}.{TABLE}
        WHERE {where}
    )
    SELECT
      COUNT(*)::BIGINT AS n_transactions,
      PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY price) AS median_price,
      AVG(price) AS avg_price,
      SUM(price)::BIGINT AS total_value
    FROM {SCHEMA}.{TABLE}
    WHERE {where}
    """
    return df_to_records(sql, params)


# Transactions Explorer (filters + pagination)

@app.get("/transactions")
def transactions(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date]   = Query(None),
    counties: Optional[str]    = Query(None),
    districts: Optional[str]   = Query(None),
    towns: Optional[str]       = Query(None),
    property_types: Optional[str] = Query(None),
    min_price: Optional[int]   = Query(None),
    max_price: Optional[int]   = Query(None),
    limit: int = Query(200, ge=1, le=5000),
    offset: int = Query(0, ge=0),
):
    conds = ["record_status <> 'D'"]
    params = {"limit": limit, "offset": offset}

    if start_date and end_date:
        conds.append("transfer_date BETWEEN :start AND :end")
        params.update({"start": start_date, "end": end_date})
    if counties := parse_csv(counties):
        conds.append("county = ANY(:cty)")
        params["cty"] = counties
    if districts := parse_csv(districts):
        conds.append("district = ANY(:dist)")
        params["dist"] = districts
    if towns := parse_csv(towns):
        conds.append("town_city = ANY(:towns)")
        params["towns"] = towns
    if pts := parse_csv(property_types):
        conds.append("property_type = ANY(:pt)")
        params["pt"] = pts
    if min_price is not None:
        conds.append("price >= :minp")
        params["minp"] = min_price
    if max_price is not None:
        conds.append("price <= :maxp")
        params["maxp"] = max_price

    where = " AND ".join(conds) if conds else "TRUE"
    sql = f"""
    SELECT transaction_id, transfer_date, price, postcode, property_type,
           duration, town_city, district, county, record_status
    FROM {SCHEMA}.{TABLE}
    WHERE {where}
    ORDER BY transfer_date DESC
    LIMIT :limit OFFSET :offset
    """
    return df_to_records(sql, params)


# Refresh all views

@app.post("/admin/refresh-mvs")
def refresh_mvs(x_api_key: Optional[str] = Header(None)):
    if not ADMIN_API_KEY:
        raise HTTPException(status_code=400, detail="ADMIN_API_KEY not configured.")
    if x_api_key != ADMIN_API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")
    sql = "SELECT housing_data.refresh_all_materialized_views(TRUE);"
    _ = df_to_records(sql)
    return {"status": "ok", "message": "Materialized views refresh triggered"}