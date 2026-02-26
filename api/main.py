from fastapi import FastAPI
from sqlalchemy import create_engine
import pandas as pd

app = FastAPI()

engine = create_engine(
    "postgresql://housing_user:housing_password@localhost:5432/housing_db"
)

@app.get("/")
def root():
    return {"message": "UK Housing Data API running"}

@app.get("/monthly-average-prices")
def monthly_average_prices():
    query = "SELECT * FROM monthly_avg_prices;"
    df = pd.read_sql(query, engine)
    return df.to_dict(orient="records")