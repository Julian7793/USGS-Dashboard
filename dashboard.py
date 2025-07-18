import streamlit as st
from scraper import fetch_site_graphs
from datetime import datetime
import pytz
from streamlit_autorefresh import st_autorefresh
import requests
import os
from dotenv import load_dotenv

# Load env for API key
load_dotenv()

# Constants
REFRESH_INTERVAL = 30
CITY = "Brookville"
API_KEY = os.getenv("WEATHERAPI_KEY")

# Set Streamlit config
st.set_page_config(page_title="USGS Water + Weather Dashboard", layout="wide")
st_autorefresh(interval=REFRESH_INTERVAL * 1000, limit=None, key="autorefresh")
eastern = pytz.timezone("US/Eastern")

# Title
st.title("📈 USGS Site Graphs (Live)")
updated_time = datetime.now(eastern).strftime("%Y-%m-%d %I:%M %p %Z")
st.caption(f"🔄 Last updated: {updated_time}")

# Fetch graphs
data = fetch_site_graphs()
cols = st.columns(3)

# --- Weather helper functions ---

def fetch_weather(city):
    if not API_KEY:
        st.warning("⚠️ WeatherAPI key not found.")
        return None
    url = f"http://api.weatherapi.com/v1/forecast.json?key={API_KEY}&q={city}&days=7&aqi=no&alerts=no"
    try:
        res = requests.get(url)
        if res.status_code == 200:
            return res.json()
        else:
            st.error(f"Weather fetch failed: {res.status_code}")
            return None
    except Exception as e:
        st.error(f"Request error: {e}")
        return None

def weather_icon(desc):
    lookup = {
        "Thunder": "⛈️",
        "Rain": "🌧️",
        "Showers": "🌦️",
        "Sunny": "☀️",
        "Clear": "☀️",
        "Cloudy": "☁️",
        "Partly cloudy": "⛅",
        "Fog": "🌫️",
        "Snow": "❄️",
        "Sleet": "🌨️"
    }
    for k, v in lookup.items():
        if k.lower() in desc.lower():
            return v
    return "🌡️"

# --- USGS graph display + weather card injection ---
for i, item in enumerate(data):
    with cols[i % 3]:
        st.markdown(f"#### [{item['title']}]({item['page_url']})", unsafe_allow_html=True)
        if item["image_url"]:
            st.image(item["image_url"], use_container_width=True)
        else:
            st.warning("⚠️ No image found.")

        if "Brookville Lake" in item["title"]:
            st.markdown("---")
            st.subheader("🌤️ Brookville Weather Forecast")

            weather = fetch_weather(CITY)
            if weather:
                current = weather["current"]
                forecast = weather["forecast"]["forecastday"]

                # --- Current Conditions ---
                col1, col2 = st.columns([1, 2])
                with col1:
                    st.markdown(f"### {current['temp_f']}°F {weather_icon(current['condition']['text'])}")
                    st.caption(current["condition"]["text"])
                with col2:
                    st.markdown(f"**💧 Precip:** {current['precip_in']} in")
                    st.markdown(f"**💨 Wind:** {current['wind_mph']} mph")
                    st.markdown(f"**🌫️ Humidity:** {current['humidity']}%")

                # --- Hourly Precip Chart ---
                hourly = forecast[0]["hour"]
                precip = [h["precip_in"] for h in hourly]
                labels = [datetime.strptime(h["time"], "%Y-%m-%d %H:%M").strftime("%-I %p") for h in hourly]
                st.markdown("**🌧️ Precipitation Next 24h**")
                st.bar_chart(data=precip, x=labels)

                # --- 7-Day Forecast ---
                st.markdown("**🗓️ 7-Day Outlook**")
                day_cols = st.columns(len(forecast))
                for i, day in enumerate(forecast):
                    with day_cols[i]:
                        dt = datetime.strptime(day["date"], "%Y-%m-%d").strftime("%a")
                        condition = day["day"]["condition"]["text"]
                        emoji = weather_icon(condition)
                        st.markdown(f"**{dt}**")
                        st.markdown(emoji)
                        st.markdown(f"↑ {day['day']['maxtemp_f']}°F")
                        st.markdown(f"↓ {day['day']['mintemp_f']}°F")
                        st.caption(condition)

            else:
                st.warning("⚠️ Could not load weather data.")
