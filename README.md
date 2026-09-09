# UK Housing Data Platform

An end-to-end full stack data engineering and analytics platform built using UK residential transaction data from HM Land Registry Price Paid Data.

This project simulates a production-style data workflow — from raw public datasets to a containerised database, backend API, and interactive dashboard.

---

## 🎯 Project Goal

To design and build a modern data platform that demonstrates:

- Automated ingestion of large public datasets
- Structured database modelling
- Clean transformation and analytics layering
- REST API development
- Containerised infrastructure (Docker)
- Interactive dashboard visualisation
- Separation of ingestion, analytics, and presentation layers

The goal is to replicate how real-world data systems are built in production environments.

---

## 🏗️ Architecture Overview

### The platform follows a layered architecture separating ingestion, transformation, and presentation:
```
PostgreSQL (Docker)
↓
Raw Ingestion Table (~1.9M rows)
↓
Analytics Table (cleaned + engineered features)
↓
Aggregated View (monthly averages)
↓
FastAPI Backend
↓
Streamlit Dashboard / Power BI
```

This separation ensures:

- Reproducibility
- Clear system boundaries
- Performance optimisation
- Production-style data engineering design

---

## 📦 Data Source

Dataset: HM Land Registry – UK Price Paid Data  
Published via GOV.UK and data.gov.uk  

The dataset contains residential property transaction records across England and Wales including:

- Transaction price  
- Transfer date  
- Property type  
- Town / district / county  
- Postcode  

For performance optimisation, selected years (2019–2020) are processed during development.

---

## 📥 Data Ingestion Strategy

### Real-World Challenges Encountered

During development, several ingestion challenges were addressed:

- Linked-data endpoints return metadata rather than raw CSV files.
- Direct S3 access may return restricted (`403`) responses.
- Some years are full CSV files (`pp-YYYY.csv`) while others are split (`pp-YYYY-partX.csv`).
- Dataset pages contain mixed resource formats requiring filtering logic.
- Large file sizes (~500k rows per file).

### Implemented Solution

The ingestion pipeline:

- Downloads selected year-part CSV files
- Stores files in `/data/raw`
- Loads data into PostgreSQL via Python ETL scripts
- Supports incremental ingestion
- Avoids reprocessing existing files

---

## 🗄️ Database Architecture

The database is containerised using Docker and PostgreSQL 15.

### 1️⃣ Raw Ingestion Layer

`price_paid`

- Stores a sample transaction data (~1.9M row)
- Mirrors original dataset schema
- Optimised with indexes

### 2️⃣ Analytics Layer

`price_paid_analytics`

- Removes unnecessary columns
- Engineers additional features:
  - Extracted year
  - Extracted month
- Filters invalid records
- Optimised for reporting

### 3️⃣ Presentation Layer

`monthly_avg_prices` (SQL View)

Pre-aggregated monthly average prices:

```sql
SELECT
    date_trunc('month', transfer_date) AS month,
    AVG(price) AS avg_price
FROM price_paid_analytics
GROUP BY date_trunc('month', transfer_date)
ORDER BY month;
```

This ensures dashboards query only lightweight aggregated data (24 rows instead of millions).

🚀 Backend API (FastAPI)

A REST API exposes curated analytics data.
Example endpoint: GET /monthly-average-prices
```python
Returns:
[
  {
    "month": "2019-01-01",
    "avg_price": 245000
  }
]
```
The API does not expose raw transactional data directly.
It queries the presentation-layer SQL view for performance and architectural separation.

## 📊 Frontend Dashboard
The project includes a Streamlit dashboard that:

- Calls the FastAPI backend
- Renders interactive line charts
- Displays aggregated monthly pricing trends
- Demonstrates full stack integration
- Power BI integration is also supported by connecting either:
- Directly to PostgreSQL
 Or via the REST API

## 🐳 Containerisation (Docker)

PostgreSQL and pgAdmin are fully containerised using Docker Compose.
This ensures:
- Environment reproducibility
- Simplified setup
- Isolation from host machine dependencies
- Production-style infrastructure management

## 🛠️ Tech Stack

- Python
- PostgreSQL
- Docker
- FastAPI
- SQLAlchemy
- Pandas
- Streamlit
- pgAdmin

## ⚙️ How To Run Locally

### 1. Clone Repository
```bash
git clone <repo-url>
cd UK-housing-data-platform
```
### 2. Start Database (Docker)
```bash
docker compose up -d
```
### 3. Load Data
```bash
py scripts/load_price_paid.py
```
### 4. Start API
```bash
py -m uvicorn api.main:app --reload
```
Visit:
http://127.0.0.1:8000/docs

### 5. Start Dashboard
In a new terminal:
```bash
py -m streamlit run dashboard/app.py
```
Visit:
http://localhost:8501

## 📈 Performance

~1.9 million transaction rows ingested
- Monthly aggregation query executes in ~37ms
- Dashboard queries lightweight aggregated view (24 rows)
- Indexed columns ensure efficient filtering

## 🔒 Data Exclusions

The /data/raw folder is excluded from version control via .gitignore to avoid committing large datasets.

## 🔮 Future Improvements

- Parameterised API filters (year, town, property type)
- Automated yearly ingestion pipeline
- CI/CD workflow
- Full Dockerised deployment (API + Dashboard)
- Authentication layer for API
- Cloud deployment (Azure / AWS / GCP)
- Star schema modelling for BI optimisation