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

# Fetch real-time gage height and lake elevation
def fetch_live_stages(site_ids):
    params = {
        "format": "json",
        "sites": ",".join(site_ids),
        "parameterCd": "00065,00062",  # Gage height and lake elevation
        "siteStatus": "all"
    }
    url = "https://waterservices.usgs.gov/nwis/iv/"
    resp = requests.get(url, params=params, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    stages = {}

    for site in data.get("value", {}).get("timeSeries", []):
        site_no = site["sourceInfo"]["siteCode"][0]["value"]
        param = site["variable"]["variableCode"][0]["value"]
        vals = site["values"][0]["value"]
        if not vals:
            continue
        value = float(vals[-1]["value"])

        # Brookville Lake uses lake elevation (00062)
        if site_no == BROOKVILLE_SITE_NO and param == "00062":
            stages[site_no] = value
        elif site_no != BROOKVILLE_SITE_NO and param == "00065":
            stages[site_no] = value

    return stages

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
        return f"🔽 Below Average"
    elif level_ft > upper_bound:
        return f"🔼 Above Average"
    else:
        return f"🟢 Average"

# Fetch live values
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
        value = live_stages.get(site_no)

        # Display site-specific status
        if site_no == BROOKVILLE_SITE_NO:
            status = get_lake_status(value)
            st.maif value is not None:
    st.markdown(f"**Lake Elevation:** {value:.2f} ft – {status}")
else:
    st.markdown(f"**Lake Elevation:** ❔ No data – {status}")
rkdown(f"**Lake Elevation:** {value:.2f} ft – {status}")
        else:
            status = get_river_safety_status(site_no, value)
            st.markdown(f"**River Status:** {status}")

        # Show operational/flood/lake metadata
        cfg = station_limits.get(site_no)
        if cfg:
            if cfg["type"] == "operational":
                st.caption(f"Operational limits: {cfg['min']} ft (min), {cfg['max']} ft (max).")
            elif cfg["type"] == "flood":
                stages = ", ".join(f"{stage} at {val} ft" for stage, val in cfg["stages"].items())
                st.caption(f"Flood stages – {stages}.")
            elif cfg["type"] == "lake":
                st.caption(cfg.get("note", "Lake level shown in ft."))

        # Weather next to Brookville Lake
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
