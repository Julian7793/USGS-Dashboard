import streamlit as st
from scraper import fetch_site_graphs
from datetime import datetime
import pytz
from streamlit_autorefresh import st_autorefresh

# Refresh interval in seconds
REFRESH_INTERVAL = 30

# Set page config at the very top
st.set_page_config(page_title="USGS Water Graphs", layout="wide")

# Automatically rerun this script every REFRESH_INTERVAL seconds
st_autorefresh(interval=REFRESH_INTERVAL * 1000, limit=None, key="autorefresh")

# Timezone for Eastern Time (handles daylight saving)
eastern = pytz.timezone("US/Eastern")

st.title("📈 USGS Site Graphs (Live)")

# Fetch data fresh every time the script runs (which now happens every 30 seconds automatically)
data = fetch_site_graphs()

# Display last updated time as current time in Eastern timezone
updated_time = datetime.now(eastern)
updated_time_str = updated_time.strftime("%Y-%m-%d %I:%M %p %Z")
st.caption(f"🔄 Last updated: {updated_time_str}")

# Layout: 3 cards per row
cols = st.columns(3)

for i, item in enumerate(data):
    with cols[i % 3]:
        st.markdown(f"#### [{item['title']}]({item['page_url']})", unsafe_allow_html=True)
        if item["image_url"]:
            st.image(item["image_url"], use_container_width=True)
        else:
            st.warning("⚠️ No image found.")
