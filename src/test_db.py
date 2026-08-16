import os

import psycopg2
from dotenv import load_dotenv

load_dotenv()

database_url = os.getenv("DATABASE_URL")

if not database_url:
    raise ValueError("DATABASE_URL is missing from .env")

connection = psycopg2.connect(database_url)

cursor = connection.cursor()
cursor.execute("SELECT version();")

version = cursor.fetchone()[0]

print("PostgreSQL connection successful!")
print(version)

cursor.close()
connection.close()
