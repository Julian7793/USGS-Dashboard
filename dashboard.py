import streamlit as st
from scraper import fetch_site_graphs
from datetime import datetime
import pytz
from streamlit_autorefresh import st_autorefresh
import requests

# Constants
REFRESH_INTERVAL = 30
ZIP_CODE = "47012"
API_KEY = st.secrets["WEATHERAPI_KEY"]  # ✅ From Streamlit Cloud Secrets

# Streamlit setup
st.set_page_config(page_title="USGS Water + Weather Dashboard", layout="wide")
st_autorefresh(interval=REFRESH_INTERVAL * 1000, limit=None, key="autorefresh")
eastern = pytz.timezone("US/Eastern")

# Title + Time
st.title("📈 USGS Site Graphs (Live)")
updated_time = datetime.now(eastern).strftime("%Y-%m-%d %I:%M %p %Z")
st.caption(f"🔄 Last updated: {updated_time}")

# Weather helpers
def fetch_weather(zip_code):
    url = f"http://api.weatherapi.com/v1/forecast.json?key={API_KEY}&q={zip_code}&days=3&aqi=no&alerts=no"
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
        "Thunder": "⛈️", "Rain": "🌧️", "Showers": "🌦️", "Sunny": "☀️",
        "Clear": "☀️", "Cloudy": "☁️", "Partly cloudy": "⛅",
        "Fog": "🌫️", "Snow": "❄️", "Sleet": "🌨️"
    }
    for k, v in lookup.items():
        if k.lower() in desc.lower():
            return v
    return "🌡️"

# Fetch USGS site data
data = fetch_site_graphs()
i = 0
while i < len(data):
    item = data[i]

    # If Brookville Lake, show graph + weather side by side
    if "Brookville Lake" in item["title"]:
        graph_col, weather_col = st.columns([2, 1])
        with graph_col:
            st.markdown(f"#### [{item['title']}]({item['page_url']})", unsafe_allow_html=True)
            if item["image_url"]:
                st.image(item["image_url"], use_container_width=True)
            else:
                st.warning("⚠️ No image found.")

        with weather_col:
            st.markdown("#### 🌤️ Brookville Weather Forecast")
            weather = fetch_weather(ZIP_CODE)
            if weather:
                current = weather["current"]
                forecast = weather["forecast"]["forecastday"]

                # Current conditions
                col1, col2 = st.columns([1, 2])
                with col1:
                    st.markdown(f"### {current['temp_f']}°F {weather_icon(current['condition']['text'])}")
                    st.caption(current["condition"]["text"])
                with col2:
                    st.markdown(f"**💨 Wind:** {current['wind_mph']} mph")
                    st.markdown(f"**🌫️ Humidity:** {current['humidity']}%")

                # 3-day forecast
                st.markdown("**🗓️ 3-Day Outlook**")
                day_cols = st.columns(3)
                for j, day in enumerate(forecast):
                    with day_cols[j]:
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
        i += 1

    else:
        # Show other graphs in standard 3-column layout
        cols = st.columns(3)
        for col in cols:
            if i >= len(data):
                break
            item = data[i]
            with col:
                st.markdown(f"#### [{item['title']}]({item['page_url']})", unsafe_allow_html=True)
                if item["image_url"]:
                    st.image(item["image_url"], use_container_width=True)
                else:
                    st.warning("⚠️ No image found.")
            i += 1
