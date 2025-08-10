import re
import requests
from typing import Optional, Tuple

# -------------------------------
# USGS sites to show as graphs
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

        site_data.append(
            {
                "title": title,
                "page_url": page_url,
                "image_url": image_url,
            }
        )
    return site_data


# -------------------------------
# USACE Brookville data scraping
# -------------------------------
USACE_URLS = [
    "https://water.sec.usace.army.mil/overview/lrl/locations/brookville",
    "https://water.usace.army.mil/overview/lrl/locations/brookville",
]

UA_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
}

# Regex helpers
NUM_RE = re.compile(r"(-?\d{1,3}(?:,\d{3})*(?:\.\d+)?|-?\d+(?:\.\d+)?)")
TAG_RE = re.compile(r"<[^>]+>")  # strip HTML tags (robust unit matching)
WS_RE = re.compile(r"\s+")

def _to_float(s):
    if s is None:
        return None
    try:
        return float(str(s).replace(",", ""))
    except Exception:
        return None

def _fmt(num: Optional[float], unit: str) -> Optional[str]:
    if num is None:
        return None
    return f"{num:.2f} {unit}"

def _sanitize_precip(num: Optional[float], unit: str) -> Optional[str]:
    if num is None:
        return None
    if num <= -900:
        return "0.00 in"  # change to "N/A" if you prefer
    return f"{num:.2f} {unit}"

def _get_html() -> Optional[str]:
    for url in USACE_URLS:
        try:
            r = requests.get(url, headers=UA_HEADERS, timeout=25)
            r.raise_for_status()
            html = r.text
            # Write for diagnostics so we can inspect what your Pi actually got
            try:
                with open("/tmp/usace_brookville.html", "w", encoding="utf-8") as f:
                    f.write(html)
            except Exception:
                pass
            if html and len(html) > 1000:
                return html
        except Exception:
            continue
    return None

def _find_label_block(html: str, label: str, window: int = 10000) -> Optional[str]:
    i = html.lower().find(label.lower())
    if i == -1:
        return None
    j = min(len(html), i + window)
    return html[i:j]

def _clean(block: Optional[str]) -> str:
    if not block:
        return ""
    # Strip tags, normalize whitespace and punctuation spacing
    txt = TAG_RE.sub(" ", block)
    txt = WS_RE.sub(" ", txt).strip()
    # Normalize weird hyphens, NBSP etc.
    txt = txt.replace("\u00a0", " ").replace("–", "-").replace("—", "-")
    return txt

def _unit_index(clean_block: str, unit_words: list[str]) -> Optional[Tuple[int, str]]:
    lowest = None
    which = None
    for u in unit_words:
        m = re.search(rf"\b{re.escape(u)}\b", clean_block, flags=re.IGNORECASE)
        if m:
            j = m.start()
            if lowest is None or j < lowest:
                lowest = j
                which = u
    if lowest is None:
        return None
    u_norm = which.lower()
    if "cfs" in u_norm:
        u_norm = "cfs"
    elif "ac" in u_norm or "acre" in u_norm:
        u_norm = "ac-ft"
    elif "ft" in u_norm:
        u_norm = "ft"
    elif u_norm == "in":
        u_norm = "in"
    return lowest, u_norm

def _value_before_unit(clean_block: str, unit_idx: int) -> Optional[float]:
    left = clean_block[:unit_idx]
    nums = NUM_RE.findall(left)
    if not nums:
        return None
    return _to_float(nums[-1])

def _delta_after_unit(clean_block: str, unit_end_idx: int, main_val: Optional[float]) -> Optional[float]:
    right = clean_block[unit_end_idx:]
    nums = [ _to_float(n) for n in NUM_RE.findall(right) ]
    # Filter out years and timestamps (>= 1900), keep distinct from main value
    cand = [n for n in nums if n is not None and n < 1900]
    # Prefer decimals (24h deltas often decimal)
    decimals = [n for n in cand if abs(n - int(n)) > 1e-9]
    seq = decimals if decimals else cand
    if not seq:
        return None
    for n in reversed(seq):
        if main_val is None or abs(n - main_val) > 1e-9:
            return n
    return seq[-1]

def _parse_metric(html: str, label: str, unit_words: list[str], default_unit: str):
    """
    Strategy:
      1) Take a large label-local block (10k chars).
      2) Strip tags so units split by tags still match.
      3) Find a unit word.
      4) value = last number BEFORE unit; delta = reasonable number AFTER unit.
      5) Fallback: first two numbers in the cleaned block.
    """
    block = _find_label_block(html, label, window=10000)
    clean = _clean(block)

    if not clean:
        return None, None, default_unit

    up = _unit_index(clean, unit_words)
    if not up:
        nums = [ _to_float(n) for n in NUM_RE.findall(clean) ]
        val = nums[0] if nums else None
        delta = nums[1] if len(nums) >= 2 else None
        return val, delta, default_unit

    unit_idx, unit_norm = up
    val = _value_before_unit(clean, unit_idx)
    delta = _delta_after_unit(clean, unit_idx + len(unit_norm), val)
    return val, delta, unit_norm or default_unit

def fetch_usace_brookville_data():
    """
    Scrape Brookville Reservoir stats:
      - Elevation (ft) + 24h delta
      - Inflow (cfs) + 24h delta
      - Outflow (cfs) + 24h delta
      - Storage (ac-ft) + 24h delta
      - Precipitation (in)  (sentinels sanitized)
    Returns a dict suitable for direct rendering.
    """
    try:
        html = _get_html()
        if not html:
            print("USACE fetch: no HTML (all metrics -> None)")
            return {
                "elevation": None, "elevation_delta": None, "elevation_unit": "ft",
                "inflow": None, "inflow_delta": None, "inflow_unit": "cfs",
                "outflow": None, "outflow_delta": None, "outflow_unit": "cfs",
                "storage": None, "storage_delta": None, "storage_unit": "ac-ft",
                "precipitation": None,
            }

        # Elevation
        v, d, u = _parse_metric(html, "Elevation", ["ft", "feet"], "ft")
        elevation = _fmt(v, u)
        elevation_delta = d

        # Inflow
        v, d, u = _parse_metric(html, "Inflow", ["cfs"], "cfs")
        inflow = _fmt(v, u)
        inflow_delta = d

        # Outflow
        v, d, u = _parse_metric(html, "Outflow", ["cfs"], "cfs")
        outflow = _fmt(v, u)
        outflow_delta = d

        # Storage
        v, d, u = _parse_metric(html, "Storage", ["ac-ft", "acre-ft", "ac ft", "acft"], "ac-ft")
        storage = _fmt(v, u)
        storage_delta = d

        # Precipitation (sanitize sentinels)
        v, _d, u = _parse_metric(html, "Precipitation", ["in"], "in")
        precipitation = _sanitize_precip(v, u)

        # Basic diagnostics if anything is None
        if any(x is None for x in [elevation, inflow, outflow, storage, precipitation]):
            print("USACE parse warning: one or more fields None. See /tmp/usace_brookville.html for the raw page.")

        return {
            "elevation": elevation,
            "elevation_delta": elevation_delta,
            "elevation_unit": "ft",
            "inflow": inflow,
            "inflow_delta": inflow_delta,
            "inflow_unit": "cfs",
            "outflow": outflow,
            "outflow_delta": outflow_delta,
            "outflow_unit": "cfs",
            "storage": storage,
            "storage_delta": storage_delta,
            "storage_unit": "ac-ft",
            "precipitation": precipitation,
        }

    except Exception as e:
        print(f"USACE data fetch failed: {e}")
        return None
