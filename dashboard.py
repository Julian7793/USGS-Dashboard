import base64
from io import BytesIO
import time
from datetime import datetime, timedelta, timezone
import requests
import streamlit as st
from streamlit_autorefresh import st_autorefresh

# matplotlib only used to draw the tiny inflow/outflow graph
try:
    import matplotlib
    matplotlib.use("Agg")  # headless backend for servers
    import matplotlib.pyplot as plt
    MATPLOTLIB_OK = True
except Exception:
    MATPLOTLIB_OK = False

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
    overflow: hidden;           /* keep the card tidy */
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
# No cache here so it always refetches on rerun
usace = fetch_usace_brookville_data()

# -------------------------------
# CWMS (USACE) helper: tiny 7-day Inflow/Outflow graph
# -------------------------------
CDA_BASE = "https://cwms-data.usace.army.mil/cwms-data"
OFFICE   = "LRL"  # Louisville

def _utc_now_iso():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

def _iso_ago(days=7):
    return (datetime.now(timezone.utc) - timedelta(days=days)).isoformat().replace("+00:00", "Z")

def _get_json(url, params=None, timeout=20):
    r = requests.get(url, headers={"Accept": "application/json", "User-Agent": "RiverStats/1.0"}, params=params or {}, timeout=timeout)
    r.raise_for_status()
    return r.json()

def _catalog_timeseries(name_like):
    url = f"{CDA_BASE}/catalog/TIMESERIES"
    params = {"office": OFFICE, "name-like": name_like, "page-size": 1000}
    try:
        j = _get_json(url, params=params)
        entries = j.get("entries", []) if isinstance(j, dict) else []
        return [e.get("name") for e in entries if "name" in e]
    except Exception:
        return []

def _pick_best(names, needles):
    def ok(n):
        s = n.lower()
        return all(needle.lower() in s for needle in needles)
    # prefer instantaneous/short interval
    ranked = []
    for n in names:
        if ok(n):
            s = n.lower()
            rank = 0
            if ".inst" in s: rank += 3
            if ".15minute" in s or ".15-min" in s: rank += 2
            if ".1hour" in s: rank += 1
            ranked.append((rank, n))
    ranked.sort(reverse=True)
    return ranked[0][1] if ranked else None

def _fetch_timeseries(name, begin, end):
    if not name:
        return []
    url = f"{CDA_BASE}/timeseries"
    params = {"office": OFFICE, "name": name, "begin": begin, "end": end, "page-size": 10000, "format": "json"}
    try:
        j = _get_json(url, params=params)
    except Exception:
        return []
    vals = []
    data = j.get("values") or j.get("values-ts") or j.get("valuesArray") or []
    if isinstance(data, list):
        if data and isinstance(data[0], dict) and "time" in data[0]:
            for v in data:
                vals.append((v.get("time"), v.get("value")))
        elif data and isinstance(data[0], list):
            for row in data:
                if len(row) >= 2:
                    vals.append((row[0], row[1]))
    return vals

def _io_graph_data_uri(days=7):
    """
    Build a base64 PNG data URI for a small Inflow/Outflow line chart (last `days`).
    Returns None if series not found or matplotlib unavailable.
    """
    if not MATPLOTLIB_OK:
        return None

    # discover series names
    candidates = set()
    for hint in ["BROK1", "BROOKVILLE", "BROOKVILLE LAKE", "BROOKVILLE LK", "BROOKVILLE DAM"]:
        candidates.update(_catalog_timeseries(f"%{hint}%"))

    infl_name = _pick_best(candidates, ["flow-res in"]) or _pick_best(candidates, ["inflow"])
    out_name  = _pick_best(candidates, ["flow-res out"]) or _pick_best(candidates, ["outflow"])

    if not infl_name or not out_name:
        return None

    end = _utc_now_iso()
    begin = _iso_ago(days)

    infl = _fetch_timeseries(infl_name, begin, end)
    out  = _fetch_timeseries(out_name,  begin, end)
    if not infl and not out:
        return None

    # convert ISO → datetime, pairs to lists (align by time visually; no resampling)
    def to_xy(series):
        xs, ys = [], []
        for t_iso, v in series:
            try:
                t = datetime.fromisoformat(str(t_iso).replace("Z", "+00:00"))
                xs.append(t)
                ys.append(float(v))
            except Exception:
                continue
        return xs, ys

    x_in, y_in = to_xy(infl)
    x_out, y_out = to_xy(out)

    # draw
    fig = plt.figure(figsize=(6.6, 2.0), dpi=150)
    ax = fig.add_subplot(111)
    fig.patch.set_facecolor("#303030")
    ax.set_facecolor("#303030")
    ax.grid(True, color="#555555", linewidth=0.5, alpha=0.6)

    if x_in:
        ax.plot(x_in, y_in, linewidth=1.6, label="Inflow (cfs)")
    if x_out:
        ax.plot(x_out, y_out, linewidth=1.6, label="Outflow (cfs)")

    ax.set_ylabel("cfs", color="#DDDDDD")
    ax.tick_params(colors="#DDDDDD")
    ax.spines["bottom"].set_color("#777777")
    ax.spines["left"].set_color("#777777")
    ax.set_title("Inflow / Outflow (last 7 days)", color="#DDDDDD", pad=4, fontsize=10)
    ax.legend(loc="upper right", facecolor="#404040", edgecolor="#777777", labelcolor="#DDDDDD", fontsize=8)

    # tighter layout for the small card
    fig.tight_layout(pad=1)

    # to PNG bytes → data URI
    buff = BytesIO()
    fig.savefig(buff, format="png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    img_bytes = buff.getvalue()
    return "data:image/png;base64," + base64.b64encode(img_bytes).decode("ascii")

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

# Row 2: 2 graphs + USACE box
cols_bottom = st.columns(3)

for i in range(2):
    with cols_bottom[i]:
        if graph_idx < len(data) and data[graph_idx].get("image_url"):
            img_url = data[graph_idx]["image_url"]
            sep = "&" if "?" in img_url else "?"
            img_url_cb = f"{img_url}{sep}_cb={bucket_15m}"
            st.markdown(f"<img src='{img_url_cb}' class='graph-img'>", unsafe_allow_html=True)
        else:
            st.warning("⚠️ No image found.")
        graph_idx += 1

# Right cell: complete USACE panel in one HTML block (title + metrics + embedded graph)
with cols_bottom[2]:
    if usace:
        inflow_delta_html = format_delta(usace.get("inflow_delta"), usace.get("inflow_unit"))
        outflow_delta_html = format_delta(usace.get("outflow_delta"), usace.get("outflow_unit"))
        storage_delta_html = format_delta(usace.get("storage_delta"), usace.get("storage_unit"))

        # build the tiny graph (if possible); if it fails, we simply omit it
        graph_uri = _io_graph_data_uri(days=7)

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

          {f"<img src='{graph_uri}' style='width:100%; height:20vh; object-fit:contain; margin-top:8px; border-radius:4px;'/>" if graph_uri else ""}
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
