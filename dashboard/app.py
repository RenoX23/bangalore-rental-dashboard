import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(
    page_title="Bangalore Rental Intelligence",
    page_icon="🏠",
    layout="wide"
)

# ── Data loader ───────────────────────────────────────────────────────────
@st.cache_data
def load_data():
    conn = psycopg2.connect(
        host=os.getenv("DB_HOST"), port=os.getenv("DB_PORT"),
        dbname=os.getenv("DB_NAME"), user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD")
    )
    df = pd.read_sql("SELECT * FROM listings", conn)
    conn.close()
    return df

df = load_data()

# ── Sidebar filters ───────────────────────────────────────────────────────
st.sidebar.title("Filters")
bhk_options = sorted(df["bhk_type"].dropna().unique())
selected_bhk = st.sidebar.multiselect("BHK Type", bhk_options, default=bhk_options)

zone_options = sorted(df["city_zone"].dropna().unique())
selected_zones = st.sidebar.multiselect("City Zone", zone_options, default=[z for z in zone_options if z != "Other"])

filtered = df[
    df["bhk_type"].isin(selected_bhk) &
    df["city_zone"].isin(selected_zones)
]

# ── Header ────────────────────────────────────────────────────────────────
st.title("🏠 Bangalore Rental Market Intelligence")
st.caption("886 listings · Source: NoBroker/Kaggle · Updated: June 2026")

# ── KPI row ───────────────────────────────────────────────────────────────
k1, k2, k3, k4 = st.columns(4)
k1.metric("Total Listings",     f"{len(filtered):,}")
k2.metric("Median Rent",        f"₹{int(filtered['rent_monthly'].median()):,}")
k3.metric("Avg Price/sqft",     f"₹{int(filtered['price_per_sqft'].dropna().mean())}")
k4.metric("Localities Covered", f"{filtered['locality'].nunique()}")

st.divider()

# ── Row 1: BHK + Zone ─────────────────────────────────────────────────────
col1, col2 = st.columns(2)

with col1:
    st.subheader("Avg Rent by BHK Type")
    bhk_df = (filtered.groupby("bhk_type")["rent_monthly"]
              .mean().round().reset_index()
              .sort_values("rent_monthly"))
    fig = px.bar(bhk_df, x="rent_monthly", y="bhk_type", orientation="h",
                 text="rent_monthly", color="rent_monthly",
                 color_continuous_scale="Blues",
                 labels={"rent_monthly": "Avg Rent (₹)", "bhk_type": ""})
    fig.update_traces(texttemplate="₹%{text:,.0f}", textposition="outside")
    fig.update_layout(coloraxis_showscale=False, height=300,xaxis_range=[0, 150000])
    st.plotly_chart(fig, use_container_width=True)

with col2:
    st.subheader("Avg Rent by City Zone")
    zone_df = (filtered[filtered["city_zone"] != "Other"]
               .groupby("city_zone")["rent_monthly"]
               .mean().round().reset_index()
               .sort_values("rent_monthly", ascending=False))
    fig2 = px.bar(zone_df, x="city_zone", y="rent_monthly",
                  text="rent_monthly", color="rent_monthly",
                  color_continuous_scale="Oranges",
                  labels={"rent_monthly": "Avg Rent (₹)", "city_zone": "Zone"})
    fig2.update_traces(texttemplate="₹%{text:,.0f}", textposition="outside")
    fig2.update_layout(coloraxis_showscale=False, height=300)
    st.plotly_chart(fig2, use_container_width=True)

st.divider()

# ── Row 2: Top expensive + Best value ────────────────────────────────────
col3, col4 = st.columns(2)

with col3:
    st.subheader("🔴 Top 10 Most Expensive Localities")
    exp_df = (filtered.groupby("locality")
              .agg(avg_rent=("rent_monthly","mean"), count=("id","count"))
              .query("count >= 5")
              .sort_values("avg_rent", ascending=False)
              .head(10).reset_index())
    exp_df["avg_rent"] = exp_df["avg_rent"].round()
    fig3 = px.bar(exp_df, x="avg_rent", y="locality", orientation="h",
                  text="avg_rent", color="avg_rent",
                  color_continuous_scale="Reds",
                  labels={"avg_rent": "Avg Rent (₹)", "locality": ""})
    fig3.update_traces(texttemplate="₹%{text:,.0f}", textposition="auto")
    fig3.update_layout(coloraxis_showscale=False, height=400,
                       yaxis={"categoryorder": "total ascending"},margin={"r":120},xaxis_range=[0, 75000])
    st.plotly_chart(fig3, use_container_width=True)

with col4:
    st.subheader("🟢 Best Value Localities (₹/sqft)")
    val_df = (filtered[filtered["price_per_sqft"].notna()]
              .groupby("locality")
              .agg(avg_ppsqft=("price_per_sqft","mean"),
                   avg_rent=("rent_monthly","mean"),
                   count=("id","count"))
              .query("count >= 5")
              .sort_values("avg_ppsqft")
              .head(10).reset_index())
    val_df["avg_ppsqft"] = val_df["avg_ppsqft"].round(1)
    fig4 = px.bar(val_df, x="avg_ppsqft", y="locality", orientation="h",
                  text="avg_ppsqft", color="avg_ppsqft",
                  color_continuous_scale="Greens",
                  labels={"avg_ppsqft": "Avg ₹/sqft", "locality": ""})
    fig4.update_traces(texttemplate="₹%{text}", textposition="auto")
    fig4.update_layout(coloraxis_showscale=False, height=400,
                       yaxis={"categoryorder": "total descending"},margin={"r": 80})
    st.plotly_chart(fig4, use_container_width=True)

st.divider()

# ── Row 3: Furnishing + Rent distribution ────────────────────────────────
col5, col6 = st.columns(2)

with col5:
    st.subheader("Furnishing Impact on Rent")
    furn_df = (filtered.groupby("furnishing")["rent_monthly"]
               .mean().round().reset_index()
               .sort_values("rent_monthly", ascending=False))
    fig5 = px.bar(furn_df, x="furnishing", y="rent_monthly",
                  text="rent_monthly", color="furnishing",
                  color_discrete_sequence=["#2196F3","#FF9800","#4CAF50"],
                  labels={"rent_monthly": "Avg Rent (₹)", "furnishing": ""})
    fig5.update_traces(texttemplate="₹%{text:,.0f}", textposition="outside")
    fig5.update_layout(showlegend=False, height=300)
    st.plotly_chart(fig5, use_container_width=True)

with col6:
    st.subheader("Rent Distribution by BHK")
    fig6 = px.box(filtered[filtered["rent_monthly"] < 100000],
                  x="bhk_type", y="rent_monthly",
                  color="bhk_type",
                  labels={"rent_monthly": "Rent (₹)", "bhk_type": "BHK Type"})
    fig6.update_layout(showlegend=False, height=300)
    st.plotly_chart(fig6, use_container_width=True)

st.divider()

# ── Key Insight callout ───────────────────────────────────────────────────
st.subheader("📌 Key Finding")
st.info(
    "**Ramamurthy Nagar and K R Puram offer the best rental value in Bangalore** — "
    "averaging just ₹13–14/sqft vs ₹31/sqft in East zone (Whitefield). "
    "A 2BHK renter in Whitefield overpays ~₹8,000/month vs equivalent space in Ramamurthy Nagar. "
    "South zone (JP Nagar, Koramangala belt) offers the best volume and mid-range pricing for renters."
)
