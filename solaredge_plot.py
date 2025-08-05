import streamlit as st
import pandas as pd
import plotly.express as px
import requests
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import seaborn as sns
import io
import os

# === CONFIGURATION ===
st.set_page_config(page_title="SolarEdge Dashboard", layout="wide")

# Sidebar input for user configuration
st.sidebar.header("🔧 Configuration")
API_KEY = st.sidebar.text_input("API Key", value=os.getenv("SE_API_KEY", ""), type="password")
SITE_ID = st.sidebar.text_input("Site ID", value=os.getenv("SE_SITE_ID", ""))

if not API_KEY or not SITE_ID:
    st.warning("Please enter your API Key and Site ID in the sidebar to begin.")
    st.stop()

BASE_URL = f"https://monitoringapi.solaredge.com/site/{SITE_ID}"
MAX_DAYS = 31

@st.cache_data(show_spinner=False)
def fetch_energy_chunked(time_unit, start_date, end_date):
    current = start_date
    all_frames = []

    while current <= end_date:
        chunk_end = min(current + timedelta(days=MAX_DAYS - 1), end_date)
        try:
            df = fetch_single_chunk(time_unit, current, chunk_end)
            if not df.empty:
                all_frames.append(df)
            current = chunk_end + timedelta(days=1)

        except requests.exceptions.HTTPError as e:
            st.warning(f"⚠️ Failed {current} to {chunk_end}. Retrying day-by-day...")
            for d in pd.date_range(current, chunk_end):
                try:
                    df_day = fetch_single_chunk(time_unit, d.date(), d.date())
                    if not df_day.empty:
                        all_frames.append(df_day)
                except Exception as sub_e:
                    st.warning(f"⚠️ Skipped {d.date()}: {sub_e}")
            current = chunk_end + timedelta(days=1)

    if all_frames:
        return pd.concat(all_frames, ignore_index=True)
    return pd.DataFrame()

def fetch_single_chunk(time_unit, start_date, end_date):
    url = f"{BASE_URL}/energy"
    params = {
        "api_key": API_KEY,
        "timeUnit": time_unit,
        "startDate": start_date.isoformat(),
        "endDate": end_date.isoformat()
    }
    r = requests.get(url, params=params, timeout=30)
    r.raise_for_status()
    data = r.json().get("energy", {}).get("values", [])
    df = pd.DataFrame(data)
    if df.empty:
        return df
    df["datetime"] = pd.to_datetime(df["date"])
    df["value"] = df["value"].fillna(0)
    df["hour"] = df["datetime"].dt.hour + df["datetime"].dt.minute / 60
    df["date"] = df["datetime"].dt.date
    df["year"] = df["datetime"].dt.year
    df["month"] = df["datetime"].dt.month
    df["day"] = df["datetime"].dt.day
    df["hour_rounded"] = df["hour"].round().astype(int)
    return df

def fetch_site_overview():
    url = f"{BASE_URL}/overview?api_key={API_KEY}"
    try:
        r = requests.get(url, timeout=30)
        r.raise_for_status()
        return r.json().get("overview", {})
    except Exception as e:
        st.warning(f"Failed to fetch site overview: {e}")
        return {}

def fetch_env_benefits():
    url = f"{BASE_URL}/envBenefits?api_key={API_KEY}"
    try:
        r = requests.get(url, timeout=30)
        r.raise_for_status()
        return r.json().get("envBenefits", {})
    except Exception as e:
        st.warning(f"Failed to fetch environmental benefits: {e}")
        return {}

# === UI ===
st.title("\U0001F4A1 SolarEdge Production Dashboard")

# Site overview
st.subheader("System Overview")
overview = fetch_site_overview()
if overview:
    col1, col2, col3 = st.columns(3)
    col1.metric("Current Power (W)", f"{overview.get('currentPower', {}).get('power', 0):,.0f}")
    col2.metric("Today (Wh)", f"{overview.get('lastDayData', {}).get('energy', 0):,.0f}")
    col3.metric("Lifetime (kWh)", f"{overview.get('lifeTimeData', {}).get('energy', 0) / 1000:,.0f}")

# Environmental impact
st.subheader("Environmental Impact")
env = fetch_env_benefits()
co2 = env.get('gasEmissionSaved', {}).get('co2', 0)
trees = round(co2 / (12940 / 386)) if co2 > 0 else 0

col1, col2 = st.columns(2)
col1.metric("CO2 Saved (kg)", f"{co2:,.0f}")
col2.metric("Trees Planted", f"{trees:,.0f}")

# Unit selection
unit = st.radio("Select unit for energy display:", ["Wh", "kWh"], horizontal=True)
unit_factor = 1 if unit == "Wh" else 1000
unit_label = unit

# Date range selection
today = datetime.today().date()
def_year = today.year
start_date = st.date_input("Start Date", value=datetime(def_year, 1, 1).date())
end_date = st.date_input("End Date", value=today)

# Fetch data if requested
if st.button("Fetch Data"):
    with st.spinner("Fetching and processing data..."):
        df = fetch_energy_chunked("QUARTER_OF_AN_HOUR", start_date, end_date)

    if df.empty:
        st.warning("No data found.")
    else:
        st.success("Data loaded successfully!")

        # Display KPI
        total_energy = df['value'].sum() / unit_factor
        st.metric(f"Total Energy ({unit_label})", f"{total_energy:,.2f}")
        max_power = df['value'].max() / 0.25
        peak_row = df[df['value'] == df['value'].max()].iloc[0]
        st.metric("Max Power (W)", f"{max_power:,.0f}")
        st.markdown(f"**Timestamp of Max Power:** {peak_row['datetime']}")

        # Daily total chart
        st.subheader("Daily Energy Production")
        daily_df = df.groupby("date")["value"].sum().reset_index()
        daily_df["value"] = (daily_df["value"] / unit_factor).round(2)
        fig = px.bar(daily_df, x="date", y="value", labels={"value": unit_label}, title="Daily Total Energy")
        st.plotly_chart(fig, use_container_width=True)

        # Daily max power
        st.subheader("Daily Peak Power (W)")
        daily_peak = df.groupby("date")["value"].max().reset_index()
        daily_peak["max_power"] = (daily_peak["value"] / 0.25).round()
        fig_peak = px.line(daily_peak, x="date", y="max_power", title="Daily Peak Power")
        st.plotly_chart(fig_peak, use_container_width=True)

        # Hourly profile
        st.subheader("Average Hourly Production")
        avg_hour = df.groupby("hour_rounded")["value"].mean().reset_index()
        avg_hour["value"] = (avg_hour["value"] / unit_factor).round(2)
        fig2 = px.line(avg_hour, x="hour_rounded", y="value", markers=True,
                      labels={"hour_rounded": "Hour", "value": f"Avg {unit_label}"})
        st.plotly_chart(fig2, use_container_width=True)

        # Avg vs Peak per Month
        st.subheader("Monthly Avg vs Peak Power")
        monthly = df.groupby(["year", "month"])
        monthly_avg = monthly["value"].mean().reset_index(name="avg_wh")
        monthly_peak = monthly["value"].max().reset_index(name="peak_wh")
        monthly_power = pd.merge(monthly_avg, monthly_peak, on=["year", "month"])
        monthly_power["avg_w"] = (monthly_power["avg_wh"] / 0.25).round()
        monthly_power["peak_w"] = (monthly_power["peak_wh"] / 0.25).round()
        monthly_power["label"] = monthly_power["year"].astype(str) + "-" + monthly_power["month"].astype(str).str.zfill(2)

        fig_month = px.bar(monthly_power, x="label", y=["avg_w", "peak_w"], barmode="group",
                           labels={"value": "Watts", "label": "Month"},
                           title="Monthly Average vs Peak Power (W)")
        st.plotly_chart(fig_month, use_container_width=True)

        # Filter heatmap
        st.subheader("Heatmap: Hour vs Day")
        year_option = st.selectbox("Filter by Year (optional)", options=["All"] + sorted(df["year"].unique().tolist()))
        if year_option != "All":
            df = df[df["year"] == int(year_option)]

        pivot = df.pivot_table(index="hour_rounded", columns="date", values="value", aggfunc="mean").fillna(0)
        pivot = pivot.loc[~(pivot == 0).all(axis=1)] / unit_factor

        # Annotate peak hour as power not energy
        peak_idx = df[df['value'] == df['value'].max()].iloc[0]
        peak_power_kw = (peak_idx['value'] / 0.25) / 1000
        st.markdown(f"**Peak Power:** {peak_idx['datetime']} — {peak_power_kw:.2f} kW")

        fig, ax = plt.subplots(figsize=(15, 6))
        sns.heatmap(pivot.round(2), cmap="YlOrRd", ax=ax, cbar_kws={"label": unit_label}, yticklabels=True)
        ax.set_title("Energy Heatmap (Hour vs Day)")
        ax.invert_yaxis()
        st.pyplot(fig)

        # Download heatmap as image
        buf = io.BytesIO()
        fig.savefig(buf, format="png")
        st.download_button("Download Heatmap as PNG", data=buf.getvalue(), file_name="heatmap.png", mime="image/png")

        # Download CSV
        st.download_button("Download CSV", data=df.to_csv(index=False), file_name="solaredge_data.csv")
