import streamlit as st
from scraper import fetch_site_graphs
from datetime import datetime
import pytz
from streamlit_autorefresh import st_autorefresh
import requests

# --- REMOVE TOP PADDING VIA CSS ---
st.markdown(
    """
    <style>
      .block-container { padding-top: 0rem; }
    </style>
    """,
    unsafe_allow_html=True,
)

# Constants
REFRESH_INTERVAL = 300
eastern = pytz.timezone("US/Eastern")
BROOKVILLE_AVG_LEVEL = 748
BROOKVILLE_SITE_NO = "03275990"

# Configure Streamlit
st.set_page_config(page_title="USGS Water Graphs", layout="wide")
st_autorefresh(interval=REFRESH_INTERVAL * 1000, limit=None, key="autorefresh")

# Page title & update time
st.header("📈 USGS Site Graphs (Live)")
data = fetch_site_graphs()

# Add custom site manually (East Fork Whitewater River near Abington)
data.append({
    "title": "East Fork Whitewater River near Abington",
    "page_url": "https://waterdata.usgs.gov/monitoring-location/USGS-03274615",
    "image_url": "https://waterdata.usgs.gov/nwisweb/graph?agency_cd=USGS&site_no=03274615&parm_cd=00065&period=7"
})

updated_time = datetime.now(eastern)
st.caption(f"🔄 Last updated: {updated_time.strftime('%Y-%m-%d %I:%M %p %Z')}")

# --- 7‑Day WEATHER FORECAST AT THE TOP ---
api_key = st.secrets.get("WEATHERAPI_KEY", "")
if not api_key:
    st.error("❌ WEATHERAPI_KEY missing in Streamlit secrets.")
else:
    try:
        res = requests.get(
            "https://api.weatherapi.com/v1/forecast.json",
            params={"key": api_key, "q": "47012", "days": 7, "aqi": "no", "alerts": "no"},
            timeout=10
        )
        res.raise_for_status()
        weather = res.json()
        st.markdown('<h3 style="font-size:1.2rem;">7‑Day Weather Forecast (47012)</h3>', unsafe_allow_html=True)

        days = weather["forecast"]["forecastday"]
        cols = st.columns(len(days))
        for col, day in zip(cols, days):
            with col:
                date = datetime.strptime(day["date"], "%Y-%m-%d").strftime("%a, %b %d")
                icon = day["day"]["condition"]["icon"]
                cond = day["day"]["condition"]["text"]
                hi, lo = day["day"]["maxtemp_f"], day["day"]["mintemp_f"]
                precip = day["day"]["totalprecip_in"]
                st.markdown(f"**{date}**")
                st.image(f"https:{icon}", width=50)
                st.markdown(cond)
                st.markdown(f"🌡️ {lo}°F – {hi}°F")
                st.markdown(f"💧 Precip: {precip:.2f} in")
    except requests.RequestException as e:
        st.error(f"❌ Weather fetch error: {e}")

st.markdown("---")

# --- USGS STAGES FETCHER ---
def fetch_live_stages(site_ids):
    lake_site = BROOKVILLE_SITE_NO
    river_sites = [sid for sid in site_ids if sid != lake_site]
    stages = {}

    # Rivers (gage height 00065)
    if river_sites:
        try:
            resp = requests.get(
                "https://waterservices.usgs.gov/nwis/iv/",
                params={"format":"json","sites":",".join(river_sites),"parameterCd":"00065","siteStatus":"all"},
                timeout=10
            )
            resp.raise_for_status()
            data = resp.json()
            for ts in data["value"]["timeSeries"]:
                sid = ts["sourceInfo"]["siteCode"][0]["value"]
                vals = ts["values"][0]["value"]
                stages[sid] = float(vals[-1]["value"]) if vals else None
        except requests.RequestException:
            for sid in river_sites:
                stages[sid] = None

    # Lake (elevation 62614)
    try:
        resp = requests.get(
            "https://waterservices.usgs.gov/nwis/iv/",
            params={"format":"json","sites":lake_site,"parameterCd":"62614","siteStatus":"all"},
            timeout=10
        )
        resp.raise_for_status()
        data = resp.json()
        for ts in data["value"]["timeSeries"]:
            sid = ts["sourceInfo"]["siteCode"][0]["value"]
            vals = ts["values"][0]["value"]
            stages[sid] = float(vals[-1]["value"]) if vals else None
    except requests.RequestException:
        stages[lake_site] = None

    return stages

# Station config
station_limits = {
    "03274650": {"type":"operational","min":2.26,"max":13.98,
                 "min_msg":"Lower intake out of water","max_msg":"Float hitting bottom of gage shelf"},
    "03276000": {"type":"operational","min":0.69,"max":25.72,
                 "min_msg":"Lower intake out of water","max_msg":"Float hitting bottom of gage shelf"},
    "03275000": {"type":"flood","stages":{"Action":10,"Minor":14,"Moderate":17,"Major":19}},
    "03276500": {"type":"flood","stages":{"Action":14,"Minor":20,"Moderate":23,"Major":29}},
    "03275990": {"type":"lake","note":"Lake or reservoir water surface elevation above NGVD 1929, ft"},
    "03274615": {"type":"flood","stages":{"Action":14,"Minor":16,"Moderate":24,"Major":30}}  # updated values
}

def get_river_safety_status(sid, val):
    cfg = station_limits[sid]
    if val is None:
        return "❔ Unknown"
    if cfg["type"] == "operational":
        if val < cfg["min"]:
            return f"🔽 Too Low – {cfg['min_msg']} ({val:.2f} ft)"
        if val > cfg["max"]:
            return f"🔼 Too High – {cfg['max_msg']} ({val:.2f} ft)"
        return f"🟢 Normal Operating Range ({val:.2f} ft)"
    for stage, thr in sorted(cfg["stages"].items(), key=lambda x: x[1], reverse=True):
        if val >= thr:
            return f"⚠️ {stage} Flood Stage Reached ({val:.2f} ft)"
    return f"🟢 Below Flood Stage ({val:.2f} ft)"

def get_lake_status(lv):
    if lv is None:
        return "❔ Unknown"
    lb, ub = BROOKVILLE_AVG_LEVEL * 0.98, BROOKVILLE_AVG_LEVEL * 1.02
    if lv < lb:
        return f"🔽 Below Normal ({lv:.2f} ft)"
    if lv > ub:
        return f"🔼 Above Normal ({lv:.2f} ft)"
    return f"🟢 Normal Level ({lv:.2f} ft)"

# Fetch USGS data
try:
    live_stages = fetch_live_stages(list(station_limits.keys()))
except Exception as e:
    st.error(f"⚠️ Failed to fetch USGS data: {e}")
    live_stages = {}

# --- DISPLAY EACH SITE ---
cols = st.columns(3)
for idx, item in enumerate(data):
    with cols[idx % 3]:
        full_title = item["title"]
        display_title = full_title.split(" - ")[0]
        st.markdown(f"#### [{display_title}]({item['page_url']})", unsafe_allow_html=True)

        # Show graph
        if item["image_url"]:
            st.image(item["image_url"], use_container_width=True)
        else:
            st.warning("⚠️ No image found.")

        # Determine site ID
        sid = item["page_url"].split("-")[-1]
        val = live_stages.get(sid)

        # Status message
        if sid == BROOKVILLE_SITE_NO:
            status = get_lake_status(val)
            st.markdown(f"**Lake Status:** {val:.2f} ft – {status}" if val is not None else f"**Lake Status:** ❔ No data – {status}")
        elif sid in station_limits:
            river_status = get_river_safety_status(sid, val)
            st.markdown(f"**River Status:** {river_status}")
        else:
            st.markdown("**Status:** Not configured")

        # Custom info footer for 03274615
        if sid == "03274615":
            st.caption("Flood stages in ft  \n"
                       "14 – Action stage  \n"
                       "16 – Minor flood  \n"
                       "24 – Moderate flood  \n"
                       "30 – Major flood")
        else:
            cfg = station_limits.get(sid)
            if cfg:
                if cfg["type"] == "operational":
                    st.caption(f"Operational limits: {cfg['min']} ft (min), {cfg['max']} ft (max).")
                elif cfg["type"] == "flood":
                    stages = ", ".join(f"{k} at {v} ft" for k, v in cfg["stages"].items())
                    st.caption(f"Flood stages – {stages}.")
                else:
                    st.caption(cfg["note"])
