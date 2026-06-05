import requests
import base64
import json
import os
import sys
import re
import time
import random
from datetime import date, datetime
from bs4 import BeautifulSoup
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from db_utils import insert_listing

load_dotenv()

# ── Locality master ───────────────────────────────────────────────────────
LOCALITIES = [
    {"placeName": "Whitefield",      "lat": 12.9698196, "lon": 77.7499721, "placeId": "ChIJg_wNXfMRrjsR-RUB2BKlzzA", "zone": "East"},
    {"placeName": "Marathahalli",    "lat": 12.956924,  "lon": 77.701127,  "placeId": "ChIJVwkdVbQTrjsRGUkefteUeFk", "zone": "East"},
    {"placeName": "Hebbal",          "lat": 13.0353557, "lon": 77.5987873, "placeId": "ChIJRwrYlaIXrjsRWUexKPPLPBo", "zone": "North"},
    {"placeName": "Koramangala",     "lat": 12.9352,    "lon": 77.6245,    "placeId": "ChIJ93DfBBITrjsRthWLuFqoKSc", "zone": "South"},
    {"placeName": "HSR Layout",      "lat": 12.9081,    "lon": 77.6476,    "placeId": "ChIJt43BI1oTrjsRdVGqpGxBfHc", "zone": "South"},
    {"placeName": "BTM Layout",      "lat": 12.9165,    "lon": 77.6101,    "placeId": "ChIJjbfMLlcTrjsRf5UMnEsxoqk", "zone": "South"},
    {"placeName": "Indiranagar",     "lat": 12.9784,    "lon": 77.6408,    "placeId": "ChIJFWABwxMTrjsROIiEfHsHBeg", "zone": "Central"},
    {"placeName": "Electronic City", "lat": 12.8452,    "lon": 77.6602,    "placeId": "ChIJL9oBKZkTrjsRdJOp83SIQKA", "zone": "South"},
    {"placeName": "Sarjapur Road",   "lat": 12.9102,    "lon": 77.6784,    "placeId": "ChIJOR7bMdQTrjsRXqylGzp4VeQ", "zone": "East"},
    {"placeName": "JP Nagar",        "lat": 12.9077,    "lon": 77.5777,    "placeId": "ChIJnUPVAl8UrjsRv3xoU5gvJRQ", "zone": "South"},
]

BASE_URL = "https://www.nobroker.in/property/rent/bangalore/multiple"

BHK_MAP = {
    "RK1": "1 RK", "BHK1": "1 BHK", "BHK2": "2 BHK",
    "BHK3": "3 BHK", "BHK4": "4 BHK", "BHK4PLUS": "4+ BHK",
}

FURNISH_MAP = {
    "Full": "Furnished", "Semi": "Semi-Furnished",
    "Unfurnished": "Unfurnished", "None": "Unfurnished",
}

# ── Helpers ───────────────────────────────────────────────────────────────
def parse_cookies(cookie_str: str) -> dict:
    cookies = {}
    for item in cookie_str.split(';'):
        item = item.strip()
        if '=' in item:
            k, v = item.split('=', 1)
            cookies[k.strip()] = v.strip()
    return cookies



def run_scraper(test_mode=False):
    cookie_str = os.getenv("NB_COOKIE", "")
    print(f"Cookie loaded: {len(cookie_str)} chars")  # must be > 500
    if not cookie_str:
        print("NB_COOKIE missing")
        return

    
def build_search_param(locality: dict) -> str:
    payload = [{"lat": locality["lat"], "lon": locality["lon"],
                "placeId": locality["placeId"], "placeName": locality["placeName"]}]
    # separators removes spaces — matches NoBroker's expected format
    return base64.b64encode(json.dumps(payload, separators=(',', ':')).encode()).decode()

def ms_to_date(ms) -> date:
    try:
        return datetime.fromtimestamp(int(ms) / 1000).date()
    except:
        return date.today()

def compute_ppsqft(rent, sqft):
    if rent and sqft and sqft > 0:
        return round(rent / sqft, 2)
    return None

def random_delay():
    time.sleep(random.uniform(2.0, 4.0))

# ── Parse one property dict → DB row ─────────────────────────────────────
# Replace parse_property function:
def parse_property(prop: dict, locality: dict) -> dict | None:
    rent = prop.get("rent")
    if not rent:
        return None

    sqft  = prop.get("propertySize")
    bhk_raw     = prop.get("type", "")
    furnish_raw = prop.get("furnishingDesc", "")

    return {
        "source":         "nobroker",
        "locality":       str(prop.get("locality") or locality["placeName"])[:200],
        "city_zone":      locality["zone"][:100],
        "bhk_type":       BHK_MAP.get(bhk_raw, bhk_raw)[:50],
        "rent_monthly":   int(rent),
        "deposit_amount": int(prop["deposit"]) if prop.get("deposit") else None,
        "area_sqft":      int(sqft) if sqft else None,
        "furnishing":     FURNISH_MAP.get(furnish_raw, furnish_raw)[:100],
        "near_metro":     None,
        "listing_date":   ms_to_date(prop.get("activationDate")),
        "listing_url":    f"https://www.nobroker.in{prop.get('detailUrl', '')}",
        "price_per_sqft": compute_ppsqft(rent, sqft),
    }

# Replace fetch_page function — add retry:
def fetch_page(session, locality: dict, page: int = 0, retries: int = 3) -> list:
    params = {
        "searchParam":        build_search_param(locality),
        "radius":             "2.0",
        "sharedAccomodation": "0",
        "city":               "bangalore",
        "locality":           locality["placeName"],
        "page":               str(page),
    }

    for attempt in range(retries):
        try:
            resp = session.get(BASE_URL, params=params, timeout=45)
            if resp.status_code != 200:
                print(f"  HTTP {resp.status_code}")
                return []
            break
        except Exception as e:
            wait = (attempt + 1) * 5
            print(f"  Timeout attempt {attempt+1}/{retries}. Retry in {wait}s...")
            time.sleep(wait)
    else:
        print("  All retries failed")
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    app_state_raw = None
    for script in soup.find_all("script"):
        content = script.string or ""
        if "nb.appState" in content:
            match = re.search(r'nb\.appState\s*=\s*(\{.+\})\s*;?\s*$', content, re.DOTALL)
            if match:
                app_state_raw = match.group(1)
                break

    if not app_state_raw:
        return []

    try:
        app_state = json.loads(app_state_raw)
    except json.JSONDecodeError:
        return []

    return app_state.get("listPage", {}).get("listPageProperties", [])

# ── Fetch + parse one page ─────────────────────────────────────────────
def fetch_page(session, locality: dict, page: int = 0) -> list:
    params = {
        "searchParam":        build_search_param(locality),
        "radius":             "2.0",
        "sharedAccomodation": "0",
        "city":               "bangalore",
        "locality":           locality["placeName"],
        "page":               str(page),
    }
    resp = session.get(BASE_URL, params=params, timeout=30)

    if resp.status_code != 200:
        print(f"  HTTP {resp.status_code}")
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    app_state_raw = None
    for script in soup.find_all("script"):
        content = script.string or ""
        if "nb.appState" in content:
            match = re.search(r'nb\.appState\s*=\s*(\{.+\})\s*;?\s*$', content, re.DOTALL)
            if match:
                app_state_raw = match.group(1)
                break

    if not app_state_raw:
        return []

    try:
        app_state = json.loads(app_state_raw)
    except json.JSONDecodeError:
        return []

    return app_state.get("listPage", {}).get("listPageProperties", [])

# ── Scrape one locality (all pages) ───────────────────────────────────────
def scrape_locality(session, locality: dict, max_pages: int = 5):
    print(f"\nScraping: {locality['placeName']} ({locality['zone']})")
    total = 0

    for page in range(max_pages):
        print(f"  Page {page}...", end=" ")
        props = fetch_page(session, locality, page)
        print(f"{len(props)} properties")

        if not props:
            break

        for prop in props:
            row = parse_property(prop, locality)
            if row:
                insert_listing(row)
                total += 1

        random_delay()

    print(f"  Saved: {total} listings")
    return total

# ── Main runner ───────────────────────────────────────────────────────────
def run_scraper(test_mode: bool = False):
    cookie_str = os.getenv("NB_COOKIE", "")
    if not cookie_str:
        print("NB_COOKIE missing in .env")
        return

    session = requests.Session()
    session.cookies.update(parse_cookies(cookie_str))
    session.headers.update({
    "user-agent":       "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36",
    "referer":          "https://www.nobroker.in/",
    "accept":           "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "accept-language":  "en-US,en;q=0.9",
    "accept-encoding":  "gzip, deflate, br",
    "connection":       "keep-alive",
    "upgrade-insecure-requests": "1",
})

    targets = LOCALITIES[:2] if test_mode else LOCALITIES
    grand_total = 0

    for locality in targets:
        try:
            count = scrape_locality(session, locality, max_pages=5)
            grand_total += count
        except Exception as e:
            print(f"  Failed {locality['placeName']}: {e}")
        random_delay()

    print(f"\nTotal saved: {grand_total} listings")

if __name__ == "__main__":
    run_scraper(test_mode=True)
