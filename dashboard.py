import streamlit as st
from scraper import fetch_site_graphs
import time
from datetime import datetime
import pytz

REFRESH_INTERVAL = 30
eastern = pytz.timezone("US/Eastern")

# Initialize last_data_refresh and last_data_refresh_human if missing
if "last_data_refresh" not in st.session_state:
    st.session_state["last_data_refresh"] = 0
if "last_data_refresh_human" not in st.session_state:
    st.session_state["last_data_refresh_human"] = datetime.fromtimestamp(0, eastern)

# Check how long since last refresh
elapsed = time.time() - st.session_state["last_data_refresh"]

# If it's time to refresh data, fetch and update timestamp, then rerun
if elapsed > REFRESH_INTERVAL:
    data = fetch_site_graphs()
    st.session_state["last_data_refresh"] = time.time()
    st.session_state["last_data_refresh_human"] = datetime.now(eastern)
    # Store data in session state so we don't fetch twice
    st.session_state["data"] = data
    st.experimental_rerun()
else:
    # Use cached data from session_state if available, otherwise fetch once
    if "data" not in st.session_state:
        st.session_state["data"] = fetch_site_graphs()
    data = st.session_state["data"]

st.set_page_config(page_title="USGS Water Graphs", layout="wide")
st.title("📈 USGS Site Graphs (Live)")

updated_time_str = st.session_state["last_data_refresh_human"].strftime("%Y-%m-%d %I:%M %p %Z")
st.caption(f"🔄 Last updated: {updated_time_str}")

cols = st.columns(3)
for i, item in enumerate(data):
    with cols[i % 3]:
        st.markdown(f"#### [{item['title']}]({item['page_url']})", unsafe_allow_html=True)
        if item["image_url"]:
            st.image(item["image_url"], use_container_width=True)
        else:
            st.warning("⚠️ No image found.")
