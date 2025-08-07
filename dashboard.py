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

# --- REMOVE TOP PADDING VIA CSS AND HIDE UI ELEMENTS ---
st.markdown(
    """
    <style>
      .block-container { padding-top: 0rem; }
      header[data-testid="stHeader"], footer {
        opacity: 0;
        transition: opacity 0.3s;
      }
      header[data-testid="stHeader"] {
        border-bottom: none;
      }
      footer {
        border-top: none;
      }
      header[data-testid="stHeader"]:hover,
      footer:hover {
        opacity: 1;
      }
            /* Hide Streamlit's fullscreen button on images/graphs */
      button[title="View fullscreen"], button[aria-label="View fullscreen"] {
        display: none;
      }
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
        st.markdown(
            f"<span style='font-size:133%'>Elevation=  {usace['elevation'] or 'N/A'}</span>",
            unsafe_allow_html=True,
        )
        io_cols = st.columns(2)
        with io_cols[0]:
            st.markdown(
                f"<span style='font-size:133%'>Inflow=  {usace['inflow'] or 'N/A'}</span>",
                unsafe_allow_html=True,
            )
            st.markdown(
                format_delta(usace.get("inflow_delta"), usace.get("inflow_unit")),
                unsafe_allow_html=True,
            )
        with io_cols[1]:
            st.markdown(
                f"<span style='font-size:133%'>Outflow=  {usace['outflow'] or 'N/A'}</span>",
                unsafe_allow_html=True,
            )
            st.markdown(
                format_delta(usace.get("outflow_delta"), usace.get("outflow_unit")),
                unsafe_allow_html=True,
            )
        st.markdown(
            f"<span style='font-size:133%'>Storage=  {usace['storage'] or 'N/A'}</span>",
            unsafe_allow_html=True,
        )
        st.markdown(
            format_delta(usace.get("storage_delta"), usace.get("storage_unit")),
            unsafe_allow_html=True,
        )
        st.markdown(
            f"<span style='font-size:133%'>Precipitation=  {usace['precipitation'] or 'N/A'}</span>",
            unsafe_allow_html=True,
        )
else:
    st.error("⚠️ Could not load Brookville Reservoir data.")




# --- LAST UPDATED FOOTER ---
updated_time = datetime.now().strftime('%Y-%m-%d %I:%M %p')
st.caption(f"🔄 Last updated: {updated_time}")
