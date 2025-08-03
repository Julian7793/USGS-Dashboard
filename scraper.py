import requests
from bs4 import BeautifulSoup
import re

site_info = [
    {"site_no": "03274650", "title": "Whitewater River Near Economy, IN - 03274650", "parm_cd": "00065"},
    {"site_no": "03276000", "title": "East Fork Whitewater River at Brookville, IN - 03276000", "parm_cd": "00065"},
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

        image_url = f"https://waterdata.usgs.gov/nwisweb/graph?agency_cd=USGS&site_no={site_no}&period=7&parm_cd={parm_cd}"
        page_url = f"https://waterdata.usgs.gov/monitoring-location/USGS-{site_no}"

        site_data.append({
            "site_no": site_no,
            "title": title,
            "image_url": image_url,
            "page_url": page_url
        })

    # Add USACE Brookville Reservoir image
    usace_image_url = fetch_usace_graph_image()
    site_data.insert(1, {
        "site_no": "USACE-POOL",
        "title": "Brookville Lake Elevation (USACE)",
        "image_url": usace_image_url,
        "page_url": "https://water.sec.usace.army.mil/overview/lrl/locations/brookville"
    })

    return site_data

def fetch_usace_graph_image():
    try:
        url = "https://water.sec.usace.army.mil/overview/lrl/locations/brookville"
        res = requests.get(url, timeout=10)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, "html.parser")

        img_tag = soup.find("img", {"src": re.compile(r"/images/locations/lrl/brookville/.*\.png")})
        if img_tag:
            return "https://water.sec.usace.army.mil" + img_tag["src"]
    except Exception as e:
        print(f"Failed to fetch USACE image: {e}")
    return None

def live_stage_data(site_ids):
    stages = {}
    lake_site = "03275990"
    river_sites = [sid for sid in site_ids if sid != lake_site and sid.startswith("0")]

    # USGS river stage
    try:
        resp = requests.get(
            "https://waterservices.usgs.gov/nwis/iv/",
            params={"format":"json","sites":",".join(river_sites),"parameterCd":"00065"},
            timeout=10
        )
        resp.raise_for_status()
        data = resp.json()
        for ts in data["value"]["timeSeries"]:
            sid = ts["sourceInfo"]["siteCode"][0]["value"]
            val_list = ts["values"][0]["value"]
            stages[sid] = float(val_list[-1]["value"]) if val_list else None
    except:
        for sid in river_sites:
            stages[sid] = None

    # USGS lake elevation
    try:
        resp = requests.get(
            "https://waterservices.usgs.gov/nwis/iv/",
            params={"format":"json","sites":lake_site,"parameterCd":"62614"},
            timeout=10
        )
        resp.raise_for_status()
        data = resp.json()
        val_list = data["value"]["timeSeries"][0]["values"][0]["value"]
        stages[lake_site] = float(val_list[-1]["value"]) if val_list else None
    except:
        stages[lake_site] = None

    return stages

station_limits = {
    "03274650": {"type": "operational", "min": 2.26, "max": 13.98,
                 "min_msg": "Lower intake out of water", "max_msg": "Float hitting bottom of gage shelf"},
    "03276000": {"type": "operational", "min": 0.69, "max": 25.72,
                 "min_msg": "Lower intake out of water", "max_msg": "Float hitting bottom of gage shelf"},
    "03275000": {"type": "flood", "stages": {"Action": 10, "Minor": 14, "Moderate": 17, "Major": 19}},
    "03276500": {"type": "flood", "stages": {"Action": 14, "Minor": 20, "Moderate": 23, "Major": 29}},
    "03275990": {"type": "lake", "note": "Lake or reservoir water surface elevation above NGVD 1929, ft"},
    "03274615": {"type": "flood", "stages": {"Action": 14, "Minor": 16, "Moderate": 24, "Major": 30}},
}

def get_river_safety_status(sid, val):
    cfg = station_limits.get(sid)
    if not cfg or val is None:
        return "❔ Unknown"
    if cfg["type"] == "operational":
        if val < cfg["min"]:
            return f"🔽 Too Low – {cfg['min_msg']} ({val:.2f} ft)"
        elif val > cfg["max"]:
            return f"🔼 Too High – {cfg['max_msg']} ({val:.2f} ft)"
        return f"🟢 Normal Operating Range ({val:.2f} ft)"
    elif cfg["type"] == "flood":
        for stage, level in sorted(cfg["stages"].items(), key=lambda x: x[1], reverse=True):
            if val >= level:
                return f"⚠️ {stage} Flood Stage Reached ({val:.2f} ft)"
        return f"🟢 Below Flood Stage ({val:.2f} ft)"
    return "❔ Unknown"

BROOKVILLE_AVG_LEVEL = 748  # Average lake level in feet
def get_lake_status(val):
    if val is None:
        return "❔ Unknown"
    lb, ub = BROOKVILLE_AVG_LEVEL * 0.98, BROOKVILLE_AVG_LEVEL * 1.02
    if val < lb:
        return f"🔽 Below Normal ({val:.2f} ft)"
    elif val > ub:
        return f"🔼 Above Normal ({val:.2f} ft)"
    return f"🟢 Normal Level ({val:.2f} ft)"
