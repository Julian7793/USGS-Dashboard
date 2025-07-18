import streamlit as st
from scraper import fetch_site_graphs
from streamlit_extras.st_autorefresh import st_autorefresh
from datetime import datetime
import pytz
import time

REFRESH_INTERVAL = 30  # seconds
eastern = pytz.timezone("US/Eastern")

# This triggers rerun every REFRESH_INTERVAL seconds (in ms)
count = st_autorefresh(interval=REFRESH_INTERVAL * 1000, key="auto_refresh")

# Fetch data every run and store in session state for possible caching
if "data" not in st.session_state or count == 0:
    st.session_state["data"] = fetch_site_graphs()
    st.session_state["last_data_refresh_human"] = datetime.now(eastern)

data = st.session_state["data"]
updated_time_str = st.session_state["last_data_refresh_human"].strftime("%Y-%m-%d %I:%M %p %Z")

st.set_page_config(page_title="USGS Water Graphs", layout="wide")
st.title("📈 USGS Site Graphs (Live)")
st.caption(f"🔄 Last updated: {updated_time_str}")

cols = st.columns(3)
for i, item in enumerate(data):
    with cols[i % 3]:
        st.markdown(f"#### [{item['title']}]({item['page_url']})", unsafe_allow_html=True)
        if item["image_url"]:
            st.image(item["image_url"], use_container_width=True)
        else:
            st.warning("⚠️ No image found.")
