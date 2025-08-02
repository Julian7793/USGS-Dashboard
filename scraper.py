import requests
from bs4 import BeautifulSoup

site_info = [
    {"site_no": "03274650", "title": "Whitewater River Near Economy, IN - 03274650", "parm_cd": "00065"},
    {"site_no": "03276000", "title": "East Fork Whitewater River at Brookville, IN - 03276000", "parm_cd": "00065"},
    {"site_no": "03275000", "title": "Whitewater River Near Alpine, IN - 03275000", "parm_cd": "00065"},
    {"site_no": "03276500", "title": "Whitewater River at Brookville, IN - 03276500", "parm_cd": "00065"},
    {"site_no": "03275990", "title": "Brookville Lake at Brookville, IN - 03275990", "parm_cd": "62614"},
]

def fetch_usace_brookville_graph():
    try:
        url = "https://water.usace.army.mil/overview/lrl/locations/brookville"
        res = requests.get(url, timeout=10)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, "html.parser")
        img_tag = soup.select_one("img.img-fluid[src*='/images/']")
        if not img_tag:
            return None
        image_url = f"https://water.usace.army.mil{img_tag['src']}"
        return {
            "site_no": "USACE-BROOKVILLE",
            "title": "Brookville Reservoir (USACE)",
            "image_url": image_url,
            "page_url": url
        }
    except Exception:
        return None

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

    # Add USACE Brookville graph
    usace_data = fetch_usace_brookville_graph()
    if usace_data:
        site_data.insert(1, usace_data)  # Replace 1 to position where you want the graph

    return site_data
