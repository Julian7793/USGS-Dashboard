import re
import requests

# -------------------------------
# USGS sites to show as graphs
# -------------------------------
site_info = [
    {"site_no": "03274650", "title": "Whitewater River Near Economy, IN - 03274650", "parm_cd": "00065"},
    {"site_no": "03275000", "title": "Whitewater River Near Alpine, IN - 03275000", "parm_cd": "00065"},
    {"site_no": "03276500", "title": "Whitewater River at Brookville, IN - 03276500", "parm_cd": "00065"},
    {"site_no": "03275990", "title": "Brookville Lake at Brookville, IN - 03275990", "parm_cd": "62614"},
]

# -------------------------------
# Build USGS graph + page links
# -------------------------------
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
    "https://water.usace.army.mil/overview/lrl/locations/brookville",
    "https://water.sec.usace.army.mil/overview/lrl/locations/brookville",
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

# numbers like 57, 1,234, 56.86, -901
NUM = re.compile(r"(-?\d{1,3}(?:,\d{3})*(?:\.\d+)?|-?\d+(?:\.\d+)?)")

def _to_float(s):
    if s is None:
        return None
    try:
        return float(str(s).replace(",", ""))
    except Exception:
        return None

def _format_val(num, unit):
    if num is None:
        return None
    return f"{num:.2f} {unit}"

def _sanitize_precip_value(num, unit: str):
    # Treat USACE negative sentinel (e.g., -901) as "no data"
    if num is None:
        return None
    if num <= -900:
        return "0.00 in"  # change to "N/A" if preferred
    return f"{num:.2f} {unit}"

def _get_html():
    for url in USACE_URLS:
        try:
            r = requests.get(url, headers=UA_HEADERS, timeout=25)
            r.raise_for_status()
            html = r.text
            if html and len(html) > 1000:  # avoid WAF shells
                return html
        except Exception:
            continue
    return None

def _find_label_block(html: str, label: str, window: int = 1800) -> str | None:
    """Take a slice starting at label for parsing."""
    i = html.lower().find(label.lower())
    if i == -1:
        return None
    return html[i: i + window]

def _unit_pos(block: str, unit_variants: list[str]) -> tuple[int, str] | None:
    """Find the first occurrence of any unit variant; return (index, normalized_unit)."""
    lowest = None
    which = None
    for u in unit_variants:
        j = block.lower().find(u.lower())
        if j != -1 and (lowest is None or j < lowest):
            lowest = j
            which = u
    if lowest is None:
        return None
    # normalize text
    u_norm = which.lower()
    if "cfs" in u_norm:
        u_norm = "cfs"
    elif "ac" in u_norm or "acre" in u_norm:
        u_norm = "ac-ft"
    elif "ft" in u_norm:
        u_norm = "ft"
    elif "in" in u_norm:
        u_norm = "in"
    return lowest, u_norm

def _value_before_unit(block: str, unit_idx: int):
    """Pick the LAST number that appears before the unit token."""
    left = block[:unit_idx]
    nums = NUM.findall(left)
    if not nums:
        return None
    return _to_float(nums[-1])

def _delta_after_unit(block: str, unit_end_idx: int, value_num: float | None):
    """
    Pick a 'delta' from numbers AFTER the unit token.
    Heuristics:
      - ignore obvious years (>= 1900)
      - prefer a number with a decimal
      - otherwise pick the last remaining number that's not equal to the main value
    """
    right = block[unit_end_idx:]
    nums = [ _to_float(n) for n in NUM.findall(right) ]
    # filter bads
    cand = [n for n in nums if n is not None and n < 1900]
    # prefer decimals
    decimals = [n for n in cand if abs(n - int(n)) > 1e-9]
    seq = decimals if decimals else cand
    if not seq:
        return None
    # pick the last that's not identical to the value
    for n in reversed(seq):
        if value_num is None or abs(n - value_num) > 1e-9:
            return n
    return seq[-1]

def _parse_metric(html: str, label: str, unit_variants: list[str], default_unit: str):
    """
    Parse a metric by:
      1) taking a label-local block,
      2) finding the unit token,
      3) value = last number BEFORE unit,
      4) delta = number AFTER unit (per heuristics).
    """
    block = _find_label_block(html, label)
    if not block:
        return None, None, default_unit
    up = _unit_pos(block, unit_variants)
    if not up:
        # If no unit token found, just try first two numbers as value/delta
        nums = [ _to_float(n) for n in NUM.findall(block) ]
        val = nums[0] if nums else None
        delta = nums[1] if len(nums) >= 2 else None
        return val, delta, default_unit

    unit_idx, unit_norm = up
    val = _value_before_unit(block, unit_idx)
    delta = _delta_after_unit(block, unit_idx + len(unit_norm), val)
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
            return {
                "elevation": None, "elevation_delta": None, "elevation_unit": "ft",
                "inflow": None, "inflow_delta": None, "inflow_unit": "cfs",
                "outflow": None, "outflow_delta": None, "outflow_unit": "cfs",
                "storage": None, "storage_delta": None, "storage_unit": "ac-ft",
                "precipitation": None,
            }

        # Elevation
        v, d, u = _parse_metric(html, "Elevation", [" ft", " feet", "ft"], "ft")
        elevation = _format_val(v, u)
        elevation_delta = d

        # Inflow  (value BEFORE 'cfs'; delta AFTER 'cfs')
        v, d, u = _parse_metric(html, "Inflow", [" cfs", "cfs"], "cfs")
        inflow = _format_val(v, u)
        inflow_delta = d

        # Outflow
        v, d, u = _parse_metric(html, "Outflow", [" cfs", "cfs"], "cfs")
        outflow = _format_val(v, u)
        outflow_delta = d

        # Storage
        v, d, u = _parse_metric(html, "Storage", [" ac-ft", " ac ft", " acre-ft", " acft", "ac-ft", "acre-ft"], "ac-ft")
        storage = _format_val(v, u)
        storage_delta = d

        # Precipitation (sanitize sentinels)
        v, _d, u = _parse_metric(html, "Precipitation", [" in", "in"], "in")
        precipitation = _sanitize_precip_value(v, u)

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
