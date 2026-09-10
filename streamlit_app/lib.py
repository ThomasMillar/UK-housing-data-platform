import os

import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from sqlalchemy import create_engine, text


# CONFIGURATION

# Load local .env values when running the project locally.
load_dotenv()


# DATABASE CONNECTION

def get_config_value(secret_name, env_name, default=None):
    """
    Get configuration from environment variables first.

    Local Docker:
        Uses values from .env / Docker environment variables.

    Streamlit Cloud:
        Falls back to st.secrets when no environment variable exists.
    """

    # Local Docker / environment variables take priority.
    env_value = os.getenv(env_name)

    if env_value:
        return env_value

    # Only try Streamlit secrets when no environment variable exists.
    try:
        if "database" in st.secrets:
            value = st.secrets["database"].get(secret_name)

            if value:
                return value

    except Exception:
        # No Streamlit secrets configured locally.
        pass

    return default


def get_engine():
    """
    Create a SQLAlchemy PostgreSQL engine.

    Local development:
        Values come from .env / Docker environment variables.

    Streamlit Cloud:
        Values come from st.secrets.
    """

    host = get_config_value(
        "host",
        "POSTGRES_HOST",
        "localhost",
    )

    port = get_config_value(
        "port",
        "POSTGRES_PORT",
        "5432",
    )

    db = get_config_value(
        "database",
        "POSTGRES_DB",
        "housing_db",
    )

    user = get_config_value(
        "user",
        "POSTGRES_USER",
        "housing_user",
    )

    password = get_config_value(
        "password",
        "POSTGRES_PASSWORD",
        None,
    )

    if not password:
        raise RuntimeError(
            "PostgreSQL password has not been configured. "
            "Set POSTGRES_PASSWORD locally or configure "
            "database.password in Streamlit secrets."
        )

    connection_string = (
        f"postgresql+psycopg2://"
        f"{user}:{password}@{host}:{port}/{db}"
    )

    return create_engine(
        connection_string,
        pool_pre_ping=True,
    )


def fqtn():
    """
    Return the fully-qualified PostgreSQL table name.
    """

    schema = os.getenv(
        "SCHEMA",
        "housing_data",
    )

    table = os.getenv(
        "TABLE",
        "transactions",
    )

    return f"{schema}.{table}"


# SHARED DATA LOADERS

@st.cache_data(show_spinner=False, ttl=600)
def load_date_range():
    """
    Get the earliest and latest transaction dates.
    """

    sql = f"""
        SELECT
            MIN(transfer_date) AS min_d,
            MAX(transfer_date) AS max_d
        FROM {fqtn()}
    """

    with get_engine().begin() as conn:
        return pd.read_sql(
            sql,
            conn,
        ).iloc[0].to_dict()


@st.cache_data(show_spinner=False, ttl=600)
def load_filter_values():
    """
    Load values used by the dashboard sidebar filters.
    """

    sql = f"""
        SELECT DISTINCT property_type
        FROM {fqtn()}
        WHERE property_type IS NOT NULL
    """

    sql_region = f"""
        SELECT DISTINCT county
        FROM {fqtn()}
        WHERE county IS NOT NULL
        ORDER BY 1
    """

    with get_engine().begin() as conn:
        types = (
            pd.read_sql(
                sql,
                conn,
            )["property_type"]
            .dropna()
            .sort_values()
            .tolist()
        )

        counties = (
            pd.read_sql(
                sql_region,
                conn,
            )["county"]
            .dropna()
            .tolist()
        )

    return types, counties


# PROPERTY TYPE HELPERS

PROPERTY_TYPE_MAP = {
    "D": "Detached",
    "S": "Semi-Detached",
    "T": "Terraced",
    "F": "Flats/Maisonettes",
    "O": "Other",
}


def map_property_type(code):
    """
    Convert HM Land Registry property type codes
    into readable labels.
    """

    return PROPERTY_TYPE_MAP.get(
        code,
        code,
    )


# SIDEBAR FILTERS

def sidebar_filters():
    """
    Display shared dashboard filters and return
    the selected values.
    """

    dr = load_date_range()

    st.sidebar.markdown("### Filters")

    start, end = st.sidebar.date_input(
        "Date range",
        value=(
            pd.to_datetime(dr["min_d"]).date(),
            pd.to_datetime(dr["max_d"]).date(),
        ),
        min_value=(
            pd.to_datetime(dr["min_d"]).date()
            if dr["min_d"]
            else None
        ),
        max_value=(
            pd.to_datetime(dr["max_d"]).date()
            if dr["max_d"]
            else None
        ),
        format="YYYY-MM-DD",
    )

    types, counties = load_filter_values()

    readable_types = [
        map_property_type(t)
        for t in types
    ]

    type_sel = st.sidebar.multiselect(
        "Property type",
        readable_types,
    )

    county_sel = st.sidebar.multiselect(
        "County",
        counties,
    )

    # Convert readable labels back to HM Land Registry codes.
    type_codes = [
        code
        for code, label in PROPERTY_TYPE_MAP.items()
        if label in type_sel
    ]

    return (
        start,
        end,
        type_codes,
        county_sel,
    )


# SQL FILTER HELPERS

def where_clause(
    start,
    end,
    type_codes,
    counties,
):
    """
    Create a shared WHERE clause and parameter dictionary.
    """

    clauses = [
        "transfer_date BETWEEN :start AND :end",
        "record_status <> 'D'",
    ]

    params = {
        "start": pd.to_datetime(start),
        "end": pd.to_datetime(end),
    }

    if type_codes:
        clauses.append(
            "property_type = ANY(:pt)"
        )

        params["pt"] = type_codes

    if counties:
        clauses.append(
            "county = ANY(:cty)"
        )

        params["cty"] = counties

    return (
        " AND ".join(clauses),
        params,
    )


# OVERVIEW / KPI DATA

@st.cache_data(show_spinner=True, ttl=600)
def load_kpis(
    start,
    end,
    type_codes,
    counties,
):
    """
    Load headline dashboard KPIs.
    """

    wc, p = where_clause(
        start,
        end,
        type_codes,
        counties,
    )

    q = f"""
        WITH base AS (
            SELECT
                price,
                transfer_date
            FROM {fqtn()}
            WHERE {wc}
        )

        SELECT
            COUNT(*)::BIGINT AS n_transactions,

            PERCENTILE_CONT(0.5)
                WITHIN GROUP (
                    ORDER BY price
                ) AS median_price,

            AVG(price) AS avg_price,

            SUM(price)::BIGINT AS total_value

        FROM base
    """

    with get_engine().begin() as conn:
        return pd.read_sql(
            text(q),
            conn,
            params=p,
        ).iloc[0].to_dict()


# TIME SERIES

@st.cache_data(show_spinner=True, ttl=600)
def load_time_series(
    start,
    end,
    type_codes,
    counties,
    freq="M",
):
    """
    Load price and transaction volume time series.

    freq:
        D = day
        M = month
        Q = quarter
        Y = year
    """

    wc, p = where_clause(
        start,
        end,
        type_codes,
        counties,
    )

    date_trunc = {
        "D": "day",
        "M": "month",
        "Q": "quarter",
        "Y": "year",
    }[freq]

    q = f"""
        SELECT
            date_trunc(
                '{date_trunc}',
                transfer_date
            )::date AS period,

            PERCENTILE_CONT(0.5)
                WITHIN GROUP (
                    ORDER BY price
                ) AS median_price,

            AVG(price) AS avg_price,

            COUNT(*)::BIGINT AS n_transactions

        FROM {fqtn()}

        WHERE {wc}

        GROUP BY 1

        ORDER BY 1
    """

    with get_engine().begin() as conn:
        return pd.read_sql(
            text(q),
            conn,
            params=p,
        )


# PROPERTY MIX

@st.cache_data(show_spinner=True, ttl=600)
def load_property_mix(
    start,
    end,
    type_codes,
    counties,
):
    """
    Load transaction counts and median prices
    by property type.
    """

    wc, p = where_clause(
        start,
        end,
        type_codes,
        counties,
    )

    q = f"""
        SELECT
            property_type,

            COUNT(*)::BIGINT AS n,

            PERCENTILE_CONT(0.5)
                WITHIN GROUP (
                    ORDER BY price
                ) AS median_price

        FROM {fqtn()}

        WHERE {wc}

        GROUP BY 1

        ORDER BY n DESC
    """

    with get_engine().begin() as conn:
        df = pd.read_sql(
            text(q),
            conn,
            params=p,
        )

    df["Property"] = df[
        "property_type"
    ].map(map_property_type)

    return df


# GEOGRAPHY

@st.cache_data(show_spinner=True, ttl=600)
def load_geo_summary(
    start,
    end,
    type_codes,
    counties,
    geo="county",
):
    """
    Load transaction counts and price statistics
    for a selected geographic level.
    """

    wc, p = where_clause(
        start,
        end,
        type_codes,
        counties,
    )

    allowed_geo = {
        "county",
        "district",
        "town_city",
    }

    if geo not in allowed_geo:
        geo = "county"

    q = f"""
        SELECT
            {geo} AS region,

            COUNT(*)::BIGINT AS n,

            PERCENTILE_CONT(0.5)
                WITHIN GROUP (
                    ORDER BY price
                ) AS median_price,

            AVG(price) AS avg_price

        FROM {fqtn()}

        WHERE {wc}

        GROUP BY {geo}

        HAVING {geo} IS NOT NULL

        ORDER BY n DESC
    """

    with get_engine().begin() as conn:
        return pd.read_sql(
            text(q),
            conn,
            params=p,
        )


# PRESENTATION HELPERS

def format_currency(value):
    """
    Format a numeric value as GBP.
    """

    if value is None or pd.isna(value):
        return "—"

    value = float(value)

    if abs(value) >= 1_000_000:
        return f"£{value / 1_000_000:.1f}M"

    if abs(value) >= 1_000:
        return f"£{value / 1_000:,.0f}K"

    return f"£{value:,.0f}"


def format_number(value):
    """
    Format a number using readable compact notation.
    """

    if value is None or pd.isna(value):
        return "—"

    value = float(value)

    if abs(value) >= 1_000_000:
        return f"{value / 1_000_000:.1f}M"

    if abs(value) >= 1_000:
        return f"{value / 1_000:,.1f}K"

    return f"{value:,.0f}"


def pct_change(
    old_value,
    new_value,
):
    """
    Calculate percentage change safely.
    """

    if old_value is None or new_value is None:
        return None

    if pd.isna(old_value) or pd.isna(new_value):
        return None

    if old_value == 0:
        return None

    return (
        (new_value - old_value)
        / old_value
    ) * 100


def insight_change(
    label,
    old_value,
    new_value,
):
    """
    Create a simple natural-language
    percentage-change insight.
    """

    change = pct_change(
        old_value,
        new_value,
    )

    if change is None:
        return None

    direction = (
        "increased"
        if change > 0
        else "decreased"
    )

    return (
        f"{label} {direction} by "
        f"{abs(change):.1f}% over the "
        f"selected period."
    )


def style_figure(
    fig,
    height=450,
):
    """
    Apply consistent styling to Plotly charts.
    """

    fig.update_layout(
        height=height,
        margin=dict(
            l=20,
            r=20,
            t=60,
            b=20,
        ),
        hovermode="x unified",
        legend_title_text="",
    )

    fig.update_xaxes(
        showgrid=False,
    )

    fig.update_yaxes(
        gridcolor="rgba(0,0,0,0.08)",
    )

    return fig