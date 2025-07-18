import streamlit as st
import requests

st.set_page_config(page_title="Weather Test", layout="centered")
st.title("🌦️ Weather Test for ZIP Code 47012")

API_KEY = st.secrets.get("WEATHERAPI_KEY")
ZIP_CODE = "47012"

if not API_KEY:
    st.error("❌ WEATHERAPI_KEY not found in secrets.")
else:
    url = f"http://api.weatherapi.com/v1/forecast.json?key={API_KEY}&q={ZIP_CODE}&days=3&aqi=no&alerts=no"
    try:
        res = requests.get(url)
        if res.status_code == 200:
            weather = res.json()

            st.success("✅ Weather data fetched!")
            current = weather["current"]
            forecast = weather["forecast"]["forecastday"]

            st.metric("Current Temp (°F)", f"{current['temp_f']}°F")
            st.caption(current["condition"]["text"])

            st.subheader("3-Day Forecast")
            cols = st.columns(3)
            for i, day in enumerate(forecast):
                with cols[i]:
                    st.markdown(f"**{day['date']}**")
                    # Fix: Properly handle image URL
                    icon_url = f"https:{day['day']['condition']['icon']}"
                    st.image(icon_url)
                    st.markdown(f"↑ {day['day']['maxtemp_f']}°F")
                    st.markdown(f"↓ {day['day']['mintemp_f']}°F")
        else:
            st.error(f"Failed to fetch data: {res.status_code}")
    except Exception as e:
        st.error(f"Request error: {e}")
