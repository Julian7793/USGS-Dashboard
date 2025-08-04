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

from scraper import fetch_usace_brookville_data

usace = fetch_usace_brookville_data()
if usace:
    st.markdown("## 🌊 Brookville Lake (USACE Data)")
    st.markdown(
        f"**Elevation:** {usace.get('elevation', 'N/A')} ft  \n"
        f"**Inflow:** {usace.get('inflow', 'N/A')} cfs  \n"
        f"**Outflow:** {usace.get('outflow', 'N/A')} cfs  \n"
        f"**Storage:** {usace.get('storage', 'N/A')} ac‑ft  \n"
        f"**Precipitation:** {usace.get('precipitation', 'N/A')} in"
    )
else:
    st.error("⚠️ Could not load Brookville Reservoir data.")



# --- LAST UPDATED FOOTER ---
updated_time = datetime.now().strftime('%Y-%m-%d %I:%M %p')
st.markdown("---")
st.caption(f"🔄 Last updated: {updated_time}")
