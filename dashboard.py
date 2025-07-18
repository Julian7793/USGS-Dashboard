import streamlit as st
from scraper import fetch_site_graphs
from datetime import datetime
import pytz
from streamlit_autorefresh import st_autorefresh
import requests
import os
from dotenv import load_dotenv

load_dotenv()

REFRESH_INTERVAL = 30
st.set_page_config(page_title="USGS Water Graphs", layout="wide")
st_autorefresh(interval=REFRESH_INTERVAL * 1000, limit=None, key="autorefresh")
eastern = pytz.timezone("US/Eastern")

st.title("📈 USGS Site Graphs (Live)")
data = fetch_site_graphs()
updated_time = datetime.now(eastern)
updated_time_str = updated_time.strftime("%Y-%m-%d %I:%M %p %Z")
st.caption(f"🔄 Last updated: {updated_time_str}")

cols = st.columns(3)

def fetch_weather(city):
    api_key = os.getenv("WEATHERAPI_KEY")
    if not api_key:
        return None, "No API key found"
    url = f"http://api.weatherapi.com/v1/current.json?key={api_key}&q={city}&aqi=no"
    resp = requests.get(url)
    if resp.status_code != 200:
        return None, f"Error fetching weather: {resp.status_code}"
    return resp.json(), None

for i, item in enumerate(data):
    with cols[i % 3]:
        st.markdown(f"#### [{item['title']}]({item['page_url']})", unsafe_allow_html=True)
        if item["image_url"]:
            st.image(item["image_url"], use_container_width=True)
        else:
            st.warning("⚠️ No image found.")

    if item["title"].startswith("Brookville Lake at Brookville"):
        st.markdown("---")
        st.subheader("🌤️ Current Weather in Brookville, IN")

        weather_data, error = fetch_weather("Brookville")
        if error:
            st.error(error)
        else:
            current = weather_data["current"]
            st.markdown(f"**Temperature:** {current['temp_f']} °F")
            st.markdown(f"**Condition:** {current['condition']['text']}")
            st.markdown(f"**Humidity:** {current['humidity']}%")
            st.markdown(f"**Wind Speed:** {current['wind_mph']} mph")
