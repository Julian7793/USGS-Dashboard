import streamlit as st
from scraper import fetch_site_graphs
from datetime import datetime
from streamlit_autorefresh import st_autorefresh
from scraper import fetch_usace_brookville_data


def format_delta(delta, unit):
    """Return HTML snippet showing 24 hour change with color coding."""
    if delta is None:
        text = "24 hour change: N/A"
        color = "gray"
    else:
        color = "green" if delta > 0 else "red" if delta < 0 else "gray"
        sign = "+" if delta > 0 else ""
        text = f"24 hour change: {sign}{delta:.2f} {unit}"
    return f'<span style="font-size:1em;color:{color}">{text}</span>'

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

usace = fetch_usace_brookville_data()
if usace:
    with cols[2]:
        # Display USACE Brookville Lake metrics
        st.markdown("### Brookville Lake (USACE Data)")
        st.text(f"Elevation=  {usace['elevation'] or 'N/A'}")
        st.text(f"Inflow=  {usace['inflow'] or 'N/A'}")
        st.markdown(
            format_delta(usace.get("inflow_delta"), usace.get("inflow_unit")),
            unsafe_allow_html=True,
        )
        st.text(f"Outflow=  {usace['outflow'] or 'N/A'}")
        st.markdown(
            format_delta(usace.get("outflow_delta"), usace.get("outflow_unit")),
            unsafe_allow_html=True,
        )
        st.text(f"Storage=  {usace['storage'] or 'N/A'}")
        st.markdown(
            format_delta(usace.get("storage_delta"), usace.get("storage_unit")),
            unsafe_allow_html=True,
        )
        st.text(f"Precipitation=  {usace['precipitation'] or 'N/A'}")
else:
    st.error("⚠️ Could not load Brookville Reservoir data.")




# --- LAST UPDATED FOOTER ---
updated_time = datetime.now().strftime('%Y-%m-%d %I:%M %p')
st.markdown("---")
st.caption(f"🔄 Last updated: {updated_time}")
