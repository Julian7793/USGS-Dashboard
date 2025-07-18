import streamlit as st
from scraper import fetch_site_graphs
from datetime import datetime
import pytz
from streamlit_autorefresh import st_autorefresh
import requests

# Constants
REFRESH_INTERVAL = 30
ZIP_CODE = "47012"

# Streamlit config
st.set_page_config(page_title="USGS Water Graphs", layout="wide")
st_autorefresh(interval=REFRESH_INTERVAL * 1000, limit=None, key="autorefresh")
eastern = pytz.timezone("US/Eastern")

# Title and timestamp
st.title("📈 USGS Site Graphs (Live)")
updated_time = datetime.now(eastern)
st.caption(f"🔄 Last updated: {updated_time.strftime('%Y-%m-%d %I:%M %p %Z')}")

# Fetch USGS data
data = fetch_site_graphs()

# Create 3-column layout
cols = st.columns(3)

# Render graphs + weather
for i, item in enumerate(data):
    with cols[i % 3]:
        st.markdown(f"#### [{item['title']}]({item['page_url']})", unsafe_allow_html=True)
        if item["image_url"]:
            st.image(item["image_url"], use_container_width=True)
        else:
            st.warning("⚠️ No image found.")

    # Inject weather after Brookville Lake
    if item.get("site_no") == "03275990":
        with cols[(i + 1) % 3]:
            st.markdown("### 🌤️ Brookville Weather Forecast")

            API_KEY = st.secrets.get("WEATHERAPI_KEY")
            if not API_KEY:
                st.error("❌ WEATHERAPI_KEY is missing from Streamlit secrets.")
            else:
                url = f"http://api.weatherapi.com/v1/forecast.json?key={API_KEY}&q={ZIP_CODE}&days=3&aqi=no&alerts=no"
                try:
                    res = requests.get(url)
                    if res.status_code == 200:
                        weather = res.json()
                        current = weather["current"]
                        forecast = weather["forecast"]["forecastday"]

                        st.metric("Current Temp (°F)", f"{current['temp_f']}°F")
                        st.caption(current["condition"]["text"])

                        forecast_cols = st.columns(3)
                        for j, day in enumerate(forecast):
                            with forecast_cols[j]:
                                st.markdown(f"**{day['date']}**")
                                icon_url = f"https:{day['day']['condition']['icon']}"
                                st.image(icon_url)
                                st.markdown(f"↑ {day['day']['maxtemp_f']}°F")
                                st.markdown(f"↓ {day['day']['mintemp_f']}°F")
                    else:
                        st.error(f"Failed to fetch weather data: {res.status_code}")
                except Exception as e:
                    st.error(f"Weather API error: {e}")
