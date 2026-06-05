import psycopg2
from dotenv import load_dotenv
import os

load_dotenv()

def get_connection():
    return psycopg2.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD")
    )

def insert_listing(data: dict):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO listings (
            source, locality, city_zone, bhk_type,
            rent_monthly, deposit_amount, area_sqft,
            furnishing, near_metro, listing_date,
            listing_url, price_per_sqft
        ) VALUES (
            %(source)s, %(locality)s, %(city_zone)s, %(bhk_type)s,
            %(rent_monthly)s, %(deposit_amount)s, %(area_sqft)s,
            %(furnishing)s, %(near_metro)s, %(listing_date)s,
            %(listing_url)s, %(price_per_sqft)s
        )
    """, data)
    conn.commit()
    cur.close()
    conn.close()

def test_connection():
    try:
        conn = get_connection()
        print("DB connection successful")
        conn.close()
    except Exception as e:
        print(f"Connection failed: {e}")

if __name__ == "__main__":
    test_connection()
