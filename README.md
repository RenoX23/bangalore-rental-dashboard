
# Bangalore Rental Market Intelligence Dashboard

Live Demo → https://renox23-bangalore-rental-dashboard.streamlit.app/

## Business Question
Which Bangalore micro-markets offer the best rental value, and where are renters overpaying?

## Key Findings
- **Ramamurthy Nagar and K R Puram** offer the best value at ₹13–14/sqft vs ₹31/sqft in Whitefield
- A 2BHK renter in Whitefield overpays ~₹8,000/month vs equivalent space in East periphery localities
- **South zone** (JP Nagar belt) has the highest listing volume (205) with mid-range pricing — best renter market
- Furnished apartments command a **98% premium** over unfurnished (₹40,881 vs ₹16,427 avg)
- 3BHK rent (₹61,989) is 3.8x a 1BHK (₹9,368) — sharp jump beyond 2BHK tier

## Stack
| Layer | Tool |
|---|---|
| Data Collection | NoBroker API (Playwright + Requests) |
| Storage | PostgreSQL |
| Processing | Python, Pandas, SQL |
| Visualization | Streamlit, Plotly |
| Deployment | Streamlit Cloud |

## Dataset
886 Bangalore rental listings across 127 localities · Cleaned and zone-mapped

## Project Structure
```
bangalore-rental-dashboard/
├── scraper/
│   ├── api_scraper.py      # NoBroker API client
│   ├── load_csv.py         # CSV → PostgreSQL loader
│   ├── db_utils.py         # DB connection utility
│   └── zone_update.sql     # Locality → zone mapping
├── dashboard/
│   └── app.py              # Streamlit dashboard
└── data/
    └── listings_clean.csv  # Cleaned dataset
```

## Setup
```bash
git clone https://github.com/RenoX23/bangalore-rental-dashboard
cd bangalore-rental-dashboard
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
streamlit run dashboard/app.py
```
