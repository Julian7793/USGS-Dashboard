import streamlit as st
from scraper import fetch_site_graphs
from datetime import datetime
import pytz
from streamlit_autorefresh import st_autorefresh
import requests

# Constants
REFRESH_INTERVAL = 30
ZIP_CODE = "47012"
API_KEY = st.secrets["WEATHERAPI_KEY"]  # ✅ Read from Streamlit Cloud secrets

# Streamlit page config
st.set_page_config(page_title="USGS Water + Weather Dashboard", layout="wide")
st_autorefresh(interval=REFRESH_INTERVAL * 1000, limit=None, key="autorefresh")
eastern = pytz.timezone("US/Eastern")

# Page title and time
st.title("📈 USGS Site Graphs (Live)")
updated_time = datetime.now(eastern).strftime("%Y-%m-%d %I:%M %p %Z")
st.caption(f"🔄 Last updated: {updated_time}")

# Weather helper
def fetch_weather(zip_code):
    url = f"http://api.weatherapi.com/v1/forecast.json?key={API_KEY}&q={zip_code}&days=3&aqi=no&alerts=no"
    try:
        res = requests.get(url)
        if res.status_code == 200:
            return res.json(
