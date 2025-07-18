import streamlit as st
from scraper import fetch_site_graphs
import time
from datetime import datetime
import pytz

# Refresh interval in seconds
REFRESH_INTERVAL = 30

# Timezone for Eastern Time (handles daylight saving)
eastern = pytz.timezone("US/Eastern")

# Initialize session state for refresh tracking
if "last_data_refresh" not in st.session_state:
    st.session_state["last_data_refresh"] = time.time()
    st.session_state["last_data_refresh_human"] = datetime.now(eastern)

# Check if it's time to refresh
elapsed = time.time() - st.session_state["last_data_refresh"]
if elapsed > REFRESH_INTERVAL:
    st.session_state["last_data_refresh"] = time.time()
    st.session_state["last_data_refresh_human"] = datetime.now(eastern)
    st.experimental_rerun()

st.set_page_config(page_title="USGS Water Graphs", layout="wide")
st.title("📈 USGS Site Graphs (Live)")

data = fetch_site_graphs()

# Display last update timestamp based on actual data refresh time
updated_time_str = st.session_state["last_data_refresh_human"].strftime("%Y-%m-%d %I:%M %p %Z")
st.caption(f"🔄 Last updated: {updated_time_str}")

# 3 cards per row
cols = st.columns(3)

for i, item in enumerate(data):
    with cols[i % 3]:
        st.markdown(f"#### [{item['title']}]({item['page_url']})", unsafe_allow_html=True)
        if item["image_url"]:
            st.image(item["image_url"], use_container_width=True)
        else:
            st.warning("⚠️ No image found.")
