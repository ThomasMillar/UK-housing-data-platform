# UK Housing Data Platform

An end-to-end data engineering project built using UK residential transaction data from  
HM Land Registry Price Paid Data.

---

## 🎯 Project Goal

To design and build a full-stack housing market data platform including:

- Automated ingestion of transaction data
- Data cleaning and transformation
- Database modelling
- REST API development
- Interactive visualisation

The goal is to simulate a production-style data engineering workflow from raw public data to a user-facing application.

---

## 🏗️ Architecture Overview

The platform follows a layered data engineering approach:

Raw Data → Processed Data → Database → API → Frontend

- **Raw layer**: Source CSV files downloaded from official government datasets  
- **Processing layer**: Data cleaning, schema enforcement, partitioning  
- **Database layer**: Structured PostgreSQL schema  
- **API layer**: FastAPI endpoints for data access  
- **Frontend layer**: Interactive dashboards  

---

## 📦 Data Source

The dataset is published by HM Land Registry via:

- GOV.UK  
- data.gov.uk  

The data contains residential property transaction records across England and Wales.

---

## 📥 Data Ingestion Strategy

### Challenges

During development, several real-world ingestion challenges were encountered:

- The linked-data API returns metadata rather than raw CSV files.
- Direct S3 access returned restricted (`403`) responses.
- Some years are published as full files (`pp-YYYY.csv`) while others are split into part files (`pp-YYYY-partX.csv`).
- Dataset pages contain multiple resource types requiring filtering logic.

### Solution

The ingestion pipeline:

- Scrapes official dataset pages for available CSV files.
- Filters and downloads only `pp-YYYY-partX.csv` files.
- Skips files already downloaded (idempotent behaviour).
- Stores files in a structured `/data/raw` layer.
- Supports incremental loading for future updates.

This ensures reliable, repeatable data ingestion aligned with production-style data engineering practices.

---

## 🛠️ Tech Stack (Planned)

- Python  
- PostgreSQL  
- FastAPI  
- Pandas  
- Streamlit (or React)  
