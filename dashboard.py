import streamlit as st
from scraper import fetch_site_graphs
from datetime import datetime
import pytz
from streamlit_autorefresh import st_autorefresh
import requests

# Refresh interval in seconds
REFRESH_INTERVAL = 30

# Set page config at the very top
st.set_page_config(page_title="USGS Water Graphs", layout="wide")

# Automatically rerun this script every REFRESH_INTERVAL seconds
st_autorefresh(interval=REFRESH_INTERVAL * 1000, limit=None, key="autorefresh")

# Timezone for Eastern Time (handles daylight saving)
eastern = pytz.timezone("US/Eastern")

st.title("📈 USGS Site Graphs (Live)")

# Fetch data fresh every time the script runs (which now happens every 30 seconds automatically)
data = fetch_site_graphs()

# Display last updated time as current time in Eastern timezone
updated_time = datetime.now(eastern)
updated_time_str = updated_time.strftime("%Y-%m-%d %I:%M %p %Z")
st.caption(f"🔄 Last updated: {updated_time_str}")

# Helper functions for MetaWeather API

def get_woeid(city):
    url = f"https://www.metaweather.com/api/location/search/?query={city}"
    res = requests.get(url)
    if res.status_code == 200 and res.json():
        return res.json()[0]["woeid"]
    return None

def get_weather(woeid):
    url = f"https://www.metaweather.com/api/location/{woeid}/"
    res = requests.get(url)
    if res.status_code == 200:
        data = res.json()
        today = data['consolidated_weather'][0]
        return {
            "temp_c": today["the_temp"],
            "desc": today["weather_state_name"],
            "humidity": today["humidity"],
            "wind_speed_mph": today["wind_speed"]
        }
    return None

# Layout: 3 cards per row
cols = st.columns(3)

for i, item in enumerate(data):
    with cols[i % 3]:
        st.markdown(f"#### [{item['title']}]({item['page_url']})", unsafe_allow_html=True)
        if item["image_url"]:
            st.image(item["image_url"], use_container_width=True)
        else:
            st.warning("⚠️ No image found.")

    # After Brookville Lake at Brookville, IN - 03275990, insert weather widget
    if item["title"].startswith("Brookville Lake at Brookville"):
        st.markdown("---")
        st.subheader("🌤️ Current Weather in Brookville, IN")

        city = "Brookville"
        woeid = get_woeid(city)

        if woeid:
            weather = get_weather(woeid)
            if weather:
                st.markdown(f"**Temperature:** {weather['temp_c']:.1f} °C")
                st.markdown(f"**Condition:** {weather['desc']}")
                st.markdown(f"**Humidity:** {weather['humidity']}%")
                st.markdown(f"**Wind Speed:** {weather['wind_speed_mph']:.1f} mph")
            else:
                st.error("⚠️ Could not fetch weather data.")
        else:
            st.error("⚠️ Could not find the city.")

