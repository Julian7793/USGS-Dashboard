import math
import statistics
import time
from datetime import datetime, timedelta, timezone
import re
import requests

# =========================
# USGS sites (unchanged)
# =========================
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


# =========================
# USACE / CWMS Data API
# =========================
# CWMS API base & defaults
CDA_BASE = "https://cwms-data.usace.army.mil/cwms-data"
OFFICE   = "LRL"            # Louisville District
LOC_HINTS = ["BROK1", "BROOKVILLE", "BROOKVILLE LAKE", "BROOKVILLE LK", "BROOKVILLE DAM"]

UA_HEADERS = {
    "User-Agent": "RiverStats-Dashboard/1.0 (+streamlit; contact=local)",
    "Accept": "application/json",
    "Cache-Control": "no-cache",
}

# Regex helpers
NUM_RE = re.compile(r"(-?\d{1,3}(?:,\d{3})*(?:\.\d+)?|-?\d+(?:\.\d+)?)")

def _to_float(x):
    if x is None:
        return None
    try:
        return float(str(x).replace(",", ""))
    except Exception:
        return None

def _fmt(num, unit):
    if num is None:
        return None
    return f"{num:.2f} {unit}"

def _sanitize_precip_value(num):
    if num is None:
        return None
    if num <= -900:
        return "0.00 in"
    return f"{num:.2f} in"

def _utc_now_iso():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

def _iso_ago(hours=24):
    return (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat().replace("+00:00", "Z")

def _get_json(url, params=None, timeout=20):
    r = requests.get(url, headers=UA_HEADERS, params=params or {}, timeout=timeout)
    r.raise_for_status()
    return r.json()

def _catalog_timeseries(name_like):
    """
    Query the catalog for time-series names that match 'name_like'.
    """
    url = f"{CDA_BASE}/catalog/TIMESERIES"
    params = {"office": OFFICE, "name-like": name_like, "page-size": 1000}
    try:
        j = _get_json(url, params=params)
        # Schema: { "entries":[{"name": "...", ...}, ...] }
        entries = j.get("entries", []) if isinstance(j, dict) else []
        return [e.get("name") for e in entries if "name" in e]
    except Exception:
        return []

def _pick_best(names, contains_all):
    """
    From a list of series names, pick one that contains all substrings in 'contains_all'
    (case-insensitive). Prefer higher temporal resolution (Inst.15Minutes over 1Hour), then recency.
    """
    def score(n):
        s = n.lower()
        ok = all(c.lower() in s for c in contains_all)
        if not ok:
            return (-1, -1)
        # prefer shorter interval and 'Inst'
        rank = 0
        if ".inst." in s: rank += 3
        if ".15minute" in s: rank += 2
        if ".1hour" in s: rank += 1
        return (1, rank)

    best = None
    best_rank = (-1, -1)
    for n in names:
        sc = score(n)
        if sc > best_rank:
            best_rank = sc
            best = n
    return best

def _fetch_timeseries(name, begin=None, end=None, page_size=10000):
    """
    Fetch time series samples for 'name' within [begin, end].
    Returns list of (time_iso, value) pairs.
    """
    url = f"{CDA_BASE}/timeseries"
    params = {
        "name": name,
        "office": OFFICE,
        "page-size": page_size,
        "format": "json",
    }
    if begin: params["begin"] = begin
    if end:   params["end"]   = end
    j = _get_json(url, params=params)
    # Expected schema: {"name": "...", "values": [{"time":"...", "value": <num>, ...}, ...]}
    vals = []
    if isinstance(j, dict):
        data = j.get("values") or j.get("values-ts") or j.get("valuesArray") or []
        # Try a few possible shapes
        if isinstance(data, list) and data and isinstance(data[0], dict) and "time" in data[0]:
            for v in data:
                vals.append((v["time"], _to_float(v.get("value"))))
        elif isinstance(data, list) and data and isinstance(data[0], list):
            # sometimes values may be [[time, value], ...]
            for arr in data:
                if len(arr) >= 2:
                    vals.append((arr[0], _to_float(arr[1])))
    return vals

def _latest_value(vals):
    if not vals:
        return None
    # assume sorted by time ascending; if not, sort
    try:
        vals_sorted = sorted(vals, key=lambda x: x[0])
    except Exception:
        vals_sorted = vals
    return vals_sorted[-1][1]

def _value_approx_at(vals, target_time):
    """
    Get the value closest to target_time (ISO Z), assuming vals = [(iso, value), ...]
    """
    if not vals:
        return None
    try:
        tt = datetime.fromisoformat(target_time.replace("Z","+00:00"))
        candidates = []
        for t_iso, v in vals:
            try:
                t = datetime.fromisoformat(t_iso.replace("Z","+00:00"))
                candidates.append((abs((t - tt).total_seconds()), v))
            except Exception:
                pass
        if not candidates:
            return None
        candidates.sort(key=lambda x: x[0])
        return candidates[0][1]
    except Exception:
        return None

def _avg(values):
    arr = [x for x in values if isinstance(x, (int, float)) and math.isfinite(x)]
    if not arr:
        return None
    return statistics.mean(arr)

def fetch_usace_brookville_data():
    """
    Live Brookville metrics via CWMS Data API:
      - Elevation (ft) + 24h change (ft)
      - Inflow (cfs)  (24h average if only Inst data is available)
      - Outflow (cfs) (latest instantaneous)
      - Precipitation (in) (24h total if available; else latest)
    Storage is not fetched here (series varies by project).
    """
    try:
        # 1) Discover candidate series names via catalog
        # We try a few location hints and pick best matches per parameter
        candidates = []
        for hint in LOC_HINTS:
            # Wildcard around hint
            like = f"%{hint}%"
            names = _catalog_timeseries(like)
            if names:
                candidates.extend(names)
        # Deduplicate
        candidates = sorted(set(candidates))

        # Helper to choose a series
        elev_name  = _pick_best(candidates, ["elev", ".inst."]) or _pick_best(candidates, ["elev"])
        infl_name  = _pick_best(candidates, ["flow-res in"]) or _pick_best(candidates, ["inflow"])
        out_name   = _pick_best(candidates, ["flow-res out"]) or _pick_best(candidates, ["outflow"])
        prec_name  = _pick_best(candidates, ["precip"]) or _pick_best(candidates, ["pcpn", "prec"])

        # 2) Fetch data windows
        end  = _utc_now_iso()
        beg1 = _iso_ago(24)   # past 24h window

        elev_vals = _fetch_timeseries(elev_name, begin=beg1, end=end) if elev_name else []
        infl_vals = _fetch_timeseries(infl_name, begin=beg1, end=end) if infl_name else []
        out_vals  = _fetch_timeseries(out_name,  begin=beg1, end=end) if out_name  else []
        pre_vals  = _fetch_timeseries(prec_name, begin=beg1, end=end) if prec_name else []

        # 3) Elevation latest + 24h change
        elev_latest = _latest_value(elev_vals)
        elev_24h_ago = _value_approx_at(elev_vals, (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat().replace("+00:00","Z"))
        elev_delta = None
        if elev_latest is not None and elev_24h_ago is not None:
            elev_delta = elev_latest - elev_24h_ago

        # 4) Inflow: prefer daily avg if the series is already an average (name contains ".Ave." or ".Mean.")
        infl_latest = _latest_value(infl_vals)
        infl_avg_24h = None
        if infl_name and (".ave." in infl_name.lower() or ".mean." in infl_name.lower() or ".1day" in infl_name.lower()):
            infl_avg_24h = infl_latest
        else:
            # compute average over last 24h instantaneous values
            infl_avg_24h = _avg([v for _, v in infl_vals])

        # 5) Outflow: latest instantaneous
        out_latest = _latest_value(out_vals)

        # 6) Precip: try 24h total if series is cumulative/periodic; else latest
        precip_val = None
        if prec_name and (".tot" in prec_name.lower() or ".1day" in prec_name.lower() or ".24hour" in prec_name.lower()):
            precip_val = _latest_value(pre_vals)
        else:
            precip_val = _latest_value(pre_vals)

        # 7) Build result
        result = {
            "elevation": _fmt(elev_latest, "ft"),
            "elevation_delta": elev_delta,
            "elevation_unit": "ft",
            "inflow": _fmt(infl_avg_24h, "cfs"),
            "inflow_delta": None,      # not provided directly by API; we show avg instead
            "inflow_unit": "cfs",
            "outflow": _fmt(out_latest, "cfs"),
            "outflow_delta": None,
            "outflow_unit": "cfs",
            "storage": None,
            "storage_delta": None,
            "storage_unit": "ac-ft",
            "precipitation": _sanitize_precip_value(precip_val),
        }

        # If everything came back None, make it clear to the caller
        if all(v is None for k,v in result.items() if k not in ("elevation_unit","inflow_unit","outflow_unit","storage_unit")):
            # Could not resolve series names at this office/location
            print("CWMS API: No matching series found for Brookville with current hints.")
        return result

    except Exception as e:
        print(f"CWMS API fetch failed: {e}")
        return None
