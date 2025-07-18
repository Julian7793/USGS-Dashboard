import streamlit as st
from scraper import fetch_site_graphs
from datetime import datetime
import pytz
from streamlit_autorefresh import st_autorefresh
import requests

# Constants
REFRESH_INTERVAL = 30
eastern = pytz.timezone("US/Eastern")
BROOKVILLE_AVG_LEVEL = 148  # feet
BROOKVILLE_SITE_NO = "03275990"

# Configure Streamlit
st.set_page_config(page_title="USGS Water Graphs", layout="wide")
st_autorefresh(interval=REFRESH_INTERVAL * 1000, limit=None, key="autorefresh")

st.title("📈 USGS Site Graphs (Live)")
data = fetch_site_graphs()
updated_time = datetime.now(eastern)
st.caption(f"🔄 Last updated: {updated_time.strftime('%Y-%m-%d %I:%M %p %Z')}")

# Mock flow/lake level data (replace with real-time USGS data if available)
mock_flows = {
    "03274650": 450,    # Economy
    "03276000": 1250,   # East Fork
    "03275000": 1700,   # Alpine
    "03276500": 800,    # Brookville River
    "03275990": 152.3   # Brookville Lake (example lake level in ft)
}

# River Safety Status
def get_river_safety_status(site_no, flow_cfs):
    thresholds = {
        "03274650": (500, 1500),
        "03276000": (600, 1600),
        "03275000": (550, 1550),
        "03276500": (700, 1700),
    }
    low, high = thresholds.get(site_no, (500, 1500))
    if flow_cfs is None:
        return "❔ Unknown"
    elif flow_cfs > high:
        return "🔴 Unsafe"
    elif flow_cfs > low:
        return "🟡 Caution"
    else:
        return "🟢 Safe"

# Lake Level Status for Brookville Lake
def get_lake_status(level_ft):
    if level_ft is None:
        return "❔ Unknown"
    lower_bound = BROOKVILLE_AVG_LEVEL * 0.90
    upper_bound = BROOKVILLE_AVG_LEVEL * 1.10
    if level_ft < lower_bound:
        return "🔽 Below Average"
    elif level_ft > upper_bound:
        return "🔼 Above Average"
    else:
        return "🟢 Average"

# Layout
cols = st.columns(3)
weather_displayed = False

for i, item in enumerate(data):
    with cols[i % 3]:
        st.markdown(f"#### [{item['title']}]({item['page_url']})", unsafe_allow_html=True)

        if item["image_url"]:
            st.image(item["image_url"], use_container_width=True)
        else:
            st.warning("⚠️ No image found.")

        # Extract site_no
        site_no = item["page_url"].split("-")[-1]
        value = mock_flows.get(site_no)

        # Show lake or river status
        if site_no == BROOKVILLE_SITE_NO:
            lake_status = get_lake_status(value)
            st.markdown(f"**Lake Status:** {lake_status}")
        else:
            river_status = get_river_safety_status(site_no, value)
            st.markdown(f"**River Status:** {river_status}")

        # Inject weather block next to Brookville Lake
        if site_no == BROOKVILLE_SITE_NO and not weather_displayed:
            weather_displayed = True
            st.markdown("---")
            st.markdown("### 🌤️ 3-Day Weather Forecast (47012)")

            api_key = st.secrets.get("WEATHERAPI_KEY", "")
            if not api_key:
                st.error("❌ WEATHERAPI_KEY missing in Streamlit secrets.")
            else:
                try:
                    res = requests.get(
                        f"https://api.weatherapi.com/v1/forecast.json?key={api_key}&q=47012&days=3&aqi=no&alerts=no"
                    )
                    res.raise_for_status()
                    weather = res.json()

                    for day in weather["forecast"]["forecastday"]:
                        date = datetime.strptime(day["date"], "%Y-%m-%d").strftime("%a, %b %d")
                        icon = day["day"]["condition"]["icon"]
                        condition = day["day"]["condition"]["text"]
                        high = day["day"]["maxtemp_f"]
                        low = day["day"]["mintemp_f"]

                        st.markdown(f"**{date}**")
                        st.image(f"https:{icon}", width=48)
                        st.markdown(f"{condition}")
                        st.markdown(f"🌡️ {low}°F – {high}°F")
                        st.markdown("---")
                except requests.RequestException as e:
                    st.error(f"Request error: {e}")
