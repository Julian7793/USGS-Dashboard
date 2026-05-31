import base64
from html import escape
from io import BytesIO
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
import requests
import streamlit as st
from streamlit_autorefresh import st_autorefresh

# matplotlib only used to draw the tiny inflow/outflow graph
try:
    import matplotlib
    matplotlib.use("Agg")  # headless backend for servers
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    MATPLOTLIB_OK = True
except Exception:
    MATPLOTLIB_OK = False

from scraper import fetch_site_graphs, fetch_usace_brookville_data, fetch_usgs_timeseries


DISPLAY_TIMEZONE = ZoneInfo("America/New_York")
DISPLAY_TIMEZONE_LABEL = "Eastern Time"
LATEST_INFO_TIMEZONE = timezone(timedelta(hours=-4), "EDT")
DISPLAY_TIME_FORMAT = "%m/%d %I:%M %p"
LAST_UPDATED_TIME_FORMAT = "%Y-%m-%d %I:%M %p"


def _to_display_timezone(timestamp):
    """Return ``timestamp`` in Eastern Time, including daylight saving changes."""
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)
    return timestamp.astimezone(DISPLAY_TIMEZONE)


def _format_display_time(timestamp, time_format=DISPLAY_TIME_FORMAT):
    """Format a timestamp for the dashboard using Eastern Time and 12-hour time."""
    display_timestamp = _to_display_timezone(timestamp)
    return display_timestamp.strftime(f"{time_format} %Z")


def _format_latest_info_time(timestamp):
    """Format the latest-observation timestamp using fixed EDT (UTC-4)."""
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)
    latest_timestamp = timestamp.astimezone(LATEST_INFO_TIMEZONE)
    return latest_timestamp.strftime(f"{DISPLAY_TIME_FORMAT} %Z")


def _set_eastern_time_axis(ax):
    """Format chart x-axis ticks in Eastern Time with daylight saving changes."""
    ax.xaxis.set_major_formatter(mdates.DateFormatter(DISPLAY_TIME_FORMAT, tz=DISPLAY_TIMEZONE))
    ax.set_xlabel(f"Time ({DISPLAY_TIMEZONE_LABEL})", color="#DDDDDD", fontsize=8)


def _fig_to_data_uri(fig):
    """Serialize a matplotlib figure to a PNG data URI for reliable embedding."""
    buff = BytesIO()
    fig.savefig(buff, format="png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    return "data:image/png;base64," + base64.b64encode(buff.getvalue()).decode("ascii")


def _render_error_graph(site):
    """Display a same-sized fallback card when a USGS graph cannot be rendered."""
    title = escape(site.get("title", "USGS graph"))
    page_url = escape(site.get("page_url", ""), quote=True)
    link_html = f"<a href='{page_url}' target='_blank' rel='noopener noreferrer'>Open USGS site page</a>" if page_url else ""
    st.markdown(
        f"""
        <div class="graph-card">
          <strong>{title}</strong>
          <div>⚠️ Could not load graph data from USGS right now.</div>
          <div>{link_html}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _usgs_graph_data(site, days=7):
    """Build a local graph image and latest-value label from USGS JSON data.

    Returning a data URI avoids relying on browser-side loading of the legacy
    USGS graph image endpoint, which is the part that commonly fails in the
    dashboard while the source data remains available.
    """
    if not MATPLOTLIB_OK:
        return None

    try:
        graph_data = fetch_usgs_timeseries(site["site_no"], site["parm_cd"], period_days=days)
    except Exception as exc:
        print(f"USGS graph fetch failed for {site.get('site_no')}: {exc}")
        return None

    points = graph_data.get("points", [])
    if not points:
        return None

    parsed_points = []
    for t_iso, value in points:
        try:
            timestamp = datetime.fromisoformat(str(t_iso).replace("Z", "+00:00"))
            parsed_points.append((_to_display_timezone(timestamp), float(value)))
        except (TypeError, ValueError):
            continue

    if not parsed_points:
        return None

    # USGS can return the newest observation ahead of the historical values.
    # Matplotlib connects points in the order provided, so sort by timestamp to
    # prevent a stray diagonal segment from latest -> oldest across the chart.
    parsed_points.sort(key=lambda point: point[0])
    xs = [timestamp for timestamp, _ in parsed_points]
    ys = [value for _, value in parsed_points]

    unit = graph_data.get("unit") or ""
    description = graph_data.get("description") or "Gage height"

    fig = plt.figure(figsize=(8.6, 6.0), dpi=150)
    ax = fig.add_subplot(111)
    fig.patch.set_facecolor("#303030")
    ax.set_facecolor("#303030")
    ax.grid(True, color="#555555", linewidth=0.6, alpha=0.6)
    ax.plot(xs, ys, linewidth=1.8, color="#4EA3F1")

    ax.set_title(site.get("title", "USGS graph"), color="#F0F0F0", pad=8, fontsize=10)
    ylabel = f"{description} ({unit})" if unit else description
    ax.set_ylabel(ylabel, color="#DDDDDD", fontsize=8)
    ax.tick_params(colors="#DDDDDD", labelsize=8)
    ax.spines["bottom"].set_color("#777777")
    ax.spines["left"].set_color("#777777")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    _set_eastern_time_axis(ax)

    latest_time = _format_latest_info_time(xs[-1])
    latest_value = f"{ys[-1]:.2f} {unit}".strip()
    latest_text = f"Latest: {latest_value} at {latest_time}"

    fig.autofmt_xdate(rotation=25, ha="right")
    fig.tight_layout(pad=1)
    return {"image_uri": _fig_to_data_uri(fig), "latest_text": latest_text}


@st.cache_data(ttl=1800, show_spinner=False)
def get_usgs_graph_image(site_no, parm_cd, title, page_url):
    """Cache rendered USGS graph images independently of the site list."""
    site = {"site_no": site_no, "parm_cd": parm_cd, "title": title, "page_url": page_url}
    return _usgs_graph_data(site)


def render_usgs_graph(site):
    graph_uri = get_usgs_graph_image(
        site.get("site_no"),
        site.get("parm_cd"),
        site.get("title"),
        site.get("page_url"),
    )
    if graph_uri:
        image_uri = graph_uri.get("image_uri")
        latest_text = escape(graph_uri.get("latest_text") or "Latest: N/A")
        st.markdown(
            f"""
            <div class='graph-card graph-data-card'>
              <img src='{image_uri}' class='graph-img'>
              <div class='latest-info'>{latest_text}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        _render_error_graph(site)

def format_delta(delta, unit):
    """Return HTML snippet showing 24 hour change with color coding."""
    if delta is None:
        text = "24 hour change: N/A"
        color = "gray"
    else:
        numeric_delta = float(delta)
        color = "green" if numeric_delta > 0 else "red" if numeric_delta < 0 else "gray"
        sign = "+" if numeric_delta > 0 else "-" if numeric_delta < 0 else ""
        formatted_delta = f"{abs(numeric_delta):,.2f}".rstrip("0").rstrip(".")
        text = f"24 hour change: {sign}{formatted_delta} {unit}"
    return f'<span style="font-size:1em;color:{color}">{text}</span>'

# --- PAGE CONFIG ---
st.set_page_config(page_title="USGS Water Graphs", layout="wide")

# --- STYLE ---
css = """
<style>
  .block-container {
    padding-top: 2px !important;
    padding-bottom: 0 !important;
    padding-left: 4px !important;
    padding-right: 4px !important;
    max-width: 1920px !important;
    background: transparent !important;
  }
  header[data-testid="stHeader"], footer { display: none !important; }
  div[data-testid="stStatusWidget"] { display: none !important; }
  div[data-testid="stDecoration"] { display: none !important; }

  /* Columns: remove default top spacing and align content to top */
  [data-testid="column"] {
    padding-left: 4px !important;
    padding-right: 4px !important;
    margin-top: 0 !important;
    align-self: flex-start !important;
  }

  .stMarkdown, .stMarkdown p { margin: 0 !important; }
  img.graph-img {
    width: 100%;
    height: calc((100vh - 82px) / 2 - 24px);
    max-height: calc((100vh - 82px) / 2 - 24px);
    object-fit: contain;
    display: block;
    margin: 0 auto 2px auto;
    border-radius: 6px;
  }
  .latest-info {
    width: 100%;
    margin: 0;
    color: #DDDDDD;
    font-size: 105%;
    line-height: 1.05;
    text-align: center;
  }
  .graph-card {
    width: calc(100% - 4px);
    height: calc((100vh - 82px) / 2);
    max-height: calc((100vh - 82px) / 2);
    margin: 2px auto;
    background-color: #303030;
    border-radius: 6px;
    padding: 8px;
    box-sizing: border-box;
    color: #DDDDDD;
    display: flex;
    flex-direction: column;
    justify-content: center;
    gap: 8px;
  }
  .graph-data-card {
    padding: 4px;
    justify-content: flex-start;
    gap: 0;
  }
  .graph-card a { color: #8AB4F8; }

  /* App background */
  .stApp { background-color: #171717; }

  /* USACE card (same height as graphs) */
  .usace-card {
    width: calc(100% - 4px);
    margin: 2px auto;
    background-color: #303030;
    padding: 8px;
    height: calc((100vh - 82px) / 2); /* match graph height while avoiding page scrollbar */
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
REFRESH_INTERVAL = 1800  # 30 minutes
st_autorefresh(interval=REFRESH_INTERVAL * 1000, limit=None, key="autorefresh")

# --- USGS GRAPHS ---
@st.cache_data(ttl=3600, show_spinner=False)
def get_usgs_graphs():
    return fetch_site_graphs()

data = get_usgs_graphs()
data.append({
    "site_no": "03274615",
    "title": "Great Miami River at Miamitown OH - USGS-03274615",
    "parm_cd": "00065",
    "page_url": "https://waterdata.usgs.gov/monitoring-location/USGS-03274615",
    "image_url": "https://waterdata.usgs.gov/nwisweb/graph?agency_cd=USGS&site_no=03274615&parm_cd=00065&period=7"
})

# Put the Great Miami River graph where the Brookville Lake graph
# previously appeared, and move Brookville Lake into Great Miami's former slot.
brookville_lake_index = next(
    (index for index, site in enumerate(data) if site.get("site_no") == "03275990"),
    None,
)
great_miami_index = next(
    (index for index, site in enumerate(data) if site.get("site_no") == "03274615"),
    None,
)
if brookville_lake_index is not None and great_miami_index is not None:
    data[brookville_lake_index], data[great_miami_index] = (
        data[great_miami_index],
        data[brookville_lake_index],
    )

# --- USACE DATA ---
# No cache here so it always refetches on rerun
usace = fetch_usace_brookville_data()

# -------------------------------
# USACE helper: 7-day Inflow/Outflow graph from the Water Data timeseries tab
# -------------------------------
USACE_REPORTING_BASE = "https://water.usace.army.mil/cda/reporting"
USACE_PROVIDER = "lrl"
BROOKVILLE_INFLOW_TSID = "Brookville.Flow-Inflow.Ave.1Hour.6Hours.lrldlb-comp"
BROOKVILLE_OUTFLOW_TSID = "Brookville.Flow-Outflow.Ave.1Hour.1Hour.lrldlb-comp"


def _utc_now_iso():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _iso_ago(days=7):
    return (datetime.now(timezone.utc) - timedelta(days=days)).isoformat().replace("+00:00", "Z")


def _get_json(url, params=None, timeout=20):
    r = requests.get(
        url,
        headers={"Accept": "application/json", "User-Agent": "USGS-Dashboard/1.0"},
        params=params or {},
        timeout=timeout,
    )
    r.raise_for_status()
    return r.json()


def _fetch_usace_reporting_timeseries(name, begin, end):
    if not name:
        return []

    url = f"{USACE_REPORTING_BASE}/providers/{USACE_PROVIDER}/timeseries"
    params = {"name": name, "begin": begin, "end": end}
    try:
        payload = _get_json(url, params=params)
    except Exception as exc:
        print(f"USACE timeseries fetch failed for {name}: {exc}")
        return []

    values = payload.get("values", []) if isinstance(payload, dict) else []
    if not isinstance(values, list):
        return []

    points = []
    for row in values:
        if isinstance(row, dict):
            timestamp, value = row.get("time"), row.get("value")
        elif isinstance(row, list) and len(row) >= 2:
            timestamp, value = row[0], row[1]
        else:
            continue
        points.append((timestamp, value))
    return points


def _series_to_display_xy(series):
    xs, ys = [], []
    for timestamp_iso, value in series:
        try:
            timestamp = datetime.fromisoformat(str(timestamp_iso).replace("Z", "+00:00"))
            xs.append(_to_display_timezone(timestamp))
            ys.append(float(value))
        except (TypeError, ValueError):
            continue
    return xs, ys


def _style_usace_axis(ax):
    ax.set_facecolor("#303030")
    ax.grid(True, axis="y", color="#555555", linewidth=0.6, alpha=0.6)
    ax.tick_params(colors="#DDDDDD", labelsize=7)
    ax.spines["top"].set_visible(False)
    ax.spines["left"].set_color("#777777")
    ax.spines["bottom"].set_color("#777777")
    ax.spines["right"].set_color("#777777")


def _usace_io_graph_data_uri(inflow_tsid=None, outflow_tsid=None, days=7):
    """Build the Brookville Inflow/Outflow graph shown on the USACE Timeseries tab."""
    if not MATPLOTLIB_OK:
        return None

    inflow_tsid = inflow_tsid or BROOKVILLE_INFLOW_TSID
    outflow_tsid = outflow_tsid or BROOKVILLE_OUTFLOW_TSID
    end = _utc_now_iso()
    begin = _iso_ago(days)

    inflow = _fetch_usace_reporting_timeseries(inflow_tsid, begin, end)
    outflow = _fetch_usace_reporting_timeseries(outflow_tsid, begin, end)
    x_in, y_in = _series_to_display_xy(inflow)
    x_out, y_out = _series_to_display_xy(outflow)

    if not x_in and not x_out:
        return None

    fig = plt.figure(figsize=(7.6, 2.35), dpi=150)
    fig.patch.set_facecolor("#303030")
    ax = fig.add_subplot(111)
    _style_usace_axis(ax)

    inflow_line = None
    outflow_line = None
    if x_in:
        (inflow_line,) = ax.plot(
            x_in,
            y_in,
            color="#00A3FF",
            linewidth=1.4,
            marker="o",
            markersize=1.6,
            label="Inflow",
        )
    if x_out:
        (outflow_line,) = ax.plot(
            x_out,
            y_out,
            color="#2F35CC",
            linewidth=1.2,
            marker="o",
            markersize=1.4,
            label="Outflow",
        )

    all_values = y_in + y_out
    y_max = max(all_values) if all_values else 1
    y_top = max(1, y_max * 1.12)
    ax.set_ylim(bottom=0, top=y_top)
    ax.set_ylabel("Inflow (cfs)", color="#DDDDDD", fontsize=7)
    ax.yaxis.set_major_formatter(lambda value, _: f"{value:,.0f} cfs")

    right_axis = ax.twinx()
    right_axis.set_ylim(ax.get_ylim())
    right_axis.set_ylabel("Outflow (cfs)", color="#DDDDDD", fontsize=7, rotation=270, labelpad=10)
    right_axis.yaxis.set_major_formatter(lambda value, _: f"{value:,.0f} cfs")
    right_axis.tick_params(colors="#DDDDDD", labelsize=7)
    right_axis.spines["top"].set_visible(False)
    right_axis.spines["left"].set_visible(False)
    right_axis.spines["bottom"].set_color("#777777")
    right_axis.spines["right"].set_color("#777777")

    ax.set_title("Inflow / Outflow", loc="left", color="#F0F0F0", fontsize=10, weight="bold", pad=6)
    ax.text(
        0.5,
        1.03,
        "Last 7 days from USACE Water Data Timeseries",
        transform=ax.transAxes,
        ha="center",
        va="bottom",
        color="#DDDDDD",
        fontsize=6.5,
    )
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d %b", tz=DISPLAY_TIMEZONE))

    handles = [line for line in (inflow_line, outflow_line) if line is not None]
    if handles:
        ax.legend(
            handles=handles,
            loc="upper center",
            bbox_to_anchor=(0.5, -0.16),
            ncol=len(handles),
            frameon=False,
            fontsize=7,
            labelcolor="#DDDDDD",
        )

    fig.tight_layout(pad=0.7)
    return _fig_to_data_uri(fig)


@st.cache_data(ttl=1800, show_spinner=False)
def get_usace_inflow_outflow_graph(inflow_tsid, outflow_tsid):
    return _usace_io_graph_data_uri(inflow_tsid, outflow_tsid, days=7)


# --- LAYOUT ---
# Row 1: 3 graphs
cols_top = st.columns(3)
graph_idx = 0
for i in range(3):
    with cols_top[i]:
        if graph_idx < len(data):
            render_usgs_graph(data[graph_idx])
        else:
            st.warning("⚠️ No graph configured.")
        graph_idx += 1

# Row 2: 2 graphs + USACE box
cols_bottom = st.columns(3)

for i in range(2):
    with cols_bottom[i]:
        if graph_idx < len(data):
            render_usgs_graph(data[graph_idx])
        else:
            st.warning("⚠️ No graph configured.")
        graph_idx += 1

# Right cell: complete USACE panel in one HTML block (title + metrics + embedded graph)
with cols_bottom[2]:
    if usace:
        inflow_delta_html = format_delta(usace.get("inflow_delta"), usace.get("inflow_unit"))
        outflow_delta_html = format_delta(usace.get("outflow_delta"), usace.get("outflow_unit"))
        storage_delta_html = format_delta(usace.get("storage_delta"), usace.get("storage_unit"))

        # Build the Timeseries-tab graph (if possible); if it fails, we simply omit it.
        graph_uri = get_usace_inflow_outflow_graph(
            usace.get("inflow_tsid"),
            usace.get("outflow_tsid"),
        )

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
            Precipitation 24hr total= {usace.get('precipitation') or 'N/A'}
          </div>

          {f"<img src='{graph_uri}' style='width:100%; height:22vh; object-fit:contain; margin-top:8px; background:#303030; border-radius:4px;'/>" if graph_uri else ""}
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
updated_time = _format_display_time(datetime.now(timezone.utc), LAST_UPDATED_TIME_FORMAT)
st.caption(f"Last updated: {updated_time}")
