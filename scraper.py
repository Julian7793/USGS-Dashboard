import requests

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
    """Fetch Brookville Lake metrics from the USACE reporting API.

    The previous implementation attempted to scrape values from the
    Brookville overview web page, but the site is now a client-side
    application that loads data asynchronously.  As a result the scraper
    always returned ``None`` for every metric.  The data is available via a
    public JSON API instead, so we query that endpoint directly and extract
    the latest values from the returned timeseries list.
    """

    url = "https://water.usace.army.mil/cda/reporting/providers/lrl/locations/brookville"
    try:
        res = requests.get(url, timeout=10)
        res.raise_for_status()
        locations = res.json()

        # The API normally returns a list containing a single location.
        # Occasionally it may return a dict (e.g. when an error occurs) in
        # which case indexing into the response would raise ``KeyError``.
        if not isinstance(locations, list) or not locations:
            return None

        location = locations[0]
        result = {
            "elevation": None,
            "inflow": None,
            "inflow_delta": None,
            "inflow_unit": None,
            "outflow": None,
            "outflow_delta": None,
            "outflow_unit": None,
            "storage": None,
            "storage_delta": None,
            "storage_unit": None,
            "precipitation": None,
        }

        for ts in location.get("timeseries", []):
            label = ts.get("label", "").lower()
            value = ts.get("latest_value")
            unit = ts.get("unit", "")
            delta = ts.get("delta24hr")
            formatted = f"{value} {unit}" if value is not None else None

            if label == "elevation":
                result["elevation"] = formatted
            elif label == "inflow":
                result["inflow"] = formatted
                result["inflow_delta"] = delta
                result["inflow_unit"] = unit
            elif label == "outflow":
                result["outflow"] = formatted
                result["outflow_delta"] = delta
                result["outflow_unit"] = unit
            elif label == "precipitation":
                result["precipitation"] = formatted
            elif "storage" in label and result["storage"] is None:
                result["storage"] = formatted
                result["storage_delta"] = delta
                result["storage_unit"] = unit

        return result

    except Exception as e:
        print(f"USACE data fetch failed: {e}")
        return None
