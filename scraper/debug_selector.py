# scraper/debug_selector.py  — replace entire file
from playwright.sync_api import sync_playwright
import time

def debug():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=100, channel="chrome")
        page = browser.new_page(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) "
                       "Chrome/122.0.0.0 Safari/537.36"
        )

        page.goto(
            "https://www.nobroker.in/property/rent/bangalore/whitefield/?propertyFor=rent",
            wait_until="domcontentloaded",
            timeout=60000
        )

        time.sleep(8)
        page.screenshot(path="debug_screenshot.png")
        print("Screenshot saved")

        # Get outer HTML of first card candidate
        for cls in ["shadow-defaultCardShadow", "bg-card-overview-border-color"]:
            el = page.query_selector(f".{cls}")
            if el:
                html = el.inner_html()
                print(f"\n=== .{cls} inner HTML (first 2000 chars) ===")
                print(html[:2000])
            else:
                print(f"\n.{cls} → NOT FOUND")

        browser.close()

if __name__ == "__main__":
    debug()
