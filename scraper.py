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

        data = {
            "elevation": None,
            "inflow": None,
            "outflow": None,
            "storage": None,
            "precipitation": None
        }

        metrics = soup.find_all("div", class_="overview-detail__metric")
        for metric in metrics:
            label = metric.find("span", class_="overview-detail__label")
            value = metric.find("div", class_="overview-detail__value")
            if not label or not value:
                continue

            label_text = label.get_text(strip=True).lower()
            value_text = value.get_text(strip=True).replace("\xa0", " ")

            if "elevation" in label_text:
                data["elevation"] = value_text
            elif "inflow" in label_text:
                data["inflow"] = value_text
            elif "outflow" in label_text:
                data["outflow"] = value_text
            elif "storage" in label_text:
                data["storage"] = value_text
            elif "precipitation" in label_text:
                data["precipitation"] = value_text

        return data

    except Exception as e:
        print(f"USACE data fetch failed: {e}")
        return None
