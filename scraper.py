from datetime import datetime, timezone

import requests

site_info = [
    {"site_no": "03274650", "title": "Whitewater River Near Economy, IN - 03274650", "parm_cd": "00065"},
    {"site_no": "03275000", "title": "Whitewater River Near Alpine, IN - 03275000", "parm_cd": "00065"},
    {"site_no": "03276500", "title": "Whitewater River at Brookville, IN - 03276500", "parm_cd": "00065"},
    {"site_no": "03275990", "title": "Brookville Lake at Brookville, IN - 03275990", "parm_cd": "62614"},
]

USGS_IV_URL = "https://waterservices.usgs.gov/nwis/iv/"
REQUEST_HEADERS = {
    "Accept": "application/json",
    "User-Agent": "USGS-Dashboard/1.0 (+https://waterservices.usgs.gov/)",
}


def _format_usace_value(value, unit):
    """Format a USACE numeric value with thousands separators and units."""
    if value is None:
        return None

    formatted_value = f"{float(value):,.2f}".rstrip("0").rstrip(".")
    return f"{formatted_value} {unit}".strip()


def _parse_usgs_timestamp(timestamp):
    """Parse a USGS timestamp and normalize naive values to UTC."""
    parsed_timestamp = datetime.fromisoformat(str(timestamp).replace("Z", "+00:00"))
    if parsed_timestamp.tzinfo is None:
        parsed_timestamp = parsed_timestamp.replace(tzinfo=timezone.utc)
    return parsed_timestamp


def _collapse_duplicate_points(point_values_by_timestamp, timestamp_labels):
    """Return one chronologically sorted value for each observation time.

    Some USGS instantaneous-values responses include more than one value with
    the exact same timestamp for a site/parameter. Plotting those duplicate
    timestamps directly makes Matplotlib draw vertical connector segments,
    which can look like two lines with the space between them filled in.
    Averaging duplicate observations preserves the overall trend while keeping
    the graph as a single continuous line.
    """

    collapsed_points = []
    for timestamp_key in sorted(point_values_by_timestamp):
        values = point_values_by_timestamp[timestamp_key]
        average_value = sum(values) / len(values)
        collapsed_points.append((timestamp_labels[timestamp_key], average_value))
    return collapsed_points


def fetch_usgs_timeseries(site_no, parm_cd, period_days=7):
    """Return recent USGS instantaneous values for one site/parameter.

    The dashboard used to embed PNGs from ``waterdata.usgs.gov/nwisweb/graph``
    directly in the browser. Those image URLs are brittle because a browser,
    ad-blocker, proxy, or upstream change can prevent them from loading even
    though the underlying data is available. Fetching the JSON data server-side
    lets the app render consistent local graphs instead.
    """

    params = {
        "format": "json",
        "sites": site_no,
        "parameterCd": parm_cd,
        "period": f"P{period_days}D",
        "siteStatus": "all",
    }
    response = requests.get(USGS_IV_URL, params=params, headers=REQUEST_HEADERS, timeout=20)
    response.raise_for_status()
    payload = response.json()

    series = payload.get("value", {}).get("timeSeries", [])
    if not series:
        return {
            "points": [],
            "unit": "",
            "description": "",
        }

    first_series = series[0]
    variable = first_series.get("variable", {})
    unit = variable.get("unit", {}).get("unitCode") or ""
    description = variable.get("variableDescription") or ""
    values_groups = first_series.get("values", [])

    point_values_by_timestamp = {}
    timestamp_labels = {}
    for group in values_groups:
        for point in group.get("value", []):
            timestamp = point.get("dateTime")
            value = point.get("value")
            if timestamp is None or value in (None, ""):
                continue
            try:
                parsed_timestamp = _parse_usgs_timestamp(timestamp)
                numeric_value = float(value)
            except (TypeError, ValueError):
                continue

            timestamp_key = parsed_timestamp.timestamp()
            point_values_by_timestamp.setdefault(timestamp_key, []).append(numeric_value)
            timestamp_labels[timestamp_key] = timestamp

    points = _collapse_duplicate_points(point_values_by_timestamp, timestamp_labels)

    return {
        "points": points,
        "unit": unit,
        "description": description,
    }


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
            "parm_cd": parm_cd,
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
            formatted = _format_usace_value(value, unit)

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
