import re
import requests

# -------------------------------
# USGS sites to show as graphs (unchanged)
# -------------------------------
site_info = [
    {"site_no": "03274650", "title": "Whitewater River Near Economy, IN - 03274650", "parm_cd": "00065"},
    {"site_no": "03275000", "title": "Whitewater River Near Alpine, IN - 03275000", "parm_cd": "00065"},
    {"site_no": "03276500", "title": "Whitewater River at Brookville, IN - 03276500", "parm_cd": "00065"},
    {"site_no": "03275990", "title": "Brookville Lake at Brookville, IN - 03275990", "parm_cd": "62614"},
]

def fetch_site_graphs():
    site_data = []
    for site in site_info:
        site_no = site["site_no"]
        title = site["title"]
        parm_cd = site["parm_cd"]

        image_url = (
            "https://waterdata.usgs.gov/nwisweb/graph"
            f"?agency_cd=USGS&site_no={site_no}&parm_cd={parm_cd}&period=7"
        )
        page_url = f"https://waterdata.usgs.gov/monitoring-location/USGS-{site_no}"

        site_data.append({"title": title, "page_url": page_url, "image_url": image_url})
    return site_data


# -------------------------------
# USACE Brookville data scraping (server-rendered daily report)
# -------------------------------
DAILY_REPORT_URL = "https://www.lrl-wc.usace.army.mil/reports/lkreport.html"

NUM = re.compile(r"(-?\d{1,3}(?:,\d{3})*(?:\.\d+)?|-?\d+(?:\.\d+)?)")
TAG = re.compile(r"<[^>]+>")
WS = re.compile(r"\s+")

def _to_float(s):
    if s is None:
        return None
    try:
        return float(str(s).replace(",", ""))
    except Exception:
        return None

def _fmt(num, unit):
    if num is None:
        return None
    return f"{num:.2f} {unit}"

def _sanitize_precip_value(num):
    # If any bogus sentinel comes through (unlikely on daily report), clamp to 0.00 in
    if num is None:
        return None
    if num <= -900:
        return "0.00 in"
    return f"{num:.2f} in"

def _clean_html(html: str) -> str:
    txt = TAG.sub(" ", html)
    txt = WS.sub(" ", txt).strip()
    return txt

def _extract_brookville_row_text(clean_text: str) -> str | None:
    """
    Find the line/segment for Brookville in the Daily Lake Report.
    The table includes a row with 'Brookville' (project name).
    We grab ~300 chars around it for parsing.
    """
    i = clean_text.lower().find("brookville")
    if i == -1:
        return None
    start = max(0, i - 80)
    end = min(len(clean_text), i + 300)
    return clean_text[start:end]

def fetch_usace_brookville_data():
    """
    Parse Brookville metrics from the Louisville District Daily Lake Report:
      - Elevation (Today's Pool, ft)
      - Elevation 24-hour Change (ft)
      - 24-hour Precipitation (in)
      - 24-hour Avg Inflow (cfs)
      - 6 A.M. Outflow (cfs)
    Storage is not provided on this report -> returned as None.
    """
    try:
        r = requests.get(DAILY_REPORT_URL, headers={"Cache-Control": "no-cache"}, timeout=25)
        r.raise_for_status()
        html = r.text

        # Clean to plain text to avoid tag split issues
        txt = _clean_html(html)

        # Pull a compact window around the Brookville row
        seg = _extract_brookville_row_text(txt)
        if not seg:
            print("USACE daily report: could not find 'Brookville' row.")
            return {
                "elevation": None, "elevation_delta": None, "elevation_unit": "ft",
                "inflow": None, "inflow_delta": None, "inflow_unit": "cfs",
                "outflow": None, "outflow_delta": None, "outflow_unit": "cfs",
                "storage": None, "storage_delta": None, "storage_unit": "ac-ft",
                "precipitation": None,
            }

        # Heuristic parse:
        # The Daily Lake Report header shows:
        #  - Today's Pool (ft)
        #  - 24 Hour Change (ft)
        #  - 24 Hour Precip (in)
        #  - 24 Hour Avg Inflow (CFS)
        #  - 6 A.M. Outflow (CFS)
        #
        # We will:
        #  1) Extract all numbers in the segment
        #  2) Use context keywords to anchor each field if present
        #  3) Fallback: pick numbers in expected order near keywords
        numbers = [ _to_float(n) for n in NUM.findall(seg) ]

        # Try anchored pulls for each metric
        def after(label, window=120):
            j = seg.lower().find(label.lower())
            if j == -1:
                return None
            subs = seg[j:j+window]
            ns = [ _to_float(n) for n in NUM.findall(subs) ]
            return ns[0] if ns else None

        elev = after("Todays Pool") or after("Today s Pool") or after("Today's Pool")
        elev_delta = after("24 Hour Change")
        precip = after("24 Hour Precip")
        inflow = after("24 Hour Avg Inflow")
        outflow = after("6 A.M. Outflow") or after("6 AM Outflow") or after("6 A M Outflow")

        # Final formatting / sanitizing
        elevation = _fmt(elev, "ft")
        elevation_delta = elev_delta  # ft, shown by your format_delta()
        precipitation = _sanitize_precip_value(precip)
        inflow_s = _fmt(inflow, "cfs")
        outflow_s = _fmt(outflow, "cfs")

        return {
            "elevation": elevation,
            "elevation_delta": elevation_delta,
            "elevation_unit": "ft",
            "inflow": inflow_s,
            "inflow_delta": inflow,   # the daily report doesn't provide inflow delta; keep None or reuse inflow if you prefer
            "inflow_unit": "cfs",
            "outflow": outflow_s,
            "outflow_delta": outflow, # same note as above
            "outflow_unit": "cfs",
            "storage": None,          # not in this report
            "storage_delta": None,
            "storage_unit": "ac-ft",
            "precipitation": precipitation,
        }

    except Exception as e:
        print(f"USACE daily report fetch failed: {e}")
        return None
