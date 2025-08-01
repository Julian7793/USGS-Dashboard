import streamlit as st
from scraper import fetch_site_graphs
from datetime import datetime
import pytz
from streamlit_autorefresh import st_autorefresh
import requests

# --- PAGE CONFIG: Wide layout for bigger graphs ---
st.set_page_config(layout="wide")

# --- REMOVE TOP PADDING AND HIDE STREAMLIT UI ---
st.markdown(
    """
    <style>
      .block-container {
        padding-top: 0rem;
        padding-bottom: 0rem;
        margin-top: 0rem;
      }
      #MainMenu, footer, header {
        visibility: hidden;
      }
      h1, h2, h3, h4, h5, h6 {
        margin-top: 0rem;
        padding-top: 0rem;
      }
      img {
        margin-top: 0rem;
      }
      .css-1lcbmhc.e1fqkh3o3 > div {
          gap: 1rem;
      }
    </style>
    """,
    unsafe_allow_html=True,
)

# Constants
REFRESH_INTERVAL = 300
eastern = pytz.timezone("US/Eastern")
BROOKVILLE_AVG_LEVEL = 748
BROOKVILLE_SITE_NO = "03275990"

# Auto-refresh every 5 minutes
st_autorefresh(interval=REFRESH_INTERVAL * 1000, limit=None, key="autorefresh")

data = fetch_site_graphs()

# Remove Brookville USGS graph if it exists
data = [item for item in data if "Brookville" not in item["title"]]

# Add custom USACE Brookville Reservoir graph
data.insert(1, {
    "title": "Brookville Reservoir (USACE)",
    "page_url": "https://water.usace.army.mil/overview/lrl/locations/brookville",
    "image_url": "https://water.usace.army.mil/img/graphs/lrl/brookville/brookville_reservoir_7day.png"
})

# Add custom East Fork Whitewater River near Abington graph
data.append({
    "title": "East Fork Whitewater River near Abington",
    "page_url": "https://waterdata.usgs.gov/monitoring-location/USGS-03274615",
    "image_url": "https://waterdata.usgs.gov/nwisweb/graph?agency_cd=USGS&site_no=03274615&parm_cd=00065&period=7"
})

# --- USGS STAGES FETCHER ---
def fetch_live_stages(site_ids):
    lake_site = BROOKVILLE_SITE_NO
    river_sites = [sid for sid in site_ids if sid != lake_site]
    stages = {}

    if river_sites:
        try:
            resp = requests.get(
                "https://waterservices.usgs.gov/nwis/iv/",
                params={"format": "json", "sites": ",".join(river_sites), "parameterCd": "00065", "siteStatus": "all"},
                timeout=10
            )
            resp.raise_for_status()
            data_json = resp.json()
            for ts in data_json["value"]["timeSeries"]:
                sid = ts["sourceInfo"]["siteCode"][0]["value"]
                vals = ts["values"][0]["value"]
                stages[sid] = float(vals[-1]["value"]) if vals else None
        except requests.RequestException:
            for sid in river_sites:
                stages[sid] = None

    try:
        resp = requests.get(
            "https://waterservices.usgs.gov/nwis/iv/",
            params={"format": "json", "sites": lake_site, "parameterCd": "62614", "siteStatus": "all"},
            timeout=10
        )
        resp.raise_for_status()
        data_json = resp.json()
        for ts in data_json["value"]["timeSeries"]:
            sid = ts["sourceInfo"]["siteCode"][0]["value"]
            vals = ts["values"][0]["value"]
            stages[sid] = float(vals[-1]["value"]) if vals else None
    except requests.RequestException:
        stages[lake_site] = None

    return stages

# Station config
station_limits = {
    "03274650": {"type": "operational", "min": 2.26, "max": 13.98,
                 "min_msg": "Lower intake out of water", "max_msg": "Float hitting bottom of gage shelf"},
    "03276000": {"type": "operational", "min": 0.69, "max": 25.72,
                 "min_msg": "Lower intake out of water", "max_msg": "Float hitting bottom of gage shelf"},
    "03275000": {"type": "flood", "stages": {"Action": 10, "Minor": 14, "Moderate": 17, "Major": 19}},
    "03276500": {"type": "flood", "stages": {"Action": 14, "Minor": 20, "Moderate": 23, "Major": 29}},
    "03275990": {"type": "lake", "note": "Lake or reservoir water surface elevation above NGVD 1929, ft"},
    "03274615": {"type": "flood", "stages": {"Action": 14, "Minor": 16, "Moderate": 24, "Major": 30}}
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
        st.markdown(
            f'<div style="font-size:0.9rem; text-align:center;"><a href="{item["page_url"]}">{display_title}</a></div>',
            unsafe_allow_html=True
        )

        if item["image_url"]:
            st.image(item["image_url"], use_container_width=True)
        else:
            st.warning("⚠️ No image found.")

        sid = item["page_url"].split("-")[-1] if "USGS" in item["page_url"] else None
        val = live_stages.get(sid)

        if sid == BROOKVILLE_SITE_NO:
            status = get_lake_status(val)
            st.markdown(f"**Lake Status:** {val:.2f} ft – {status}" if val is not None else f"**Lake Status:** ❔ No data – {status}")
        elif sid in station_limits:
            river_status = get_river_safety_status(sid, val)
            st.markdown(f"**River Status:** {river_status}")
        else:
            st.markdown("**Status:** Not configured")

        if sid == "03274615":
            st.caption(
                "Flood stages in ft  \n"
                "14 – Action stage  \n"
                "16 – Minor flood  \n"
                "24 – Moderate flood  \n"
                "30 – Major flood"
            )
        else:
            cfg = station_limits.get(sid)
            if cfg:
                if cfg["type"] == "operational":
                    st.caption(f"Operational limits: {cfg['min']} ft (min), {cfg['max']} ft (max).")
                elif cfg["type"] == "flood":
                    stages = ", ".join(f"{k} at {v} ft" for k, v in cfg["stages"].items())
                    st.caption(f"Flood stages – {stages}.")
                else:
                    st.caption(cfg["note"])

# Last updated timestamp
updated_time = datetime.now(eastern)
st.caption(f"🔄 Last updated: {updated_time.strftime('%Y-%m-%d %I:%M %p %Z')}")

# Fetch all USGS graphs
data = fetch_site_graphs()

# Remove the Brookville USGS site (03274650) from the list
data = [d for d in data if not d["page_url"].endswith("03274650")]

# Add custom USACE Brookville Reservoir graph
data.insert(1, {
    "title": "Brookville Reservoir (USACE)",
    "page_url": "https://water.usace.army.mil/overview/lrl/locations/brookville",
    "image_url": "https://water.usace.army.mil/api/projects/lrl/locations/brookville/graphs/pool-elevations?period=7d"
})

# Add East Fork Whitewater River near Abington
data.append({
    "title": "East Fork Whitewater River near Abington",
    "page_url": "https://waterdata.usgs.gov/monitoring-location/USGS-03274615",
    "image_url": "https://waterdata.usgs.gov/nwisweb/graph?agency_cd=USGS&site_no=03274615&parm_cd=00065&period=7"
})

# --- USGS STAGES FETCHER ---
def fetch_live_stages(site_ids):
    lake_site = BROOKVILLE_SITE_NO
    river_sites = [sid for sid in site_ids if sid != lake_site]
    stages = {}

    if river_sites:
        try:
            resp = requests.get(
                "https://waterservices.usgs.gov/nwis/iv/",
                params={"format":"json","sites":",".join(river_sites),"parameterCd":"00065","siteStatus":"all"},
                timeout=10
            )
            resp.raise_for_status()
            data_json = resp.json()
            for ts in data_json["value"]["timeSeries"]:
                sid = ts["sourceInfo"]["siteCode"][0]["value"]
                vals = ts["values"][0]["value"]
                stages[sid] = float(vals[-1]["value"]) if vals else None
        except requests.RequestException:
            for sid in river_sites:
                stages[sid] = None

    try:
        resp = requests.get(
            "https://waterservices.usgs.gov/nwis/iv/",
            params={"format":"json","sites":lake_site,"parameterCd":"62614","siteStatus":"all"},
            timeout=10
        )
        resp.raise_for_status()
        data_json = resp.json()
        for ts in data_json["value"]["timeSeries"]:
            sid = ts["sourceInfo"]["siteCode"][0]["value"]
            vals = ts["values"][0]["value"]
            stages[sid] = float(vals[-1]["value"]) if vals else None
    except requests.RequestException:
        stages[lake_site] = None

    return stages

# Station config
station_limits = {
    "03276000": {"type":"operational","min":0.69,"max":25.72,
                 "min_msg":"Lower intake out of water","max_msg":"Float hitting bottom of gage shelf"},
    "03275000": {"type":"flood","stages":{"Action":10,"Minor":14,"Moderate":17,"Major":19}},
    "03276500": {"type":"flood","stages":{"Action":14,"Minor":20,"Moderate":23,"Major":29}},
    "03275990": {"type":"lake","note":"Lake or reservoir water surface elevation above NGVD 1929, ft"},
    "03274615": {"type":"flood","stages":{"Action":14,"Minor":16,"Moderate":24,"Major":30}}
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

# Fetch live data
try:
    live_stages = fetch_live_stages(list(station_limits.keys()))
except Exception as e:
    st.error(f"⚠️ Failed to fetch USGS data: {e}")
    live_stages = {}

# --- DISPLAY ---
cols = st.columns(3)
for idx, item in enumerate(data):
    with cols[idx % 3]:
        display_title = item["title"].split(" - ")[0]
        st.markdown(
            f'<div style="font-size:0.9rem; text-align:center;"><a href="{item["page_url"]}">{display_title}</a></div>',
            unsafe_allow_html=True
        )

        if item["image_url"]:
            st.image(item["image_url"], use_container_width=True)
        else:
            st.warning("⚠️ No image found.")

        sid = item["page_url"].split("-")[-1]
        val = live_stages.get(sid)

        if sid == BROOKVILLE_SITE_NO:
            status = get_lake_status(val)
            st.markdown(f"**Lake Status:** {val:.2f} ft – {status}" if val is not None else f"**Lake Status:** ❔ No data – {status}")
        elif sid in station_limits:
            river_status = get_river_safety_status(sid, val)
            st.markdown(f"**River Status:** {river_status}")
        else:
            st.markdown("**Status:** Not configured")

        if sid == "03274615":
            st.caption(
                "Flood stages in ft  \n"
                "14 – Action stage  \n"
                "16 – Minor flood  \n"
                "24 – Moderate flood  \n"
                "30 – Major flood"
            )
        else:
            cfg = station_limits.get(sid)
            if cfg:
                if cfg["type"] == "operational":
                    st.caption(f"Operational limits: {cfg['min']} ft (min), {cfg['max']} ft (max).")
                elif cfg["type"] == "flood":
                    stages = ", ".join(f"{k} at {v} ft" for k, v in cfg["stages"].items())
                    st.caption(f"Flood stages – {stages}.")
                else:
                    st.caption(cfg["note"])

# Timestamp
updated_time = datetime.now(eastern)
st.caption(f"🔄 Last updated: {updated_time.strftime('%Y-%m-%d %I:%M %p %Z')}")
            )
            resp.raise_for_status()
            data_json = resp.json()
            for ts in data_json["value"]["timeSeries"]:
                sid = ts["sourceInfo"]["siteCode"][0]["value"]
                vals = ts["values"][0]["value"]
                stages[sid] = float(vals[-1]["value"]) if vals else None
        except requests.RequestException:
            for sid in river_sites:
                stages[sid] = None

    try:
        resp = requests.get(
            "https://waterservices.usgs.gov/nwis/iv/",
            params={"format":"json","sites":lake_site,"parameterCd":"62614","siteStatus":"all"},
            timeout=10
        )
        resp.raise_for_status()
        data_json = resp.json()
        for ts in data_json["value"]["timeSeries"]:
            sid = ts["sourceInfo"]["siteCode"][0]["value"]
            vals = ts["values"][0]["value"]
            stages[sid] = float(vals[-1]["value"]) if vals else None
    except requests.RequestException:
        stages[lake_site] = None

    return stages

# Station config
station_limits = {
    "03276000": {"type":"operational","min":0.69,"max":25.72,
                 "min_msg":"Lower intake out of water","max_msg":"Float hitting bottom of gage shelf"},
    "03275000": {"type":"flood","stages":{"Action":10,"Minor":14,"Moderate":17,"Major":19}},
    "03276500": {"type":"flood","stages":{"Action":14,"Minor":20,"Moderate":23,"Major":29}},
    "03275990": {"type":"lake","note":"Lake or reservoir water surface elevation above NGVD 1929, ft"},
    "03274615": {"type":"flood","stages":{"Action":14,"Minor":16,"Moderate":24,"Major":30}}
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

# Fetch live data
try:
    live_stages = fetch_live_stages(list(station_limits.keys()))
except Exception as e:
    st.error(f"⚠️ Failed to fetch USGS data: {e}")
    live_stages = {}

# --- DISPLAY ---
cols = st.columns(3)
for idx, item in enumerate(data):
    with cols[idx % 3]:
        display_title = item["title"].split(" - ")[0]
        st.markdown(
            f'<div style="font-size:0.9rem; text-align:center;"><a href="{item["page_url"]}">{display_title}</a></div>',
            unsafe_allow_html=True
        )

        if item["image_url"]:
            st.image(item["image_url"], use_container_width=True)
        else:
            st.warning("⚠️ No image found.")

        sid = item["page_url"].split("-")[-1]
        val = live_stages.get(sid)

        if sid == BROOKVILLE_SITE_NO:
            status = get_lake_status(val)
            st.markdown(f"**Lake Status:** {val:.2f} ft – {status}" if val is not None else f"**Lake Status:** ❔ No data – {status}")
        elif sid in station_limits:
            river_status = get_river_safety_status(sid, val)
            st.markdown(f"**River Status:** {river_status}")
        else:
            st.markdown("**Status:** Not configured")

        if sid == "03274615":
            st.caption(
                "Flood stages in ft  \n"
                "14 – Action stage  \n"
                "16 – Minor flood  \n"
                "24 – Moderate flood  \n"
                "30 – Major flood"
            )
        else:
            cfg = station_limits.get(sid)
            if cfg:
                if cfg["type"] == "operational":
                    st.caption(f"Operational limits: {cfg['min']} ft (min), {cfg['max']} ft (max).")
                elif cfg["type"] == "flood":
                    stages = ", ".join(f"{k} at {v} ft" for k, v in cfg["stages"].items())
                    st.caption(f"Flood stages – {stages}.")
                else:
                    st.caption(cfg["note"])

# Timestamp
updated_time = datetime.now(eastern)
st.caption(f"🔄 Last updated: {updated_time.strftime('%Y-%m-%d %I:%M %p %Z')}")
})

# --- 7‑Day WEATHER FORECAST REMOVED PER PREVIOUS REQUEST ---

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
            data_json = resp.json()
            for ts in data_json["value"]["timeSeries"]:
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
        data_json = resp.json()
        for ts in data_json["value"]["timeSeries"]:
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
        # Centered, smaller font graph title
        st.markdown(
            f'<div style="font-size:0.9rem; text-align:center;"><a href="{item["page_url"]}">{display_title}</a></div>',
            unsafe_allow_html=True
        )

        # Show graph filling the column width
        if item["image_url"]:
            st.image(item["image_url"], use_container_width=True)
        else:
            st.warning("⚠️ No image found.")

        # Determine site ID from URL
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
            st.caption(
                "Flood stages in ft  \n"
                "14 – Action stage  \n"
                "16 – Minor flood  \n"
                "24 – Moderate flood  \n"
                "30 – Major flood"
            )
        else:
            cfg = station_limits.get(sid)
            if cfg:
                if cfg["type"] == "operational":
                    st.caption(f"Operational limits: {cfg['min']} ft (min), {cfg['max']} ft (max).")
                elif cfg["type"] == "flood":
                    stages = ", ".join(f"{k} at {v} ft" for k, v in cfg["stages"].items())
                    st.caption(f"Flood stages – {stages}.")
                else:
                    st.caption(cfg["note"])

# Last updated timestamp at the bottom
updated_time = datetime.now(eastern)
st.caption(f"🔄 Last updated: {updated_time.strftime('%Y-%m-%d %I:%M %p %Z')}")
