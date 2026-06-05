import requests
import base64
import json
import os
import sys
import time
import random
import re
from datetime import date
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from db_utils import insert_listing

load_dotenv()

# ── Locality master (lat/lon/placeId from NoBroker's own URL encoding) ──
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

# ── Helpers ──────────────────────────────────────────────────────────────
def parse_cookies(cookie_str: str) -> dict:
    cookies = {}
    for item in cookie_str.split(';'):
        item = item.strip()
        if '=' in item:
            k, v = item.split('=', 1)
            cookies[k.strip()] = v.strip()
    return cookies

def build_search_param(locality: dict) -> str:
    payload = [{
        "lat":       locality["lat"],
        "lon":       locality["lon"],
        "placeId":   locality["placeId"],
        "placeName": locality["placeName"]
    }]
    return base64.b64encode(json.dumps(payload).encode()).decode()

def parse_rent(text: str):
    if not text:
        return None
    digits = re.sub(r"[^\d]", "", text)
    return int(digits) if digits else None

def parse_area(text: str):
    if not text:
        return None
    m = re.search(r"(\d[\d,]*)", text)
    return int(m.group(1).replace(",", "")) if m else None

def random_delay():
    time.sleep(random.uniform(1.5, 3.0))

# ── Core fetch ───────────────────────────────────────────────────────────
def fetch_locality(session: requests.Session, locality: dict, page: int = 0):
    params = {
        "searchParam":       build_search_param(locality),
        "radius":            "2.0",
        "sharedAccomodation":"0",
        "city":              "bangalore",
        "locality":          locality["placeName"],
        "page":              str(page),
    }
    response = session.get(BASE_URL, params=params, timeout=30)
    print(f"  Status: {response.status_code} | Size: {len(response.text)} chars | Content-Type: {response.headers.get('content-type','?')}")
    return response

# ── Test run — inspect raw response ──────────────────────────────────────
def test_fetch():
    cookie_str = os.getenv("NB_COOKIE", "")
    if not cookie_str:
        print("NB_COOKIE missing in .env")
        return

    session = requests.Session()
    session.cookies.update(parse_cookies(cookie_str))
    session.headers.update({
        "user-agent":  "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36",
        "referer":     "https://www.nobroker.in/",
        "accept":      "application/json, text/plain, */*",
        "accept-language": "en-US,en;q=0.9",
    })

    locality = LOCALITIES[0]  # Whitefield
    print(f"Testing: {locality['placeName']}")
    resp = fetch_locality(session, locality)
    parse_listings_from_html(resp.text, locality)

    # Print first 2000 chars to inspect structure
    print("\n── Response preview ──")
    extract_json_from_html(resp.text)



# Add to imports at top
from bs4 import BeautifulSoup

# Add this function
def extract_json_from_html(html: str):
    """Find embedded JSON listing data in NoBroker's SSR HTML"""
    soup = BeautifulSoup(html, "html.parser")

    scripts = soup.find_all("script")
    print(f"\nTotal script tags: {len(scripts)}")

    for i, script in enumerate(scripts):
        content = script.string or ""
        # Look for script tags containing property/listing data
        if any(kw in content for kw in ["propertyList", "searchResult", "listingData", "INITIAL_STATE", "rentValue", "builtUpArea"]):
            print(f"\n[Script #{i}] Found relevant script — length: {len(content)}")
            print(content[:3000])
            break
    else:
        print("\nNo matching script found. Trying regex on raw HTML...")
        # Try finding JSON blob with rent data
        matches = re.findall(r'"rentValue"\s*:\s*\d+', html)
        print(f"'rentValue' occurrences: {len(matches)}")
        if matches:
            print("Sample:", matches[:5])

        matches2 = re.findall(r'"builtUpArea"\s*:\s*\d+', html)
        print(f"'builtUpArea' occurrences: {len(matches2)}")


def parse_listings_from_html(html: str, locality: dict) -> list:
    soup = BeautifulSoup(html, "html.parser")
    scripts = soup.find_all("script")

    app_state_raw = None
    for script in scripts:
        content = script.string or ""
        if "nb.appState" in content:
            match = re.search(r'nb\.appState\s*=\s*(\{.+\})\s*;?\s*$', content, re.DOTALL)
            if match:
                app_state_raw = match.group(1)
                break

    if not app_state_raw:
        print("  nb.appState not found")
        return []

    try:
        app_state = json.loads(app_state_raw)
    except json.JSONDecodeError as e:
        print(f"  JSON parse failed: {e}")
        return []

    # Navigate to listing data
    properties = app_state.get("listPage", {}).get("listPageProperties", [])
    print(f"  Properties found: {len(properties)}")

    if not properties:
        return []

    # Inspect first property keys
    print(f"  First property keys: {list(properties[0].keys())}")
    print(f"  Sample: {json.dumps(properties[0], indent=2)[:1500]}")

    return properties

def test_fetch():
    cookie_str = os.getenv("NB_COOKIE", "")
    session = requests.Session()
    session.cookies.update(parse_cookies(cookie_str))
    session.headers.update({
        "user-agent":      "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36",
        "referer":         "https://www.nobroker.in/",
        "accept":          "application/json, text/plain, */*",
        "accept-language": "en-US,en;q=0.9",
    })

    locality = LOCALITIES[0]
    print(f"Testing: {locality['placeName']}")
    resp = fetch_locality(session, locality)
    parse_listings_from_html(resp.text, locality)

if __name__ == "__main__":
    test_fetch()
