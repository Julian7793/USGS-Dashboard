import streamlit as st
from scraper import fetch_site_graphs
import streamlit as st

import time

# Refresh interval in seconds
REFRESH_INTERVAL = 30

if "last_refresh" not in st.session_state:
    st.session_state["last_refresh"] = time.time()
else:
    elapsed = time.time() - st.session_state["last_refresh"]
    if elapsed > REFRESH_INTERVAL:
        st.session_state["last_refresh"] = time.time()
        st.experimental_rerun()
        
####
from datetime import datetime
import pytz

# --- Timezone for Eastern Time (handles daylight saving)
eastern = pytz.timezone("US/Eastern")
now_eastern = datetime.now(eastern)
####

st.set_page_config(page_title="USGS Water Graphs", layout="wide")
st.title("📈 USGS Site Graphs (Live)")

data = fetch_site_graphs()

####
st.caption(f"🔄 Last updated: {now_eastern.strftime('%Y-%m-%d %I:%M %p %Z')}")

# 3 cards per row
cols = st.columns(3)

for i, item in enumerate(data):
    with cols[i % 3]:
        st.markdown(f"#### [{item['title']}]({item['page_url']})", unsafe_allow_html=True)
        if item["image_url"]:
            st.image(item["image_url"], use_container_width=True)
        else:
            st.warning("⚠️ No image found.")

