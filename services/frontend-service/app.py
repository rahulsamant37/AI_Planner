import streamlit as st
import requests
import os
from datetime import datetime
import json

st.set_page_config(
    page_title="AI Travel Planner",
    page_icon="✈️",
    layout="wide"
)

# Configuration
PLANNER_SERVICE_URL = os.getenv("PLANNER_SERVICE_URL", "http://localhost:8000")

def call_planner_service(city: str, interests: str):
    """Call the planner microservice"""
    try:
        response = requests.post(
            f"{PLANNER_SERVICE_URL}/generate-itinerary",
            json={"city": city, "interests": interests},
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Failed to connect to planner service: {str(e)}")
        return None

def get_service_health():
    """Check service health"""
    try:
        response = requests.get(f"{PLANNER_SERVICE_URL}/health", timeout=5)
        return response.status_code == 200
    except:
        return False

def get_cache_stats():
    """Get cache statistics"""
    try:
        response = requests.get(f"{PLANNER_SERVICE_URL}/cache/stats", timeout=5)
        if response.status_code == 200:
            return response.json()
    except:
        pass
    return None

# Main UI
st.title("✈️ AI Travel Itinerary Planner")
st.write("Plan your day trip itinerary by entering your city and interests")

# Service status in sidebar
with st.sidebar:
    st.subheader("🔧 Service Status")
    if get_service_health():
        st.success("✅ Planner Service Online")
    else:
        st.error("❌ Planner Service Offline")
    
    # Cache statistics
    cache_stats = get_cache_stats()
    if cache_stats and not cache_stats.get("error"):
        st.subheader("📊 Cache Statistics")
        st.metric("Connected Clients", cache_stats.get("connected_clients", 0))
        st.metric("Memory Used", cache_stats.get("used_memory", "0B"))
        st.metric("Cached Keys", cache_stats.get("keyspace", 0))
        
        if st.button("🗑️ Clear Cache"):
            try:
                response = requests.delete(f"{PLANNER_SERVICE_URL}/cache/clear")
                if response.status_code == 200:
                    st.success("Cache cleared successfully!")
                    st.rerun()
                else:
                    st.error("Failed to clear cache")
            except Exception as e:
                st.error(f"Error clearing cache: {str(e)}")
    
    st.subheader("ℹ️ About")
    st.info("""
    This is a modern microservice-based AI Travel Planner.
    
    **Features:**
    - Microservice architecture
    - Redis caching
    - Health monitoring
    - Logging & observability
    """)

# Main form
with st.form("planner_form"):
    col1, col2 = st.columns(2)
    
    with col1:
        city = st.text_input(
            "🏙️ City Name",
            placeholder="e.g., Paris, Tokyo, New York",
            help="Enter the city you want to visit"
        )
    
    with col2:
        interests = st.text_input(
            "🎯 Your Interests",
            placeholder="e.g., museums, food, shopping, nature",
            help="Enter your interests separated by commas"
        )
    
    submitted = st.form_submit_button("🚀 Generate Itinerary", type="primary")

    if submitted:
        if city and interests:
            with st.spinner("Generating your personalized itinerary..."):
                result = call_planner_service(city, interests)
                
                if result:
                    st.success("✅ Itinerary generated successfully!")
                    
                    # Display metadata
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("📍 City", result["city"])
                    with col2:
                        st.metric("🎯 Interests", len(result["interests"]))
                    with col3:
                        cache_status = "🟢 From Cache" if result.get("cached", False) else "🔵 Fresh Generated"
                        st.metric("📊 Status", cache_status)
                    
                    # Display itinerary
                    st.subheader("📋 Your Personalized Itinerary")
                    st.markdown(result["itinerary"])
                    
                    # Show interests as tags
                    st.subheader("🏷️ Based on your interests:")
                    interests_html = ""
                    for interest in result["interests"]:
                        interests_html += f'<span style="background-color: #ff4b4b; color: white; padding: 0.2rem 0.6rem; margin: 0.1rem; border-radius: 1rem; font-size: 0.8rem;">{interest.strip()}</span> '
                    st.markdown(interests_html, unsafe_allow_html=True)
                    
                    # Generation timestamp
                    if "generated_at" in result:
                        st.caption(f"Generated at: {result['generated_at']}")
                    
                    # Download option
                    itinerary_text = f"""
AI Travel Itinerary for {result["city"]}
Generated on: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
Interests: {", ".join(result["interests"])}

{result["itinerary"]}
                    """
                    
                    st.download_button(
                        label="📥 Download Itinerary",
                        data=itinerary_text,
                        file_name=f"{city.lower().replace(' ', '_')}_itinerary.txt",
                        mime="text/plain"
                    )
        else:
            st.warning("⚠️ Please fill in both city and interests to generate your itinerary")

# Footer
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: #666; font-size: 0.8rem;'>
    🏗️ Built with modern microservice architecture | 
    ⚡ Powered by FastAPI, Streamlit & Redis | 
    🔍 Full observability with ELK Stack
    </div>
    """,
    unsafe_allow_html=True
)
