# SolarEdge Streamlit Dashboard

This Streamlit dashboard visualizes solar production data using the SolarEdge Monitoring API. It supports energy tracking, peak power analysis, CO₂ savings, and customizable visualizations including heatmaps and bar charts.

## 🌞 Features

- Live site overview (current power, daily & lifetime energy)
- Environmental benefits (CO₂ saved, trees planted)
- Interactive energy visualizations:
  - Daily energy production
  - Daily peak power (W)
  - Average hourly energy output
  - Monthly average vs. peak power
  - Hour vs. day energy heatmap
- Timestamp and power of peak production
- Downloadable CSV and PNG outputs
- Unit toggle: Wh / kWh

## 🚀 How to Use

1. Clone this repository or upload it to [Streamlit Cloud](https://streamlit.io/cloud)
2. Or go to https://k8nqdbwc4mpaiu4r8faewc.streamlit.app
3. Add your SolarEdge **API Key** and **Site ID** in the Streamlit sidebar
4. Select your date range
5. Click "Fetch Data" to generate visualizations

## 📦 Requirements

Install dependencies using pip:

```bash
pip install -r requirements.txt
```

## 🔧 Configuration

You will need:
- A valid [SolarEdge API Key](https://www.solaredge.com/)
- Your SolarEdge Site ID

These values can be pasted into the sidebar fields when running the app.

## 📁 Files

- `solaredge_dashboard.py`: Main Streamlit app
- `requirements.txt`: Python dependencies
- `README.md`: This file

## 📷 Screenshots

*(Insert screenshots here if desired)*

## 🛡 License

This project is open-source and available for customization.
