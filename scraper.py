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

# Numbers like 57, 1,234, 56.86, -901
NUM_RE = re.compile(r"(-?\d{1,3}(?:,\d{3})*(?:\.\d+)?|-?\d+(?:\.\d+)?)")
TAG_RE = re.compile(r"<[^>]+>")  # strip HTML tags

def _to_float(s):
    if s is None:
        return None
    try:
        return float(str(s).replace("
