import time
from datetime import datetime
import streamlit as st
from streamlit_autorefresh import st_autorefresh

from scraper import fetch_site_graphs, fetch_usace_brookville_data

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

# --- PAGE CONFIG ---
st.set_page_config(page_title="USGS Water Graphs", layout="wide")

# --- STYLE: remove padding, header/footer, status bar, and top line ---
st.markdown(
    """
    <style>
      /* Remove all Streamlit default padding/margins */
      .block-container {
        padding-top: 0 !important;
        padding-bottom: 0 !important;
        padding-left: 8px !important;
        padding-right: 8px !important;
        max-width: 1920px !important;
      }
      header[data-testid="stHeader"], footer { display: none !important; }
      div[data-testid="stStatusWidget"] { display: none !important; } /* status bar */
      div[data-testid="stDecoration"] { display: none !important; } /* colored top line */
      [data-testid="column"] { padding-left: 8px !important; padding-right: 8px !important; }
      .stMarkdown, .stMarkdown p { margin: 0 !important; }
      img.graph-img {
        width: 100%;
        height: 46vh;
        max-height: 46vh;
        object-fit: contain;
        display: block;
      }
    </style>
    """,
    unsafe_allow_html=True,
)

# --- AUTOREFRESH ---
REFRESH_INTERVAL = 300
st_autorefresh(interval=REFRESH_INTERVAL * 1000, limit=None, key="autorefresh")

# --- USGS GRAPHS (cached) ---
@st.cache_data(ttl=3600, show_spinner=False)
def get_usgs_graphs():
    return fetch_site_graphs()

data = get_usgs_graphs()

# Add custom site manually
data.append({
    "title": "East Fork Whitewater River near Abington",
    "page_url": "https://waterdata.usgs.gov/monitoring-location/USGS-03274615",
    "image_url": "https://waterdata.usgs.gov/nwisweb/graph?agency_cd=USGS&site_no=03274615&parm_cd=00065&period=7"
})

# --- USACE DATA (always refetch) ---
usace = fetch_usace_brookville_data()

# --- 3×2 GRID ---
cols = st.columns(3)
graph_count = 0

bucket_15m = int(time.time() // (15 * 60))

for idx in range(5):
    with cols[idx % 3]:
        if graph_count < len(data) and data[graph_count].get("image_url"):
            img_url = data[graph_count]["image_url"]
            sep = "&" if "?" in img_url else "?"
            img_url_cb = f"{img_url}{sep}_cb={bucket_15m}"
            st.markdown(
                f"<img src='{img_url_cb}' class='graph-img' alt='Graph'>",
                unsafe_allow_html=True,
            )
        else:
            st.warning("⚠️ No image found.")
        graph_count += 1

# Last cell = USACE data
with cols[2]:
    if usace:
        st.markdown("### Brookville Lake (USACE Data)")
        st.markdown(
            f"<span style='font-size:125%'>Elevation=  {usace['elevation'] or 'N/A'}</span>",
            unsafe_allow_html=True,
        )

        io_cols = st.columns(2)
        with io_cols[0]:
            st.markdown(
                f"<span style='font-size:125%'>Inflow=  {usace['inflow'] or 'N/A'}</span>",
                unsafe_allow_html=True,
            )
            st.markdown(format_delta(usace.get("inflow_delta"), usace.get("inflow_unit")), unsafe_allow_html=True)

        with io_cols[1]:
            st.markdown(
                f"<span style='font-size:125%'>Outflow=  {usace['outflow'] or 'N/A'}</span>",
                unsafe_allow_html=True,
            )
            st.markdown(format_delta(usace.get("outflow_delta"), usace.get("outflow_unit")), unsafe_allow_html=True)

        st.markdown(
            f"<span style='font-size:125%'>Storage=  {usace['storage'] or 'N/A'}</span>",
            unsafe_allow_html=True,
        )
        st.markdown(format_delta(usace.get("storage_delta"), usace.get("storage_unit")), unsafe_allow_html=True)

        st.markdown(
            f"<span style='font-size:125%'>Precipitation=  {usace['precipitation'] or 'N/A'}</span>",
            unsafe_allow_html=True,
        )
    else:
        st.error("⚠️ Could not load Brookville Reservoir data.")

# --- LAST UPDATED FOOTER (no emoji) ---
updated_time = datetime.now().strftime('%Y-%m-%d %I:%M %p')
st.caption(f"Last updated: {updated_time}")
