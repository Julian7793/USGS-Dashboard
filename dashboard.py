import streamlit as st
from scraper import fetch_site_graphs
from datetime import datetime
import pytz
import requests
from streamlit_autorefresh import st_autorefresh

# Constants
REFRESH_INTERVAL = 30
eastern = pytz.timezone("US/Eastern")
BROOKVILLE_AVG_LEVEL = 748  # Target lake level
BROOKVILLE_SITE_NO = "03275990"

# Configure Streamlit
st.set_page_config(page_title="USGS Water Graphs", layout="wide")
st_autorefresh(interval=REFRESH_INTERVAL * 1000, limit=None, key="autorefresh")

st.title("📈 USGS Site Graphs (Live)")
data = fetch_site_graphs()
updated_time = datetime.now(eastern)
st.caption(f"🔄 Last updated: {updated_time.strftime('%Y-%m-%d %I:%M %p %Z')}")

# Fetch real-time gage height (ft) and timestamp
def fetch_live_stages(site_ids):
    params = {
        "format": "json",
        "sites": ",".join(site_ids),
        "parameterCd": "00065",
        "siteStatus": "all"
    }
    url = "https://waterservices.usgs.gov/nwis/iv/"
    resp = requests.get(url, params=params, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    stages = {}
    for site in data.get("value", {}).get("timeSeries", []):
        site_no = site["sourceInfo"]["siteCode"][0]["value"]
        vals = site["values"][0]["value"]
        if vals:
            value = float(vals[-1]["value"])
            timestamp = vals[-1]["dateTime"]
            stages[site_no] = {"value": value, "timestamp": timestamp}
        else:
            stages[site_no] = {"value": None, "timestamp": None}
    return stages

# Site limits and config
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

# Status evaluation
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

def get_lake_status(level_ft):
    if level_ft is None:
        return "❔ Unknown"
    lower_bound = BROOKVILLE_AVG_LEVEL * 0.98
    upper_bound = BROOKVILLE_AVG_LEVEL * 1.02
    if level_ft < lower_bound:
        return f"🔽 Below Normal ({level_ft:.2f} ft)"
    elif level_ft > upper_bound:
        return f"🔼 Above Normal ({level_ft:.2f} ft)"
    else:
        return f"🟢 Normal Level ({level_ft:.2f} ft)"

# Fetch data
site_list = list(station_limits.keys())
try:
    live_stages = fetch_live_stages(site_list)
except requests.RequestException as e:
    st.error(f"⚠️ Failed to fetch USGS gage heights: {e}")
    live_stages = {}

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

        site_no = item["page_url"].split("-")[-1]
        entry = live_stages.get(site_no, {})
        value = entry.get("value")
        timestamp = entry.get("timestamp")
        cfg = station_limits.get(site_no)

        if site_no == BROOKVILLE_SITE_NO:
            lake_status = get_lake_status(value)
            if value is not None:
                ts_local = datetime.fromisoformat(timestamp).astimezone(eastern)
                st.markdown(f"**Lake Elevation:** {value:.2f} ft – {lake_status}")
                st.caption(f"Last reading: {ts_local.strftime('%Y-%m-%d %I:%M %p %Z')}")
            else:
                st.markdown(f"**Lake Elevation:** ❔ No data – {lake_status}")
        else:
            river_status = get_river_safety_status(site_no, value)
            st.markdown(f"**River Status:** {river_status}")

        if cfg:
            if cfg["type"] == "operational":
                st.caption(f"Operational limits: {cfg['min']} ft (min), {cfg['max']} ft (max).")
            elif cfg["type"] == "flood":
                stages = ", ".join(f"{stage} at {val} ft" for stage, val in cfg["stages"].items())
                st.caption(f"Flood stages – {stages}.")
            elif cfg["type"] == "lake":
                st.caption(cfg.get("note", "Lake level shown in ft."))

        # Weather for Brookville Lake
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
