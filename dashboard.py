import streamlit as st
from scraper import fetch_site_graphs
from datetime import datetime
import pytz
from streamlit_autorefresh import st_autorefresh
import requests

# Streamlit UI tweaks
st.set_page_config(layout="wide")
st.markdown("""
<style>
  .block-container { padding-top:0; }
  #MainMenu, header, footer {visibility:hidden;}
  .css-1lcbmh3 > div {gap:1rem;}
  h4 {margin-top:0;}
</style>
""", unsafe_allow_html=True)

REFRESH_INTERVAL = 300
eastern = pytz.timezone("US/Eastern")
BROOKVILLE_SITE_NO = "03275990"
BROOKVILLE_AVG_LEVEL = 748

st.header("📈 Live Water Graphs / Elevation")
st.caption(f"🔄 Updated: {datetime.now(eastern).strftime('%Y‑%m‑%d %I:%M %p')}")

st_autorefresh(interval=REFRESH_INTERVAL * 1000, limit=None, key="auto")

# USACE pool elevation fetch
def fetch_usace_pool():
    try:
        resp = requests.get("https://water.sec.usace.army.mil/overview/lrl/locations/brookville", timeout=10)
        resp.raise_for_status()
        text = resp.text
        # look for "current pool elevation is X feet"
        import re
        m = re.search(r"current pool elevation is ([\d\.]+) feet", text)
        return float(m.group(1)) if m else None
    except Exception:
        return None

usace_elev = fetch_usace_pool()

# Fetch USGS graphs
data = fetch_site_graphs()

# Add USACE entry separately
data.insert(1, {
    "site_no": "USACE-POOL",
    "title": "Brookville Lake Elevation (USACE)",
    "image_url": None,
    "page_url": "https://water.sec.usace.army.mil/overview/lrl/locations/brookville"
})

# USGS stage fetch functions should be as before...
from scraper import live_stage_data, get_river_safety_status, get_lake_status

live = live_stage_data(list(d["site_no"] for d in data if d["site_no"].startswith("0")))

cols = st.columns(3)
for idx, d in enumerate(data):
    with cols[idx % 3]:
        st.markdown(f"**{d['title']}**")
        if d["image_url"]:
            st.image(d["image_url"], use_container_width=True)
        elif d["site_no"] == "USACE-POOL":
            if usace_elev is not None:
                status = get_lake_status(usace_elev)
                st.markdown(f"**Elevation:** {usace_elev:.2f} ft – {status}")
            else:
                st.markdown("**Elevation:** ❔ Unknown")
        else:
            st.warning("⚠️ No image found.")
        # USGS or pool status below:
        if d["site_no"].startswith("0"):
            val = live.get(d["site_no"])
            st.markdown(f"**Status:** {get_river_safety_status(d['site_no'], val) if d['site_no'] != BROOKVILLE_SITE_NO else get_lake_status(val)}")
            # add caption logic if needed

updated = datetime.now(eastern)
st.caption(f"Last updated: {updated.strftime('%Y‑%m‑%d %I:%M %p %Z')}")
