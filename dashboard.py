import streamlit as st
from scraper import fetch_site_graphs, live_stage_data, get_river_safety_status, get_lake_status
from datetime import datetime
import pytz
from streamlit_autorefresh import st_autorefresh

# Config
st.set_page_config(layout="wide")
st.markdown("""
<style>
.block-container { padding-top: 0rem; }
#MainMenu, footer, header {visibility: hidden;}
img { margin-top: 0rem; }
</style>
""", unsafe_allow_html=True)

eastern = pytz.timezone("US/Eastern")
REFRESH_INTERVAL = 300
BROOKVILLE_SITE_NO = "03275990"

st_autorefresh(interval=REFRESH_INTERVAL * 1000, limit=None, key="autorefresh")
st.header("📊 Water Level Dashboard")
st.caption(f"🔄 Updated: {datetime.now(eastern).strftime('%Y-%m-%d %I:%M %p %Z')}")

# Fetch data
data = fetch_site_graphs()
live = live_stage_data([d["site_no"] for d in data if d["site_no"].startswith("0")])

cols = st.columns(3)
for idx, item in enumerate(data):
    with cols[idx % 3]:
        title = item["title"]
        st.markdown(f'<div style="text-align:center;"><a href="{item["page_url"]}">{title}</a></div>', unsafe_allow_html=True)

        # Show image if it's a USGS graph
        if item["image_url"]:
            st.image(item["image_url"], use_container_width=True)

        # USACE text panel
        elif item.get("site_no") == "USACE-POOL":
            stats = item.get("usace_panel")
            if stats:
                for key, val in stats.items():
                    st.markdown(f"**{key}:** {val}")
            else:
                st.warning("⚠️ Unable to fetch Brookville data.")
        else:
            st.warning("⚠️ No image found.")

        # Safety status
        sid = item["site_no"]
        if sid.startswith("0"):
            val = live.get(sid)
            if sid == BROOKVILLE_SITE_NO:
                st.markdown(f"**Lake Status:** {get_lake_status(val)}")
            else:
                st.markdown(f"**River Status:** {get_river_safety_status(sid, val)}")
