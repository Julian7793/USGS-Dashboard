import streamlit as st
from scraper import fetch_site_graphs, live_stage_data, get_river_safety_status, get_lake_status
from datetime import datetime
from streamlit_autorefresh import st_autorefresh
import pytz

# Streamlit setup
st.set_page_config(layout="wide")
st.markdown("""
<style>
  .block-container { padding-top:0; }
  #MainMenu, header, footer {visibility:hidden;}
  .css-1lcbmh3 > div {gap:1rem;}
  h4 {margin-top:0;}
</style>
""", unsafe_allow_html=True)

# Constants
REFRESH_INTERVAL = 300  # seconds
eastern = pytz.timezone("US/Eastern")
BROOKVILLE_SITE_NO = "03275990"
BROOKVILLE_AVG_LEVEL = 748

# Refresh every 5 minutes
st_autorefresh(interval=REFRESH_INTERVAL * 1000, limit=None, key="autorefresh")

# Header
st.header("📈 Live Water Graphs / Elevation")
st.caption(f"🔄 Updated: {datetime.now(eastern).strftime('%Y‑%m‑%d %I:%M %p')}")

# Fetch data
data = fetch_site_graphs()
live = live_stage_data([d["site_no"] for d in data if d["site_no"].startswith("0")])

# Layout
cols = st.columns(3)
for idx, d in enumerate(data):
    with cols[idx % 3]:
        st.markdown(f"**{d['title']}**")

        # Display image if available
        if d["image_url"]:
            st.image(d["image_url"], use_container_width=True)
        else:
            st.warning("⚠️ No image available.")

        # Site ID-based status logic
        sid = d["site_no"]
        if sid.startswith("0"):
            val = live.get(sid)
            if sid == BROOKVILLE_SITE_NO:
                st.markdown(f"**Lake Status:** {get_lake_status(val)}" if val is not None else "❔ No lake data")
            else:
                st.markdown(f"**River Status:** {get_river_safety_status(sid, val)}")
        elif sid == "USACE-POOL":
            # USACE pool status
            import scraper  # avoid circular import
            pool_level = scraper.fetch_usace_pool()
            if pool_level is not None:
                st.markdown(f"**Elevation:** {pool_level:.2f} ft – {get_lake_status(pool_level)}")
            else:
                st.markdown("**Elevation:** ❔ Unknown")

        # Optional caption for special site
        if sid == "03274615":
            st.caption(
                "Flood stages in ft  \n"
                "14 – Action stage  \n"
                "16 – Minor flood  \n"
                "24 – Moderate flood  \n"
                "30 – Major flood"
            )

# Timestamp
updated = datetime.now(eastern)
st.caption(f"Last updated: {updated.strftime('%Y‑%m‑%d %I:%M %p %Z')}")
