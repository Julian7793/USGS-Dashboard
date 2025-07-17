import requests
from bs4 import BeautifulSoup

# Your 6 URLs
urls = [
    "https://waterdata.usgs.gov/monitoring-location/USGS-03274650/#dataTypeId=continuous-00065-0&period=P7D",
    "https://waterdata.usgs.gov/monitoring-location/USGS-03276000/#dataTypeId=continuous-00065-0&period=P7D",
    "https://waterdata.usgs.gov/monitoring-location/USGS-03275000/#dataTypeId=continuous-00065-0&period=P7D",
    "https://waterdata.usgs.gov/monitoring-location/USGS-03276500/#dataTypeId=continuous-00065-0&period=P7D",
    "https://waterdata.usgs.gov/nwis/dv?cb_00010=on&cb_00010=on&cb_00095=on&cb_00095=on&cb_00300=on&cb_00300=on&cb_00400=on&cb_00400=on&cb_32318=on&cb_32318=on&cb_32319=on&cb_32319=on&cb_32320=on&cb_32320=on&cb_32321=on&cb_32321=on&cb_62614=on&cb_63680=on&cb_99133=on&format=gif_default&site_no=03275990&legacy=&referred_module=sw&period=&begin_date=2024-07-16&end_date=2025-07-16"
]

def fetch_site_graphs():
    site_data = []

    for url in urls:
        try:
            response = requests.get(url)
            soup = BeautifulSoup(response.text, "html.parser")

            # Try to extract the title (site name)
            title_tag = soup.find("title")
            title = title_tag.text.strip() if title_tag else "No Title Found"

            # Try to find the first graph/image
            img = soup.find("img")
            img_url = img['src'] if img else None

            # Resolve relative URLs
            if img_url and img_url.startswith("/"):
                base = "https://waterdata.usgs.gov"
                img_url = base + img_url

            site_data.append({
                "title": title,
                "image_url": img_url,
                "page_url": url
            })

        except Exception as e:
            site_data.append({
                "title": "Error loading page",
                "image_url": None,
                "page_url": url
            })

    return site_data