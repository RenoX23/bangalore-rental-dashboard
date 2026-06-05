import pandas as pd
import psycopg2
import os
import re
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from db_utils import get_connection
from dotenv import load_dotenv
load_dotenv()

ZONE_MAP = {
    "whitefield": "East", "marathahalli": "East", "sarjapur": "East",
    "bellandur": "East", "kr puram": "East", "kr puram": "East",
    "koramangala": "South", "hsr layout": "South", "btm layout": "South",
    "jp nagar": "South", "jayanagar": "South", "electronic city": "South",
    "bannerghatta": "South", "bommanahalli": "South",
    "indiranagar": "Central", "domlur": "Central", "richmond": "Central",
    "hebbal": "North", "yelahanka": "North", "sahakara nagar": "North",
    "rajajinagar": "West", "vijayanagar": "West", "malleshwaram": "West",
}

def get_zone(locality: str) -> str:
    loc = locality.lower()
    for key, zone in ZONE_MAP.items():
        if key in loc:
            return zone
    return "Other"

def parse_floor(floor_str: str):
    if not floor_str or pd.isna(floor_str):
        return None
    match = re.search(r'(\d+)', str(floor_str))
    return int(match.group(1)) if match else None

def compute_ppsqft(rent, sqft):
    try:
        if rent and sqft and float(sqft) > 0:
            return round(float(rent) / float(sqft), 2)
    except:
        pass
    return None

def load():
    df = pd.read_csv("data/House_Rent_Dataset.csv")

    # Filter Bangalore only
    df = df[df["City"].str.lower() == "bangalore"].copy()
    print(f"Bangalore rows: {len(df)}")

    # Clean
    df = df.dropna(subset=["Rent", "Size", "BHK", "Area Locality"])
    df["BHK"]  = df["BHK"].astype(int)
    df["Rent"] = df["Rent"].astype(int)
    df["Size"] = df["Size"].astype(float).astype(int)
    print(f"After cleaning: {len(df)} rows")

    conn = get_connection()
    cur  = conn.cursor()
    inserted = 0

    for _, row in df.iterrows():
        locality = str(row["Area Locality"]).strip()
        rent     = int(row["Rent"])
        sqft     = int(row["Size"])
        bhk      = int(row["BHK"])

        cur.execute("""
            INSERT INTO listings (
                source, locality, city_zone, bhk_type,
                rent_monthly, area_sqft, furnishing,
                near_metro, listing_date, price_per_sqft
            ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (
            "kaggle",
            locality[:200],
            get_zone(locality),
            f"{bhk} BHK",
            rent,
            sqft,
            str(row.get("Furnishing Status", "")).strip()[:100],
            None,
            pd.to_datetime(row["Posted On"]).date() if pd.notna(row.get("Posted On")) else None,
            compute_ppsqft(rent, sqft),
        ))
        inserted += 1

    conn.commit()
    cur.close()
    conn.close()
    print(f"Inserted: {inserted} rows")

if __name__ == "__main__":
    load()
