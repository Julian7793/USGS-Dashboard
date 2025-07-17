import streamlit as st
from scraper import fetch_site_graphs
import streamlit as st

st.experimental_rerun()  # this reruns immediately, not on a timer


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
