import streamlit as st
import requests
from datetime import datetime
import folium
from streamlit_folium import st_folium
import streamlit as st
import os

api_key = st.secrets.get("google", {}).get("api_key") or os.getenv("GOOGLE_API_KEY")

st.set_page_config(page_title="🚕 Smart Taxi Fare Predictor", layout="centered")
st.title("🚕 Smart Taxi Fare Predictor")

api_key = st.secrets["google"]["api_key"]

# Initialize session state
if "pickup_final" not in st.session_state:
    st.session_state.pickup_final = None
if "dropoff_final" not in st.session_state:
    st.session_state.dropoff_final = None
if "show_results" not in st.session_state:
    st.session_state.show_results = False
if "fare_result" not in st.session_state:
    st.session_state.fare_result = None
if "map_data" not in st.session_state:
    st.session_state.map_data = None

# -------------------------------
# AUTOCOMPLETE FUNCTION (NYC ONLY)
# -------------------------------
def autocomplete_place_nyc(input_text):
    if not input_text or len(input_text) < 2:
        return []
    endpoint = "https://maps.googleapis.com/maps/api/place/autocomplete/json"
    params = {
        "input": input_text,
        "key": api_key,
        "types": "geocode",
        "components": "country:us",
        "language": "en",
        "location": "40.7128,-74.0060",
        "radius": 50000
    }
    try:
        response = requests.get(endpoint, params=params)
        predictions = response.json().get("predictions", [])
        return [p["description"] for p in predictions]
    except:
        return []

# -------------------------------
# GEOCODE FUNCTION
# -------------------------------
@st.cache_data
def get_coordinates(place_name):
    endpoint = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {"address": place_name, "key": api_key}
    response = requests.get(endpoint, params=params)
    results = response.json().get("results", [])
    if results:
        loc = results[0]["geometry"]["location"]
        return loc["lat"], loc["lng"]
    return None, None

# -------------------------------
# PICKUP LOCATION
# -------------------------------
st.markdown("### 📍 Pickup Location")

if st.session_state.pickup_final:
    st.success(f"✅ Selected: **{st.session_state.pickup_final}**")
    if st.button("🔄 Change Pickup", key="change_pickup"):
        st.session_state.pickup_final = None
        st.session_state.show_results = False
        st.rerun()
else:
    pickup_input = st.text_input(
        "Type your pickup location",
        key="pickup_input",
        placeholder="e.g., Times Square, Central Park"
    )

    if pickup_input and len(pickup_input) >= 2:
        pickup_suggestions = autocomplete_place_nyc(pickup_input)

        if pickup_suggestions:
            st.markdown(f"**{len(pickup_suggestions)} suggestions found - Click to select:**")
            for i, suggestion in enumerate(pickup_suggestions):
                if st.button(f"📍 {suggestion}", key=f"pickup_{i}"):
                    st.session_state.pickup_final = suggestion
                    st.rerun()
        else:
            st.warning("⚠️ No suggestions found. Try different keywords.")

# -------------------------------
# DROPOFF LOCATION
# -------------------------------
st.markdown("### 🏁 Dropoff Location")

if st.session_state.dropoff_final:
    st.success(f"✅ Selected: **{st.session_state.dropoff_final}**")
    if st.button("🔄 Change Dropoff", key="change_dropoff"):
        st.session_state.dropoff_final = None
        st.session_state.show_results = False
        st.rerun()
else:
    dropoff_input = st.text_input(
        "Type your dropoff location",
        key="dropoff_input",
        placeholder="e.g., JFK Airport, Brooklyn Bridge"
    )

    if dropoff_input and len(dropoff_input) >= 2:
        dropoff_suggestions = autocomplete_place_nyc(dropoff_input)

        if dropoff_suggestions:
            st.markdown(f"**{len(dropoff_suggestions)} suggestions found - Click to select:**")
            for i, suggestion in enumerate(dropoff_suggestions):
                if st.button(f"🏁 {suggestion}", key=f"dropoff_{i}"):
                    st.session_state.dropoff_final = suggestion
                    st.rerun()
        else:
            st.warning("⚠️ No suggestions found. Try different keywords.")

# -------------------------------
# DATE, TIME, PASSENGERS
# -------------------------------
st.markdown("### 📅 Trip Details")
col1, col2 = st.columns(2)
with col1:
    date = st.date_input("Pickup date", datetime.now().date())
with col2:
    time = st.time_input("Pickup time", datetime.now().time())

pickup_datetime = datetime.combine(date, time)
passenger_count = st.number_input("👥 Number of passengers", min_value=1, max_value=8, value=1)

# -------------------------------
# PREDICT FARE
# -------------------------------
st.markdown("---")
if st.button("🚀 Predict Fare", type="primary", use_container_width=True):
    if not st.session_state.pickup_final or not st.session_state.dropoff_final:
        st.error("⚠️ Please select both pickup and dropoff locations first.")
    else:
        with st.spinner("Calculating fare..."):
            pickup_lat, pickup_lon = get_coordinates(st.session_state.pickup_final)
            dropoff_lat, dropoff_lon = get_coordinates(st.session_state.dropoff_final)

            if not pickup_lat or not dropoff_lat:
                st.error("⚠️ Could not find coordinates for the selected locations.")
            else:
                # Store map data
                st.session_state.map_data = {
                    "pickup_lat": pickup_lat,
                    "pickup_lon": pickup_lon,
                    "dropoff_lat": dropoff_lat,
                    "dropoff_lon": dropoff_lon,
                    "pickup_name": st.session_state.pickup_final,
                    "dropoff_name": st.session_state.dropoff_final
                }

                # Taxi fare API
                url = "https://taxifare.lewagon.ai/predict"
                params = {
                    "pickup_datetime": pickup_datetime.strftime("%Y-%m-%d %H:%M:%S"),
                    "pickup_longitude": pickup_lon,
                    "pickup_latitude": pickup_lat,
                    "dropoff_longitude": dropoff_lon,
                    "dropoff_latitude": dropoff_lat,
                    "passenger_count": passenger_count
                }
                response = requests.get(url, params=params)
                result = response.json()

                if "fare" in result:
                    st.session_state.fare_result = result["fare"]
                    st.session_state.show_results = True
                else:
                    st.error("⚠️ Could not get a valid prediction from the API.")

# -------------------------------
# DISPLAY RESULTS (PERSISTENT)
# -------------------------------
if st.session_state.show_results and st.session_state.map_data and st.session_state.fare_result:
    st.markdown("### 🗺️ Route Map")

    map_data = st.session_state.map_data
    m = folium.Map(
        location=[(map_data["pickup_lat"] + map_data["dropoff_lat"])/2,
                  (map_data["pickup_lon"] + map_data["dropoff_lon"])/2],
        zoom_start=12
    )
    folium.Marker(
        [map_data["pickup_lat"], map_data["pickup_lon"]],
        popup=f"Pickup: {map_data['pickup_name']}",
        icon=folium.Icon(color="green", icon="play")
    ).add_to(m)
    folium.Marker(
        [map_data["dropoff_lat"], map_data["dropoff_lon"]],
        popup=f"Dropoff: {map_data['dropoff_name']}",
        icon=folium.Icon(color="red", icon="flag")
    ).add_to(m)
    folium.PolyLine(
        [[map_data["pickup_lat"], map_data["pickup_lon"]],
         [map_data["dropoff_lat"], map_data["dropoff_lon"]]],
        color="blue", weight=3, opacity=0.8
    ).add_to(m)
    st_folium(m, width=700, height=500)

    st.markdown("### 💵 Fare Estimate")
    st.success(f"## ${st.session_state.fare_result:.2f}")
