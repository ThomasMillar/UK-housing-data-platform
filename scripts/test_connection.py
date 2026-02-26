import psycopg2

conn = psycopg2.connect(
    host="localhost",
    database="housing_db",
    user="housing_user",
    password="housing_password",
    port=5432
)

print("Connection successful!")

conn.close()