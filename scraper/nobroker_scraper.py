from playwright.sync_api import sync_playwright
from db_utils import insert_listing
from datetime import date
import time
import random
import re

# ── Config ─────────────────────────────────────────────
BASE_URL = "https://www.nobroker.in/property/rent/bangalore"

LOCALITIES = {
    "whitefield":       "East",
    "marathahalli":     "East",
    "sarjapur-road":    "East",
    "bellandur":        "East",
    "hsr-layout":       "South",
    "btm-layout":       "South",
    "koramangala":      "South",
    "jp-nagar":         "South",
    "electronic-city":  "South",
    "indiranagar":      "Central",
    "domlur":           "Central",
    "hebbal":           "North",
    "yelahanka":        "North",
}

# ── Helpers ─────────────────────────────────────────────
def parse_rent(text: str) -> int | None:
    if not text:
        return None
    digits = re.sub(r"[^\d]", "", text)
    return int(digits) if digits else None

def parse_area(text: str) -> int | None:
    if not text:
        return None
    match = re.search(r"(\d+)", text.replace(",", ""))
    return int(match.group(1)) if match else None

def compute_price_per_sqft(rent, sqft):
    if rent and sqft and sqft > 0:
        return round(rent / sqft, 2)
    return None

def random_delay():
    time.sleep(random.uniform(2.5, 5.0))

# ── Core Scraper ─────────────────────────────────────────
def scrape_locality(page, locality: str, zone: str, max_listings: int = 100):
    url = f"{BASE_URL}/{locality}/?propertyFor=rent"
    print(f"\n Scraping: {locality} ({zone}) → {url}")

    page.goto(url, wait_until="domcontentloaded", timeout=60000)
    page.wait_for_selector(".list-card-container", timeout=30000)
    # Add after wait_for_selector:
    try:
        page.click(".chat-bot-close", timeout=3000)
    except:
        pass
    random_delay()

    scraped = 0
    scroll_attempts = 0
    max_scrolls = 20

    while scraped < max_listings and scroll_attempts < max_scrolls:
        # Get all listing cards currently loaded
        cards = page.query_selector_all(".list-card-container")

        if not cards:
            print(f"  No cards found. Check selector.")
            break

        for card in cards[scraped:]:
            try:
                # ── Extract fields ──────────────────────────
                rent_el    = card.query_selector(".list-card-price")
                bhk_el     = card.query_selector(".list-card-bedroom-value")
                area_el    = card.query_selector(".list-card-area-value")
                furnish_el = card.query_selector(".list-card-furniture-value")
                url_el     = card.query_selector("a")

                rent_text    = rent_el.inner_text()    if rent_el    else None
                bhk_text     = bhk_el.inner_text()     if bhk_el     else None
                area_text    = area_el.inner_text()    if area_el    else None
                furnish_text = furnish_el.inner_text() if furnish_el else None
                listing_url  = url_el.get_attribute("href") if url_el else None

                rent   = parse_rent(rent_text)
                sqft   = parse_area(area_text)
                ppsqft = compute_price_per_sqft(rent, sqft)

                if not rent:
                    continue  # skip if no rent found

                data = {
                    "source":        "nobroker",
                    "locality":      locality.replace("-", " ").title(),
                    "city_zone":     zone,
                    "bhk_type":      bhk_text.strip() if bhk_text else None,
                    "rent_monthly":  rent,
                    "deposit_amount": None,
                    "area_sqft":     sqft,
                    "furnishing":    furnish_text.strip() if furnish_text else None,
                    "near_metro":    None,
                    "listing_date":  date.today(),
                    "listing_url":   listing_url,
                    "price_per_sqft": ppsqft,
                }

                insert_listing(data)
                scraped += 1
                print(f"  [{scraped}] {data['locality']} | {data['bhk_type']} | ₹{data['rent_monthly']}")

                if scraped >= max_listings:
                    break

            except Exception as e:
                print(f"  Card parse error: {e}")
                continue

        # Scroll down to load more
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        random_delay()
        scroll_attempts += 1

    print(f"  Done: {scraped} listings saved for {locality}")
    return scraped

# ── Runner ───────────────────────────────────────────────
def run_scraper(test_mode: bool = False):
    targets = dict(list(LOCALITIES.items())[:2]) if test_mode else LOCALITIES

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,   # keep visible while debugging
            slow_mo=100, channel="chrome"
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) "
                       "Chrome/122.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        total = 0
        for locality, zone in targets.items():
            try:
                count = scrape_locality(page, locality, zone, max_listings=50)
                total += count
                random_delay()
            except Exception as e:
                print(f"Failed {locality}: {e}")
                continue

        browser.close()
        print(f"\n Total scraped: {total} listings")

if __name__ == "__main__":
    run_scraper(test_mode=True)   # test 2 localities first
