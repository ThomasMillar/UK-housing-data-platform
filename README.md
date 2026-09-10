# UK Housing Data Platform

An end-to-end data engineering and analytics project built using HM Land Registry Price Paid Data for England and Wales.

The aim of this project was to build more than a dashboard. I wanted to work through the full data process: downloading public data, loading and cleaning it, modelling it in PostgreSQL, exposing it through an API, and building an interactive dashboard on top.

**Live dashboard:** https://uk-housing-data-platform.streamlit.app/

## What the project covers

The platform processes residential property transactions from **2019 to 2025**, with just over **7 million cleaned transaction records** in the full dataset.

The main parts are:

- automated download of HM Land Registry CSV files
- incremental ingestion into PostgreSQL
- cleaning and transformation into a curated dataset
- SQL views / serving tables for analytics
- a FastAPI REST API
- a multi-page Streamlit dashboard
- Docker Compose for the local environment
- Supabase PostgreSQL for the deployed serving layer

## Architecture

```text
HM Land Registry Price Paid Data
            |
            v
Python downloader
            |
            v
data/raw CSV files
            |
            v
master_data.price_paid
            |
            v
housing_data.transactions
            |
            v
Analytics / serving layer
       /             \
      v               v
 FastAPI           Streamlit
                     |
                     v
              Streamlit Cloud
```

Locally, PostgreSQL, pgAdmin, the API and Streamlit can be run with Docker Compose.

For the public dashboard, the serving layer is hosted in Supabase and Streamlit connects using a read-only database role.

## 1. Downloading the data

`scripts/download_monthly_data.py` handles downloading the source files.

One challenge with the Price Paid Data is that the available files are not always presented in exactly the same format. Some years have a complete yearly file while others may be split into parts.

The downloader checks the HM Land Registry dataset page, finds the relevant CSV files for the selected year range and downloads them into:

```text
data/raw/
```

Existing files are skipped so the same data is not downloaded every time the pipeline runs.

The year range is controlled through environment variables:

```env
START_YEAR=2019
END_YEAR=2025
```

Raw CSV files are excluded from Git because they are large and can always be downloaded again from the source.

## 2. Ingestion

`scripts/load_price_paid.py` loads the downloaded files into PostgreSQL.

The raw Land Registry structure is kept in:

```text
master_data.price_paid
```

The loader reads large CSV files in chunks rather than trying to load the whole file into memory at once.

I also created an ingestion log so previously processed files can be skipped. This makes the process incremental and means restarting the pipeline does not automatically reload everything.

Transactions are loaded using an upsert approach, so an existing transaction can be updated rather than duplicated.

## 3. Cleaning and transformation

`scripts/create_tables.py` moves the data from the raw ingestion layer into the curated model:

```text
housing_data.transactions
```

This layer is used to keep the cleaned transaction data separate from the original source table.

The pipeline uses the transaction ID as the key and tracks changes using timestamps. New or changed records can therefore be processed without rebuilding the entire dataset every time.

Materialized views are also refreshed after the main data load so reporting data stays in sync.

This gives the database a simple separation between:

```text
master_data  -> raw/source data
housing_data -> cleaned and curated data
serving      -> data prepared for applications
```

## 4. Serving layer and performance

The full curated dataset contains **7,014,855 non-deleted transactions**.

The cloud database also contains a smaller serving table used by the public dashboard:

```text
serving.transactions_explorer
```

This is a deterministic sample of roughly **2% of the full dataset**. The same transaction will always either be included or excluded because the sample is based on a hash of the transaction ID.

I introduced this after testing the dashboard against the full dataset. Queries such as percentiles, medians and multiple interactive filters were too slow for a small public cloud deployment.

The full dataset is still retained in the serving layer, while the interactive dashboard uses the sample for faster filtering.

Counts and total values shown in the dashboard are scaled estimates. Measures such as median price, average price and percentiles are calculated from the sample and should therefore be treated as estimates.

This was a deliberate trade-off between query speed, hosting cost and analytical detail.

## 5. FastAPI

The project includes a FastAPI service in:

```text
api/main.py
```

The API provides another way to access the curated data and demonstrates how the database can be separated from applications that consume it.

Example endpoints include:

```text
GET /trends/monthly-prices
GET /geo/county
GET /geo/district
GET /property-mix
GET /stats/overview
GET /transactions
```

The transaction endpoint supports filters such as date, county, district, town, property type and price range, together with pagination.

There is also an admin endpoint for refreshing materialized views. It is protected using an API key rather than being publicly available without authentication.

FastAPI automatically provides interactive API documentation at:

```text
http://localhost:8000/docs
```

## 6. Streamlit dashboard

The dashboard is built as a multi-page Streamlit application.

It includes:

- Overview
- Price Trends
- Geography
- Property Mix
- Price Distribution
- COVID-Era Analysis
- Data Explorer

Users can filter the dashboard by date, property type and county.

The Data Explorer also includes pagination so records can be browsed without loading the full result set into the browser.

The deployed app connects to Supabase using a dedicated read-only PostgreSQL login. Database credentials are stored in Streamlit's secret management rather than in the repository.

## Running locally

Create a local `.env` file with the required PostgreSQL settings, then start the stack:

```bash
docker compose up -d --build
```

The main services are:

```text
PostgreSQL   database
pgAdmin      database management
FastAPI      backend API
Streamlit    analytics dashboard
```

To run the downloader manually:

```bash
python scripts/download_monthly_data.py
```

To run the loader manually:

```bash
python scripts/load_price_paid.py
```

The API documentation is available at:

```text
http://localhost:8000/docs
```

The Streamlit dashboard is available at:

```text
http://localhost:8501
```

## Project structure

```text
UK-housing-data-platform/
├── api/                 # FastAPI application
├── db/                  # Database setup
├── scripts/             # Download, ingestion and transformation scripts
├── streamlit_app/       # Streamlit dashboard
│   ├── Home.py
│   ├── lib.py
│   └── pages/
├── docker-compose.yml
└── README.md
```

## Tech stack

**Python, PostgreSQL, Pandas, SQLAlchemy, FastAPI, Streamlit, Plotly, Docker, Supabase and pgAdmin**

## What I learned

The main thing I wanted from this project was experience working across the full data lifecycle rather than only analysing an already prepared dataset.

It gave me practical experience with large CSV ingestion, incremental loads, database modelling, SQL performance, API development, application deployment and handling the difference between a local development database and a smaller public cloud environment.

One of the most useful parts was seeing how design decisions change as the amount of data grows. Queries that are simple on a small dataset can become expensive across millions of rows, which led me to introduce indexes, caching and a separate serving layer for the public dashboard.
