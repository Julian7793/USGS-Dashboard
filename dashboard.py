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

# Mock gage height stage values in feet
mock_stages = {
    "03274650": 3.85,   # Economy
    "03276000": 5.12,   # East Fork
    "03275000": 10.7,   # Alpine
    "03276500": 12.6,   # Brookville River
    "03275990": 152.3   # Brookville Lake
}

# Station-specific limits and flood stages
station_limits = {
    "03274650": {
        "name": "Whitewater River Near Economy, IN",
        "type": "operational",
        "min": 2.26,
        "max": 13.98,
        "min_msg": "Lower intake out of water",
        "max_msg": "Float hitting bottom of gage shelf"
    },
    "03276000": {
        "name": "East Fork Whitewater River at Brookville, IN",
        "type": "operational",
        "min": 0.69,
        "max": 25.72,
        "min_msg": "Lower intake out of water",
        "max_msg": "Float hitting bottom of gage shelf"
    },
    "03275000": {
        "name": "Whitewater River Near Alpine, IN",
        "type": "flood",
        "stages": {"Action": 10, "Minor": 14, "Moderate": 17, "Major": 19}
    },
    "03276500": {
        "name": "Whitewater River at Brookville, IN",
        "type": "flood",
        "stages": {"Action": 14, "Minor": 20, "Moderate": 23, "Major": 29}
    },
    "03275990": {
        "name": "Brookville Lake at Brookville, IN",
        "type": "lake",
        "note": "Lake or reservoir water surface elevation above NGVD 1929, ft"
    }
}

# River or Flood Safety Status
def get_river_safety_status(site_no, value):
    cfg = station_limits.get(site_no)
    if value is None or cfg is None:
        return "❔ Unknown"

    if cfg["type"] == "operational":
        if value < cfg["min"]:
            return f"🔽 Too Low – {cfg['min_msg']} ({value:.2f} ft)"
        elif value > cfg["max"]:
            return f"🔼 Too High – {cfg['max_msg']} ({value:.2f} ft)"
        else:
            return f"🟢 Normal Operating Range ({value:.2f} ft)"

    elif cfg["type"] == "flood":
        for stage, threshold in reversed(sorted(cfg["stages"].items(), key=lambda x: x[1])):
            if value >= threshold:
                return f"⚠️ {stage} Flood Stage Reached ({value:.2f} ft)"
        return f"🟢 Below Flood Stage ({value:.2f} ft)"

    return "🟢 Normal"

# Lake Level Status for Brookville Lake
def get_lake_status(level_ft):
    if level_ft is None:
        return "❔ Unknown"
    lower_bound = BROOKVILLE_AVG_LEVEL * 0.90
    upper_bound = BROOKVILLE_AVG_LEVEL * 1.10
    if level_ft < lower_bound:
        return f"🔽 Below Average ({level_ft:.2f} ft)"
    elif level_ft > upper_bound:
        return f"🔼 Above Average ({level_ft:.2f} ft)"
    else:
        return f"🟢 Average ({level_ft:.2f} ft)"

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
        value = mock_stages.get(site_no)

        # Show lake or river status
        if site_no == BROOKVILLE_SITE_NO:
            lake_status = get_lake_status(value)
            st.markdown(f"**Lake Status:** {lake_status}")
        else:
            river_status = get_river_safety_status(site_no, value)
            st.markdown(f"**River Status:** {river_status}")

        # Add description/caption
        cfg = station_limits.get(site_no)
        if cfg:
            if cfg["type"] == "operational":
                st.caption(
                    f"Operational limits: {cfg['min']} ft (min), {cfg['max']} ft (max)."
                )
            elif cfg["type"] == "flood":
                stages = ", ".join(f"{stage} at {val} ft" for stage, val in cfg["stages"].items())
                st.caption(f"Flood stages – {stages}.")
            elif cfg["type"] == "lake":
                st.caption(cfg.get("note", "Lake level shown in ft."))

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
