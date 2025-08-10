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

# --- STYLE ---
css = """
<style>
  .block-container {
    padding-top: 0 !important;
    padding-bottom: 0 !important;
    padding-left: 8px !important;
    padding-right: 8px !important;
    max-width: 1920px !important;
    background: transparent !important;
  }
  header[data-testid="stHeader"], footer { display: none !important; }
  div[data-testid="stStatusWidget"] { display: none !important; }
  div[data-testid="stDecoration"] { display: none !important; }

  /* Columns: remove default top spacing and align content to top */
  [data-testid="column"] {
    padding-left: 8px !important;
    padding-right: 8px !important;
    margin-top: 0 !important;
    align-self: flex-start !important;
  }

  .stMarkdown, .stMarkdown p { margin: 0 !important; }
  img.graph-img {
    width: 100%;
    height: 46vh;
    max-height: 46vh;
    object-fit: contain;
    display: block;
    border-radius: 6px;
  }

  /* App background */
  .stApp { background-color: #171717; }

  /* USACE card (same height as graphs) */
  .usace-card {
    background-color: #303030;
    padding: 12px;
    height: 46vh;               /* match graph height */
    display: flex;
    flex-direction: column;
    justify-content: flex-start;
    border-radius: 6px;
    box-sizing: border-box;
  }
</style>
"""
st.markdown(css, unsafe_allow_html=True)

# --- AUTOREFRESH ---
REFRESH_INTERVAL = 300  # 5 minutes
st_autorefresh(interval=REFRESH_INTERVAL * 1000, limit=None, key="autorefresh")

# --- USGS GRAPHS ---
@st.cache_data(ttl=3600, show_spinner=False)
def get_usgs_graphs():
    return fetch_site_graphs()

data = get_usgs_graphs()

data.append({
    "title": "East Fork Whitewater River near Abington",
    "page_url": "https://waterdata.usgs.gov/monitoring-location/USGS-03274615",
    "image_url": "https://waterdata.usgs.gov/nwisweb/graph?agency_cd=USGS&site_no=03274615&parm_cd=00065&period=7"
})

# --- USACE DATA ---
usace = fetch_usace_brookville_data()

# --- LAYOUT ---
bucket_15m = int(time.time() // (15 * 60))  # cache-buster for USGS images

# Row 1: 3 graphs
cols_top = st.columns(3)
graph_idx = 0
for i in range(3):
    with cols_top[i]:
        if graph_idx < len(data) and data[graph_idx].get("image_url"):
            img_url = data[graph_idx]["image_url"]
            sep = "&" if "?" in img_url else "?"
            img_url_cb = f"{img_url}{sep}_cb={bucket_15m}"
            st.markdown(f"<img src='{img_url_cb}' class='graph-img'>", unsafe_allow_html=True)
        else:
            st.warning("⚠️ No image found.")
        graph_idx += 1

# Row 2: 2 graphs + USACE
cols_bottom = st.columns(3)

for i in range(2):  # two graphs left/middle
    with cols_bottom[i]:
        if graph_idx < len(data) and data[graph_idx].get("image_url"):
            img_url = data[graph_idx]["image_url"]
            sep = "&" if "?" in img_url else "?"
            img_url_cb = f"{img_url}{sep}_cb={bucket_15m}"
            st.markdown(f"<img src='{img_url_cb}' class='graph-img'>", unsafe_allow_html=True)
        else:
            st.warning("⚠️ No image found.")
        graph_idx += 1

# Right cell: USACE panel (title + data INSIDE the grey box)
with cols_bottom[2]:
    if usace:
        inflow_delta_html = format_delta(usace.get("inflow_delta"), usace.get("inflow_unit"))
        outflow_delta_html = format_delta(usace.get("outflow_delta"), usace.get("outflow_unit"))
        storage_delta_html = format_delta(usace.get("storage_delta"), usace.get("storage_unit"))

        usace_html = f"""
        <div class="usace-card">
          <h3 style="margin:0 0 8px 0;">Brookville Lake (USACE Data)</h3>

          <div style="font-size:125%; margin-bottom:8px;">
            Elevation= {usace.get('elevation') or 'N/A'}
          </div>

          <div style="display:flex; gap:24px; margin-bottom:8px;">
            <div style="flex:1;">
              <div style="font-size:125%;">Inflow= {usace.get('inflow') or 'N/A'}</div>
              {inflow_delta_html}
            </div>
            <div style="flex:1;">
              <div style="font-size:125%;">Outflow= {usace.get('outflow') or 'N/A'}</div>
              {outflow_delta_html}
            </div>
          </div>

          <div style="font-size:125%; margin-bottom:4px;">
            Storage= {usace.get('storage') or 'N/A'}
          </div>
          {storage_delta_html}

          <div style="font-size:125%; margin-top:8px;">
            Precipitation= {usace.get('precipitation') or 'N/A'}
          </div>
        </div>
        """
        st.markdown(usace_html, unsafe_allow_html=True)
    else:
        st.markdown(
            """
            <div class="usace-card">
              <h3 style="margin:0;">Brookville Lake (USACE Data)</h3>
              <div style="margin-top:8px;">⚠️ Could not load Brookville Reservoir data.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

# --- LAST UPDATED FOOTER ---
updated_time = datetime.now().strftime('%Y-%m-%d %I:%M %p')
st.caption(f"Last updated: {updated_time}")
