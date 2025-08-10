import base64
import time
from datetime import datetime, timedelta

import requests
import streamlit as st
from streamlit_autorefresh import st_autorefresh

from scraper import fetch_site_graphs, fetch_usace_brookville_data

# -------------------------------
# Helper for 24h delta formatting (kept for IO/Storage only)
# -------------------------------
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

# -------------------------------
# STYLE: remove all padding/margins & header/footer (kiosk-like)
# -------------------------------
st.markdown(
    """
    <style>
      .block-container {
        padding-top: 0 !important;
        padding-bottom: 0 !important;
        padding-left: 8px !important;
        padding-right: 8px !important;
        max-width: 1920px !important;
      }
      header[data-testid="stHeader"], footer { display: none !important; }

      div[data-testid="stVerticalBlock"] > div:first-child {
        margin-top: 0 !important;
        padding-top: 0 !important;
      }
      [data-testid="column"] {
        padding-left: 8px !important;
        padding-right: 8px !important;
      }
      .stMarkdown, .stMarkdown p { margin: 0 !important; }
      img.graph-img {
        width: 100%;
        height: 46vh; /* fits two rows exactly */
        max-height: 46vh;
        object-fit: contain;
      }
    </style>
    """,
    unsafe_allow_html=True,
)

# -------------------------------
# Smart rerun timing (align to USGS 15-min cadence)
# -------------------------------
def seconds_until_next_quarter_hour(grace_seconds: int = 120) -> int:
    now = datetime.now()
    next_q = (now.replace(second=0, microsecond=0)
              + timedelta(minutes=15 - (now.minute % 15)))
    wait = int((next_q - now).total_seconds()) + grace_seconds
    return max(15, wait)

st_autorefresh(interval=seconds_until_next_quarter_hour() * 1000, limit=None, key="autorefresh")

# -------------------------------
# Option B helpers: server-side image fetch with caching
# -------------------------------
def time_bucket(seconds: int, offset: int = 0) -> int:
    """Return an integer that changes only at the desired cadence."""
    return int((time.time() - offset) // seconds)

def add_cache_buster(url: str, bucket: int) -> str:
    """Append a cache-busting query param so the upstream server returns a fresh image each cadence."""
    sep = "&" if "?" in url else "?"
    return f"{url}{sep}_cb={bucket}"

@st.cache_data(show_spinner=False)
def fetch_image_bytes(url_with_cb: str, bucket: int) -> bytes:
    """Fetch image bytes. 'bucket' participates in the cache key so refetch happens only when cadence ticks."""
    r = requests.get(
        url_with_cb,
        headers={"Cache-Control": "no-cache", "Pragma": "no-cache"},
        timeout=20,
    )
    r.raise_for_status()
    return r.content

def to_data_uri(img_bytes: bytes) -> str:
    return "data:image/png;base64," + base64.b64encode(img_bytes).decode("ascii")

def _sanitize_precip(val):
    if val is None:
        return val
    s = str(val)
    # Extract first number if present
    import re
    m = re.search(r'(-?\d+(?:\.\d+)?)', s)
    if m:
        try:
            num = float(m.group(1))
            # USACE sometimes uses negative sentinels (e.g., -901) for missing precip
            if num <= -900:
                return "0.00 in"
        except Exception:
            pass
    return val

# -------------------------------
# FETCH USGS GRAPH DATA
# -------------------------------
data = fetch_site_graphs()

# Add custom site manually (kept from your version)
data.append({
    "title": "East Fork Whitewater River near Abington",
    "page_url": "https://waterdata.usgs.gov/monitoring-location/USGS-03274615",
    "image_url": "https://waterdata.usgs.gov/nwisweb/graph?agency_cd=USGS&site_no=03274615&parm_cd=00065&period=7"
})

# -------------------------------
# USACE Brookville — make it actually refresh
# -------------------------------
usace = fetch_usace_brookville_data()

# -------------------------------
# 3×2 GRID (5 graphs + 1 USACE panel)
# -------------------------------
cols = st.columns(3)
graph_count = 0

# Compute bucket once per run: 15 min cadence + 2 min grace
bucket_15m = time_bucket(15 * 60, offset=120)

for idx in range(5):
    with cols[idx % 3]:
        if graph_count < len(data) and data[graph_count].get("image_url"):
            img_url = data[graph_count]["image_url"]
            try:
                url_with_cb = add_cache_buster(img_url, bucket_15m)
                img_bytes = fetch_image_bytes(url_with_cb, bucket_15m)
                st.markdown(
                    f"<img src='{to_data_uri(img_bytes)}' class='graph-img' alt='Graph'>",
                    unsafe_allow_html=True,
                )
            except Exception as e:
                st.error(f"⚠️ Could not load image: {e}")
        else:
            st.warning("⚠️ No image found.")
        graph_count += 1

# Last cell = USACE data
with cols[2]:
    if usace:
        st.markdown("### Brookville Lake (USACE Data)")
        # Elevation WITHOUT 24h change (per your request)
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
            st.markdown(
                format_delta(usace.get("inflow_delta"), usace.get("inflow_unit")),
                unsafe_allow_html=True,
            )
        with io_cols[1]:
            st.markdown(
                f"<span style='font-size:125%'>Outflow=  {usace['outflow'] or 'N/A'}</span>",
                unsafe_allow_html=True,
            )
            st.markdown(
                format_delta(usace.get("outflow_delta"), usace.get("outflow_unit")),
                unsafe_allow_html=True,
            )

        st.markdown(
            f"<span style='font-size:125%'>Storage=  {usace['storage'] or 'N/A'}</span>",
            unsafe_allow_html=True,
        )
        st.markdown(
            format_delta(usace.get("storage_delta"), usace.get("storage_unit")),
            unsafe_allow_html=True,
        )

        st.markdown(
            f"<span style='font-size:125%'>Precipitation=  {_sanitize_precip(usace['precipitation']) if 'precipitation' in usace else 'N/A'}</span>",
            unsafe_allow_html=True,
        )
    else:
        st.error("⚠️ Could not load Brookville Reservoir data.")

# -------------------------------
# LAST UPDATED FOOTER
# -------------------------------
updated_time = datetime.now().strftime('%Y-%m-%d %I:%M %p')
st.caption(f"🔄 Last updated: {updated_time}")
