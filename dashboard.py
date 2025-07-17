import streamlit as st
from scraper import fetch_site_graphs
from streamlit_extras.st_autorefresh import st_autorefresh

# Auto-refresh every 10 minutes (600,000 ms)
st_autorefresh(interval=600000, key="datarefresh")

st.set_page_config(page_title="USGS Water Graphs", layout="wide")
st.title("📈 USGS Site Graphs (Live)")

data = fetch_site_graphs()

# 3 cards per row
cols = st.columns(3)

for i, item in enumerate(data):
    with cols[i % 3]:
        st.markdown(f"#### [{item['title']}]({item['page_url']})", unsafe_allow_html=True)
        if item["image_url"]:
            st.image(item["image_url"], use_container_width=True)
        else:
            st.warning("⚠️ No image found.")
