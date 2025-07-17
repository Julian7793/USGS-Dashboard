# Direct USGS graph URLs by site number
site_info = [
    {"site_no": "03274650", "title": "Mad River"},
    {"site_no": "03276000", "title": "Buck Creek"},
    {"site_no": "03275000", "title": "Little Miami River"},
    {"site_no": "03276500", "title": "Great Miami River"},
    {"site_no": "03275990", "title": "Lagonda Ave (Daily Values)"}
]

def fetch_site_graphs():
    site_data = []

    for site in site_info:
        site_no = site["site_no"]
        title = site["title"]

        # Construct direct graph image URL
        image_url = f"https://waterdata.usgs.gov/nwisweb/graph?agency_cd=USGS&site_no={site_no}&period=7&parm_cd=00065"

        # Page URL for reference
        page_url = f"https://waterdata.usgs.gov/monitoring-location/USGS-{site_no}"

        site_data.append({
            "title": title,
            "image_url": image_url,
            "page_url": page_url
        })

    return site_data
