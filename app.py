import streamlit as st
from PIL import Image
import json
import os
import folium
from streamlit_folium import st_folium
from google import genai
from google.genai import types
from dotenv import load_dotenv


load_dotenv()
# -----------------------------------------------------------------------------
# Configuration & Setup
# -----------------------------------------------------------------------------
st.set_page_config(page_title="Street Dog Management & Reporting System", layout="wide")

# Initialize Gemini Client from the local .env file or sidebar input.
api_key = st.sidebar.text_input(
    "Enter Gemini API Key",
    placeholder="Paste your Gemini API key",
    type="password",
    help="Your key is used only for this app session.",
)
api_key = api_key or os.getenv("GEMINI_API_KEY", "")

st.title("🐾 Street Dog Incident & Management System")
st.caption("Upload an image of a stray dog/pack to assess severity, generate management protocols, and report spatial data.")

# -----------------------------------------------------------------------------
# Core Function: Gemini Vision Analysis
# -----------------------------------------------------------------------------
def analyze_dog_incident(image: Image.Image, key: str):
    """
    Sends the uploaded image to Gemini to extract count, health status, 
    behavior, severity score, and recommended humane actions.
    """
    client = genai.Client(api_key=key)
    
    prompt = """
    Analyze this image for street dog population management and public safety.
    Return ONLY a valid JSON object matching this schema:
    {
        "dog_count": integer,
        "observed_behavior": "Calm" | "Pack formation" | "Aggressive" | "Injured/Sick",
        "visible_health_issues": list of strings (e.g., skin infection, open wound, none),
        "severity_score": string ("Low" | "Medium" | "High" | "Critical"),
        "severity_reasoning": string,
        "recommended_actions": list of strings (must align with ABC rules: vaccination, sterilization, medical aid)
    }
    """
    
    response = client.models.generate_content(
        model="gemini-3.6-flash",
        contents=[image, prompt],
        config=types.GenerateContentConfig(
            response_mime_type="application/json"
        )
    )
    return json.loads(response.text)

# -----------------------------------------------------------------------------
# Layout: Left Column (Upload & Analysis), Right Column (Map & Output)
# -----------------------------------------------------------------------------
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("1. Report Incident")
    uploaded_file = st.file_uploader("Upload Street Dog Photo", type=["jpg", "jpeg", "png"])
    
    # Location input simulate GPS/User Tagging
    lat = st.number_input("Latitude", value=13.0827, format="%.6f") # Default: Chennai
    lon = st.number_input("Longitude", value=80.2707, format="%.6f")
    notes = st.text_area("Additional Location Notes", placeholder="Near market area, behind school...")

    analyze_btn = st.button("Run AI Analysis", type="primary", disabled=not uploaded_file)

if uploaded_file and analyze_btn:
    if not api_key:
        st.error("Please provide a Gemini API Key in the sidebar.")
    else:
        image = Image.open(uploaded_file)
        with col1:
            st.image(image, caption="Uploaded Image", use_container_width=True)
            
        with st.spinner("Analyzing image via Gemini Vision AI..."):
            try:
                analysis = analyze_dog_incident(image, api_key)
                st.session_state["analysis_result"] = analysis
                st.session_state["location"] = {"lat": lat, "lon": lon, "notes": notes}
            except Exception as e:
                st.error(f"Analysis failed: {e}")

# -----------------------------------------------------------------------------
# Results & Leaflet Mapping Display
# -----------------------------------------------------------------------------
with col2:
    st.subheader("2. AI Analysis & Spatial Mapping")
    
    if "analysis_result" in st.session_state:
        res = st.session_state["analysis_result"]
        loc = st.session_state["location"]
        
        # Display Severity Badge & Metrics
        sev_color = {
            "Low": "🟢", "Medium": "🟡", "High": "🟠", "Critical": "🔴"
        }.get(res["severity_score"], "⚪")
        
        st.markdown(f"### Severity Status: {sev_color} **{res['severity_score']}**")
        
        m_col1, m_col2 = st.columns(2)
        m_col1.metric("Dogs Detected", res["dog_count"])
        m_col2.metric("Behavior", res["observed_behavior"])
        
        # Actions & Details
        with st.expander("Management Protocols (ABC Rules)", expanded=True):
            st.write(f"**Reasoning:** {res['severity_reasoning']}")
            st.write("**Recommended Actions:**")
            for act in res["recommended_actions"]:
                st.write(f"- {act}")

        # Render Leaflet Map using Folium
        st.markdown("#### Dynamic Leaflet Map")
        marker_color = {
            "Low": "green", "Medium": "orange", "High": "red", "Critical": "darkred"
        }.get(res["severity_score"], "blue")
        
        # Create Folium Map centered on reported coordinates
        m = folium.Map(location=[loc["lat"], loc["lon"]], zoom_start=15)
        
        popup_html = f"""
        <b>Severity:</b> {res['severity_score']}<br>
        <b>Dogs Count:</b> {res['dog_count']}<br>
        <b>Behavior:</b> {res['observed_behavior']}<br>
        <b>Notes:</b> {loc['notes']}
        """
        
        folium.Marker(
            location=[loc["lat"], loc["lon"]],
            popup=folium.Popup(popup_html, max_width=300),
            tooltip=f"Incident Level: {res['severity_score']}",
            icon=folium.Icon(color=marker_color, icon="info-sign")
        ).add_to(m)
        
        # Display map in Streamlit
        st_folium(m, width=500, height=350)
    else:
        st.info("Upload an image and click 'Run AI Analysis' to view severity scores and plot on the map.")