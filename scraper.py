import requests
from bs4 import BeautifulSoup
import re

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

        image_url = f"https://waterdata.usgs.gov/nwisweb/graph?agency_cd=USGS&site_no={site_no}&period=7&parm_cd={parm_cd}"
        page_url = f"https://waterdata.usgs.gov/monitoring-location/USGS-{site_no}"

        site_data.append({
            "site_no": site_no,
            "title": title,
            "image_url": image_url,
            "page_url": page_url
        })

    return site_data

def fetch_usace_brookville_data():
    url = "https://water.usace.army.mil/overview/lrl/locations/brookville"
    try:
        res = requests.get(url, timeout=10)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, "html.parser")

        data_map = {}
        # Based on the identified snippet content pattern:
        mapping = {
            "Elevation": "elevation",
            "Inflow": "inflow",
            "Outflow": "outflow",
            "Storage": "storage",
            "Precipitation": "precipitation"
        }
        for label, key in mapping.items():
            # look for label text, then the next numeric sibling text
            span = soup.find("span", string=lambda t: t and label in t)
            if span:
                # find the next text node or sibling that holds numeric content
                val = span.find_next(string=re.compile(r"[0-9.,]+"))
                data_map[key] = val.strip() if val else None
            else:
                data_map[key] = None

        return data_map
    except Exception as e:
        print("Error fetching USACE Brookville data:", e)
        return None

