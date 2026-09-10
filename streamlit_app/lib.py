import os

import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL


load_dotenv()

PROPERTY_TYPE_MAP = {
    "D": "Detached",
    "S": "Semi-Detached",
    "T": "Terraced",
    "F": "Flats/Maisonettes",
    "O": "Other",
}

ANALYTICS_TABLE = "serving.transactions_explorer"
LOCATION_TABLE = "serving.location_dim"
META_TABLE = "serving.dataset_meta"


def get_config_value(secret_name, app_env_name, local_env_name, default=None):
    app_value = os.getenv(app_env_name)
    if app_value:
        return app_value

    local_value = os.getenv(local_env_name)
    if local_value:
        return local_value

    try:
        if "database" in st.secrets:
            value = st.secrets["database"].get(secret_name)
            if value:
                return value
    except Exception:
        pass

    return default


@st.cache_resource
def get_engine():
    host = get_config_value("host", "APP_POSTGRES_HOST", "POSTGRES_HOST", "localhost")
    port = get_config_value("port", "APP_POSTGRES_PORT", "POSTGRES_PORT", "5432")
    database = get_config_value("database", "APP_POSTGRES_DB", "POSTGRES_DB", "housing_db")
    user = get_config_value("user", "APP_POSTGRES_USER", "POSTGRES_USER", "housing_user")
    password = get_config_value("password", "APP_POSTGRES_PASSWORD", "POSTGRES_PASSWORD")
    sslmode = get_config_value("sslmode", "APP_POSTGRES_SSLMODE", "POSTGRES_SSLMODE")

    if not password:
        raise RuntimeError("PostgreSQL password is not configured.")

    url = URL.create(
        "postgresql+psycopg2",
        username=user,
        password=password,
        host=host,
        port=int(port),
        database=database,
    )

    connect_args = {"sslmode": sslmode} if sslmode else {}

    return create_engine(
        url,
        pool_pre_ping=True,
        pool_size=3,
        max_overflow=2,
        connect_args=connect_args,
    )


def from_clause():
    return f"{ANALYTICS_TABLE} t"


def fqtn():
    return from_clause()


@st.cache_data(show_spinner=False, ttl=3600)
def load_dataset_meta():
    query = f"""
        SELECT min_date, max_date, total_rows, sample_rows
        FROM {META_TABLE}
        WHERE id = 1
    """

    with get_engine().begin() as conn:
        return pd.read_sql(query, conn).iloc[0].to_dict()


def sample_weight():
    meta = load_dataset_meta()
    return float(meta["total_rows"]) / float(meta["sample_rows"])


def scale_count(value):
    if value is None or pd.isna(value):
        return 0
    return round(float(value) * sample_weight())


def scale_value(value):
    if value is None or pd.isna(value):
        return None
    return round(float(value) * sample_weight())


@st.cache_data(show_spinner=False, ttl=3600)
def load_date_range():
    meta = load_dataset_meta()
    return {"min_d": meta["min_date"], "max_d": meta["max_date"]}


@st.cache_data(show_spinner=False, ttl=3600)
def load_filter_values():
    county_query = f"""
        SELECT DISTINCT county
        FROM {LOCATION_TABLE}
        WHERE county IS NOT NULL
        ORDER BY county
    """

    with get_engine().begin() as conn:
        counties = pd.read_sql(county_query, conn)["county"].dropna().tolist()

    return list(PROPERTY_TYPE_MAP.keys()), counties


def map_property_type(code):
    return PROPERTY_TYPE_MAP.get(code, code)


def sidebar_filters():
    date_range = load_date_range()
    min_date = pd.to_datetime(date_range["min_d"]).date()
    max_date = pd.to_datetime(date_range["max_d"]).date()

    st.sidebar.markdown("### Filters")

    selected_dates = st.sidebar.date_input(
        "Date range",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
        format="YYYY-MM-DD",
    )

    if isinstance(selected_dates, (tuple, list)) and len(selected_dates) == 2:
        start, end = selected_dates
    else:
        start = end = selected_dates

    types, counties = load_filter_values()
    readable_types = [map_property_type(code) for code in types]

    selected_types = st.sidebar.multiselect("Property type", readable_types)
    selected_counties = st.sidebar.multiselect("County", counties)

    type_codes = [
        code for code, label in PROPERTY_TYPE_MAP.items()
        if label in selected_types
    ]

    st.sidebar.caption(
        "Interactive analytics use a deterministic ~2% sample for responsive filtering. "
        "Counts and total values are scaled estimates."
    )

    return start, end, type_codes, selected_counties


def where_clause(start, end, type_codes, counties):
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

    return " AND ".join(clauses), params


@st.cache_data(show_spinner=True, ttl=1800)
def load_kpis(start, end, type_codes, counties):
    wc, params = where_clause(start, end, type_codes, counties)

    query = f"""
        SELECT
            COUNT(*)::BIGINT AS sample_n,
            PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY t.price) AS median_price,
            AVG(t.price) AS avg_price,
            SUM(t.price)::BIGINT AS sample_total_value
        FROM {from_clause()}
        WHERE {wc}
    """

    with get_engine().begin() as conn:
        result = pd.read_sql(text(query), conn, params=params).iloc[0].to_dict()

    result["n_transactions"] = scale_count(result.pop("sample_n"))
    result["total_value"] = scale_value(result.pop("sample_total_value"))
    return result


@st.cache_data(show_spinner=True, ttl=1800)
def load_time_series(start, end, type_codes, counties, freq="M"):
    wc, params = where_clause(start, end, type_codes, counties)
    date_trunc = {"D": "day", "M": "month", "Q": "quarter", "Y": "year"}[freq]

    query = f"""
        SELECT
            date_trunc('{date_trunc}', t.transfer_date)::date AS period,
            PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY t.price) AS median_price,
            AVG(t.price) AS avg_price,
            COUNT(*)::BIGINT AS sample_n
        FROM {from_clause()}
        WHERE {wc}
        GROUP BY 1
        ORDER BY 1
    """

    with get_engine().begin() as conn:
        df = pd.read_sql(text(query), conn, params=params)

    df["period"] = pd.to_datetime(df["period"])
    df["n_transactions"] = (df.pop("sample_n") * sample_weight()).round().astype("int64")
    return df


def add_monthly_metrics(df):
    df = df.sort_values("period").copy()
    df["median_price_yoy_pct"] = df["median_price"].pct_change(periods=12, fill_method=None) * 100
    df["transactions_yoy_pct"] = df["n_transactions"].pct_change(periods=12, fill_method=None) * 100
    df["median_price_12m_avg"] = df["median_price"].rolling(window=12, min_periods=12).mean()
    df["transactions_12m"] = df["n_transactions"].rolling(window=12, min_periods=12).sum()
    return df


@st.cache_data(show_spinner=True, ttl=1800)
def load_property_mix(start, end, type_codes, counties):
    wc, params = where_clause(start, end, type_codes, counties)

    query = f"""
        SELECT
            t.property_type,
            COUNT(*)::BIGINT AS sample_n,
            PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY t.price) AS median_price,
            AVG(t.price) AS avg_price
        FROM {from_clause()}
        WHERE {wc}
        GROUP BY t.property_type
        ORDER BY sample_n DESC
    """

    with get_engine().begin() as conn:
        df = pd.read_sql(text(query), conn, params=params)

    df["n"] = (df.pop("sample_n") * sample_weight()).round().astype("int64")
    df["Property"] = df["property_type"].map(map_property_type)
    return df


@st.cache_data(show_spinner=True, ttl=1800)
def load_build_status_summary(start, end, type_codes, counties):
    wc, params = where_clause(start, end, type_codes, counties)

    query = f"""
        SELECT
            t.old_new,
            COUNT(*)::BIGINT AS sample_n,
            PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY t.price) AS median_price
        FROM {from_clause()}
        WHERE {wc}
          AND t.old_new IN ('Y', 'N')
        GROUP BY t.old_new
        ORDER BY sample_n DESC
    """

    with get_engine().begin() as conn:
        df = pd.read_sql(text(query), conn, params=params)

    df["n"] = (df.pop("sample_n") * sample_weight()).round().astype("int64")
    df["build_status"] = df["old_new"].map({
        "Y": "New build",
        "N": "Existing property",
    })

    return df


@st.cache_data(show_spinner=True, ttl=1800)
def load_tenure_summary(start, end, type_codes, counties):
    wc, params = where_clause(start, end, type_codes, counties)

    query = f"""
        SELECT
            t.duration,
            COUNT(*)::BIGINT AS sample_n,
            PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY t.price) AS median_price
        FROM {from_clause()}
        WHERE {wc}
          AND t.duration IN ('F', 'L')
        GROUP BY t.duration
        ORDER BY sample_n DESC
    """

    with get_engine().begin() as conn:
        df = pd.read_sql(text(query), conn, params=params)

    df["n"] = (df.pop("sample_n") * sample_weight()).round().astype("int64")
    df["tenure"] = df["duration"].map({
        "F": "Freehold",
        "L": "Leasehold",
    })

    return df


@st.cache_data(show_spinner=True, ttl=1800)
def load_geo_summary(start, end, type_codes, counties, geo="county"):
    geo_columns = {
        "county": "t.county",
        "district": "t.district",
        "town_city": "t.town_city",
    }

    geo_column = geo_columns.get(geo, "t.county")
    wc, params = where_clause(start, end, type_codes, counties)

    query = f"""
        SELECT
            {geo_column} AS region,
            COUNT(*)::BIGINT AS sample_n,
            PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY t.price) AS median_price,
            AVG(t.price) AS avg_price
        FROM {from_clause()}
        WHERE {wc}
          AND {geo_column} IS NOT NULL
        GROUP BY {geo_column}
        ORDER BY sample_n DESC
    """

    with get_engine().begin() as conn:
        df = pd.read_sql(text(query), conn, params=params)

    df["n"] = (df.pop("sample_n") * sample_weight()).round().astype("int64")
    return df


def load_geo_movers(
    start,
    end,
    type_codes,
    counties,
    geo="county",
    min_transactions=100,
):
    selected_start = pd.Timestamp(start)
    selected_end = pd.Timestamp(end)

    current_start = selected_end - pd.DateOffset(years=1) + pd.Timedelta(days=1)
    previous_end = current_start - pd.Timedelta(days=1)
    previous_start = previous_end - pd.DateOffset(years=1) + pd.Timedelta(days=1)

    if selected_start > previous_start:
        return pd.DataFrame()

    current = load_geo_summary(
        current_start.date(), selected_end.date(), type_codes, counties, geo
    )
    previous = load_geo_summary(
        previous_start.date(), previous_end.date(), type_codes, counties, geo
    )

    current = current.rename(columns={
        "n": "current_n",
        "median_price": "current_median",
    })
    previous = previous.rename(columns={
        "n": "previous_n",
        "median_price": "previous_median",
    })

    movers = current[["region", "current_n", "current_median"]].merge(
        previous[["region", "previous_n", "previous_median"]],
        on="region",
        how="inner",
    )

    movers = movers[
        (movers["current_n"] >= min_transactions)
        & (movers["previous_n"] >= min_transactions)
    ].copy()

    movers["price_change_pct"] = (
        (movers["current_median"] - movers["previous_median"])
        / movers["previous_median"]
        * 100
    )

    return movers


def format_currency(value):
    if value is None or pd.isna(value):
        return "—"

    value = float(value)

    if abs(value) >= 1_000_000:
        return f"£{value / 1_000_000:.2f}M"

    return f"£{value:,.0f}"


def format_number(value):
    if value is None or pd.isna(value):
        return "—"

    value = float(value)

    if abs(value) >= 1_000_000:
        return f"{value / 1_000_000:.1f}M"

    if abs(value) >= 1_000:
        return f"{value / 1_000:.1f}K"

    return f"{value:,.0f}"


def pct_change(old_value, new_value):
    if old_value is None or new_value is None:
        return None

    if pd.isna(old_value) or pd.isna(new_value) or old_value == 0:
        return None

    return ((new_value - old_value) / old_value) * 100


def style_figure(fig, height=450):
    fig.update_layout(
        height=height,
        margin=dict(l=20, r=20, t=60, b=20),
        legend_title_text="",
    )

    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(gridcolor="rgba(0,0,0,0.08)")
    return fig
