import streamlit as st
from scraper import fetch_site_graphs
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

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

# Configure Streamlit
st.set_page_config(page_title="USGS Water Graphs", layout="wide")
st_autorefresh(interval=REFRESH_INTERVAL * 1000, limit=None, key="autorefresh")

# Fetch site graph data
data = fetch_site_graphs()

# Add custom site manually (East Fork Whitewater River near Abington)
data.append({
    "title": "East Fork Whitewater River near Abington",
    "page_url": "https://waterdata.usgs.gov/monitoring-location/USGS-03274615",
    "image_url": "https://waterdata.usgs.gov/nwisweb/graph?agency_cd=USGS&site_no=03274615&parm_cd=00065&period=7"
})

# --- DISPLAY GRAPHS ONLY ---
st.markdown("---")

cols = st.columns(3)
for idx, item in enumerate(data):
    with cols[idx % 3]:
        if item["image_url"]:
            st.image(item["image_url"], use_container_width=True)
        else:
            st.warning("⚠️ No image found.")

# --- LAST UPDATED FOOTER ---
updated_time = datetime.now().strftime('%Y-%m-%d %I:%M %p')
st.markdown("---")
st.caption(f"🔄 Last updated: {updated_time}")
