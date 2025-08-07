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


# --- PAGE CONFIG ---
st.set_page_config(page_title="USGS Water Graphs", layout="wide")

# --- STYLE: trim padding, tighten column gaps, fix image height for 3x2 on 1080p ---
st.markdown(
    """
    <style>
      /* Keep everything snug for a 1920x1080 kiosk */
      .block-container {
        padding-top: 0 !important;
        padding-left: 8px !important;
        padding-right: 8px !important;
        max-width: 1920px !important;
      }
      /* Hide Streamlit chrome */
      header[data-testid="stHeader"], footer { display: none !important; }

      /* Reduce gutters between columns */
      [data-testid="column"] {
        padding-left: 8px !important;
        padding-right: 8px !important;
      }

      /* Make markdown blocks not add big margins */
      .stMarkdown, .stMarkdown p { margin: 0 !important; }

      /* Graph sizing:
         Two rows should fill most of the height.
         46vh x 2 = 92vh (leaves ~8vh for tiny margins).
      */
      img.graph-img {
        width: 100%;
        height: 46vh;           /* <- adjust to 45–48vh to taste */
        max-height: 46vh;
        object-fit: contain;    /* preserve aspect ratio, no cropping */
        display: block;
      }
    </style>
    """,
    unsafe_allow_html=True,
)

# --- AUTOREFRESH ---
REFRESH_INTERVAL = 300  # seconds
st_autorefresh(interval=REFRESH_INTERVAL * 1000, limit=None, key="autorefresh")

# --- DATA ---
data = fetch_site_graphs()

# Add custom site manually (East Fork Whitewater River near Abington)
data.append({
    "title": "East Fork Whitewater River near Abington",
    "page_url": "https://waterdata.usgs.gov/monitoring-location/USGS-03274615",
    "image_url": "https://waterdata.usgs.gov/nwisweb/graph?agency_cd=USGS&site_no=03274615&parm_cd=00065&period=7"
})

# Keep only 6 graphs for a clean 3x2 grid on 1080p
grid_items = [d for d in data if d.get("image_url")][:6]

# --- 3x2 GRID ---
cols = st.columns(3)
for idx, item in enumerate(grid_items):
    with cols[idx % 3]:
        st.markdown(
            f"<img src='{item['image_url']}' class='graph-img' alt='Graph'>",
            unsafe_allow_html=True,
        )

# --- USACE BROOKVILLE (compact, below the grid) ---
usace = fetch_usace_brookville_data()
if usace:
    st.markdown("<div style='height:4vh'></div>", unsafe_allow_html=True)  # small spacer
    st.markdown("### Brookville Lake (USACE Data)")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(
            f"<span style='font-size:125%'>Elevation=  {usace['elevation'] or 'N/A'}</span>",
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            f"<span style='font-size:125%'>Inflow=  {usace['inflow'] or 'N/A'}</span>",
            unsafe_allow_html=True,
        )
        st.markdown(format_delta(usace.get("inflow_delta"), usace.get("inflow_unit")), unsafe_allow_html=True)
    with c3:
        st.markdown(
            f"<span style='font-size:125%'>Outflow=  {usace['outflow'] or 'N/A'}</span>",
            unsafe_allow_html=True,
        )
        st.markdown(format_delta(usace.get("outflow_delta"), usace.get("outflow_unit")), unsafe_allow_html=True)
    with c4:
        st.markdown(
            f"<span style='font-size:125%'>Storage=  {usace['storage'] or 'N/A'}</span>",
            unsafe_allow_html=True,
        )
        st.markdown(format_delta(usace.get("storage_delta"), usace.get("storage_unit")), unsafe_allow_html=True)
    st.markdown(
        f"<span style='font-size:120%'>Precipitation=  {usace['precipitation'] or 'N/A'}</span>",
        unsafe_allow_html=True,
    )
else:
    st.error("⚠️ Could not load Brookville Reservoir data.")

# --- LAST UPDATED FOOTER (small) ---
updated_time = datetime.now().strftime('%Y-%m-%d %I:%M %p')
st.caption(f"🔄 Last updated: {updated_time}")
