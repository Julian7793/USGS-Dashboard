import re
import requests

DAILY_REPORT_URL = "https://www.lrl-wc.usace.army.mil/reports/lkreport.html"
_NUM = re.compile(r"(-?\d{1,3}(?:,\d{3})*(?:\.\d+)?|-?\d+(?:\.\d+)?)")
_TAG = re.compile(r"<[^>]+>")
_WS = re.compile(r"\s+")

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

def _sanitize_precip(num):
    if num is None:
        return None
    if num <= -900:
        return "0.00 in"
    return f"{num:.2f} in"

def _clean_html(html: str) -> str:
    txt = _TAG.sub(" ", html)
    txt = _WS.sub(" ", txt).strip()
    return txt

def _find_brookville_segment(clean_text: str) -> str | None:
    """
    Find the Brookville row in the Daily Lake Report text and return ~300 chars around it.
    The row starts with the basin (Whitewater) then 'Brookville' and a bunch of columns.
    """
    i = clean_text.lower().find(" brookville ")
    if i == -1:
        # sometimes basin name precedes; still return a window if only 'brookville' appears
        i = clean_text.lower().find("brookville")
        if i == -1:
            return None
    start = max(0, i - 80)
    end = min(len(clean_text), i + 320)
    return clean_text[start:end]

def fetch_usace_brookville_data():
    """
    Pull Brookville metrics from the Louisville District Daily Lake Report (server-rendered):
      Columns of interest (in order on that page):
        Today's Pool (ft), 24 Hour Change (ft), 24 Hour Precip (in),
        24 Hour Avg Inflow (CFS), 6 A.M. Outflow (CFS)
    Storage is not included on this report -> return None for storage.
    """
    try:
        r = requests.get(DAILY_REPORT_URL, headers={"Cache-Control": "no-cache"}, timeout=25)
        r.raise_for_status()
        html = r.text
        clean = _clean_html(html)

        seg = _find_brookville_segment(clean)
        if not seg:
            print("Daily Lake Report: Brookville row not found.")
            return {
                "elevation": None, "elevation_delta": None, "elevation_unit": "ft",
                "inflow": None, "inflow_delta": None, "inflow_unit": "cfs",
                "outflow": None, "outflow_delta": None, "outflow_unit": "cfs",
                "storage": None, "storage_delta": None, "storage_unit": "ac-ft",
                "precipitation": None,
            }

        # Extract numbers in the segment. For Brookville the sequence contains:
        # WinterPool, SummerPool, FloodPool, TodaysPool, DevFromPool, 24hChange,
        # 24hPrecip, 24hAvgInflow, 6AMOutflow, (then other columns we ignore)
        nums = [ _to_float(n) for n in _NUM.findall(seg) ]
        if len(nums) < 9:
            print(f"Daily Lake Report: unexpected numeric count in segment: {seg}")
            return {
                "elevation": None, "elevation_delta": None, "elevation_unit": "ft",
                "inflow": None, "inflow_delta": None, "inflow_unit": "cfs",
                "outflow": None, "outflow_delta": None, "outflow_unit": "cfs",
                "storage": None, "storage_delta": None, "storage_unit": "ac-ft",
                "precipitation": None,
            }

        todays_pool   = nums[3]
        change_24h    = nums[5]
        precip_24h    = nums[6]
        inflow_24h    = nums[7]
        outflow_6am   = nums[8]

        return {
            "elevation": _fmt(todays_pool, "ft"),
            "elevation_delta": change_24h,   # you can show with format_delta()
            "elevation_unit": "ft",
            "inflow": _fmt(inflow_24h, "cfs"),
            "inflow_delta": None,            # daily report doesn't provide inflow delta
            "inflow_unit": "cfs",
            "outflow": _fmt(outflow_6am, "cfs"),
            "outflow_delta": None,           # daily report doesn't provide outflow delta
            "outflow_unit": "cfs",
            "storage": None,
            "storage_delta": None,
            "storage_unit": "ac-ft",
            "precipitation": _sanitize_precip(precip_24h),
        }

    except Exception as e:
        print(f"USACE daily report fetch failed: {e}")
        return None
