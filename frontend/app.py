"""
Streamlit frontend for Where Am I? - a geography guessing game.

Features:
- Registration and login with JWT tokens
- 5-round gameplay per session
- Cached Google Street View images
- Interactive map with location pinning
- Confetti animations and engaging UI
- Live leaderboard

IMPORTANT:
- Set BACKEND_URL or provide via environment variable
- Requires backend running (default: http://localhost:8000)
"""

import os
from dotenv import load_dotenv

# Load .env from project root (parent of frontend directory)
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(ROOT_DIR, ".env"))

import time
import requests
import streamlit as st
from streamlit_folium import st_folium
import folium
import json
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

# --------------------
# Configuration
# --------------------
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY", "")  # For interactive Street View
ROUNDS_PER_GAME = 5  # 5 rounds per game
ROUND_TIME_SECONDS = 90  # Timer for each round
HINT_REVEAL_SECONDS = 15  # Show hint in last N seconds


def format_distance(meters: float) -> str:
    """Format distance in km with appropriate precision."""
    km = meters / 1000
    if km < 1:
        return f"{meters:,.0f} m"
    elif km < 10:
        return f"{km:,.2f} km"
    elif km < 100:
        return f"{km:,.1f} km"
    else:
        return f"{km:,.0f} km"


def get_image_url(image_path: str) -> str:
    """Convert backend image path to a proper HTTP URL for serving.
    
    The backend returns either:
    - An absolute file path (e.g., C:\\...\\cache\\gsv_48_8566_2_3522.jpg)
    - An HTTP URL (starts with http)
    
    This function converts local paths to backend-served URLs.
    """
    if not image_path:
        return ""
    
    # Already an HTTP URL - return as-is
    if image_path.startswith("http"):
        return image_path
    
    # Extract just the filename from the path and serve via backend
    filename = os.path.basename(image_path)
    return f"{BACKEND_URL}/cache/{filename}"


def get_interactive_streetview_html(lat: float, lng: float, api_key: str, initial_heading: int = 0) -> str:
    """Generate interactive Google Street View panorama HTML/JS.
    
    Features:
    - Full 360° panoramic view
    - User can look around (pan/tilt)
    - User can move along streets (if available)
    - Road labels and address hidden to prevent cheating
    - Random initial heading for variety
    
    Args:
        lat: Latitude of the location
        lng: Longitude of the location
        api_key: Google Maps JavaScript API key
        initial_heading: The initial heading for the panorama (0-360)
    
    Returns:
        HTML string with embedded Street View panorama
    """
    
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }}
            #street-view {{
                width: 100%;
                height: 500px;
                border-radius: 12px;
                overflow: hidden;
                box-shadow: 0 4px 15px rgba(0,0,0,0.2);
            }}
            #error-message {{
                display: none;
                width: 100%;
                height: 500px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                border-radius: 12px;
                color: white;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                justify-content: center;
                align-items: center;
                flex-direction: column;
                text-align: center;
                padding: 20px;
            }}
            #error-message h3 {{
                font-size: 24px;
                margin-bottom: 10px;
            }}
            #error-message p {{
                font-size: 16px;
                opacity: 0.9;
            }}
            #loading {{
                width: 100%;
                height: 500px;
                background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
                border-radius: 12px;
                display: flex;
                justify-content: center;
                align-items: center;
                flex-direction: column;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            }}
            #loading .spinner {{
                font-size: 50px;
                animation: spin 1s linear infinite;
            }}
            @keyframes spin {{
                0% {{ transform: rotate(0deg); }}
                100% {{ transform: rotate(360deg); }}
            }}
            #loading p {{
                margin-top: 15px;
                color: #667eea;
                font-weight: 600;
            }}
        </style>
    </head>
    <body>
        <div id="loading">
            <div class="spinner">🌍</div>
            <p>Loading Street View...</p>
        </div>
        <div id="street-view"></div>
        <div id="error-message">
            <h3>📍 Street View Unavailable</h3>
            <p>No Street View imagery available for this location.<br>Try submitting your best guess based on the hint!</p>
        </div>
        
        <script>
            let panorama;
            
            function initStreetView() {{
                const location = {{lat: {lat}, lng: {lng}}};
                
                // Check if Street View is available at this location
                const streetViewService = new google.maps.StreetViewService();
                
                streetViewService.getPanorama(
                    {{
                        location: location,
                        radius: 1000,  // Search within 1km radius
                        preference: google.maps.StreetViewPreference.NEAREST,
                        source: google.maps.StreetViewSource.OUTDOOR
                    }},
                    function(data, status) {{
                        document.getElementById('loading').style.display = 'none';
                        
                        if (status === google.maps.StreetViewStatus.OK) {{
                            document.getElementById('street-view').style.display = 'block';
                            
                            panorama = new google.maps.StreetViewPanorama(
                                document.getElementById('street-view'),
                                {{
                                    position: data.location.latLng,
                                    pov: {{
                                        heading: {initial_heading},
                                        pitch: 0
                                    }},
                                    zoom: 1,
                                    // Hide UI elements that could give away location
                                    addressControl: false,
                                    showRoadLabels: false,
                                    // Keep navigation controls for better UX
                                    linksControl: true,
                                    panControl: true,
                                    zoomControl: true,
                                    fullscreenControl: true,
                                    motionTracking: false,
                                    motionTrackingControl: false,
                                    // Styling
                                    scrollwheel: true,
                                    disableDefaultUI: false,
                                    enableCloseButton: false
                                }}
                            );
                        }} else {{
                            // No Street View available
                            document.getElementById('error-message').style.display = 'flex';
                        }}
                    }}
                );
            }}
            
            // Handle API load errors
            function handleApiError() {{
                document.getElementById('loading').style.display = 'none';
                document.getElementById('error-message').style.display = 'flex';
                document.getElementById('error-message').innerHTML = `
                    <h3>⚠️ API Error</h3>
                    <p>Could not load Google Maps API.<br>Please check your API key configuration.</p>
                `;
            }}
        </script>
        <script 
            src="https://maps.googleapis.com/maps/api/js?key={api_key}&callback=initStreetView"
            async 
            defer
            onerror="handleApiError()"
        ></script>
    </body>
    </html>
    """


def api_post(path, token=None, json_body=None, data=None):
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    url = f"{BACKEND_URL}{path}"
    try:
        resp = requests.post(url, json=json_body, data=data, headers=headers, timeout=30)
        resp.raise_for_status()
        return resp.json()
    except requests.HTTPError as e:
        st.error(f"API error: {e} - {resp.text}")
        return None
    except Exception as e:
        st.error(f"API request failed: {e}")
        return None


def api_get(path, token=None, params=None):
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    url = f"{BACKEND_URL}{path}"
    try:
        resp = requests.get(url, headers=headers, params=params, timeout=30)
        resp.raise_for_status()
        return resp.json()
    except requests.HTTPError as e:
        st.error(f"API error: {e} - {resp.text}")
        return None
    except Exception as e:
        st.error(f"API request failed: {e}")
        return None


def register_user(username, password):
    url = f"{BACKEND_URL}/register"
    try:
        resp = requests.post(url, json={"username": username, "password": password}, timeout=10)
        resp.raise_for_status()
        return True, resp.json()
    except requests.HTTPError as e:
        return False, resp.text
    except Exception as e:
        return False, str(e)


def login_user(username, password):
    url = f"{BACKEND_URL}/token"
    try:
        resp = requests.post(url, data={"username": username, "password": password}, timeout=10)
        resp.raise_for_status()
        return True, resp.json().get("access_token")
    except requests.HTTPError as e:
        return False, resp.text
    except Exception as e:
        return False, str(e)


def show_confetti():
    """Show celebratory confetti animation"""
    js = """
    <script src="https://cdn.jsdelivr.net/npm/canvas-confetti@1.5.1/dist/confetti.min.js"></script>
    <script>
    confetti({
      particleCount: 150,
      spread: 90,
      origin: { x: 0.5, y: 0.4 }
    })
    </script>
    """
    st.components.v1.html(js, height=0)


def show_loading_animation():
    """Show cool loading animation with globe emoji"""
    html = """
    <div style='text-align: center; padding: 20px;'>
        <div style='font-size: 60px; animation: spin 1s linear infinite; display: inline-block;'>🌍</div>
        <p style='font-size: 18px; color: #1f77b4; font-weight: bold;'>Loading location...</p>
    </div>
    <style>
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
    </style>
    """
    st.components.v1.html(html, height=120)


def get_subtle_hint(location_name: str) -> str:
    """Generate a subtle hint showing only the continent.
    
    Examples:
    - "Paris, France" -> "Europe"
    - "Tokyo, Japan" -> "Asia"
    - "New York, USA" -> "North America"
    """
    hints = {
        # Europe
        "Paris": "Europe",
        "London": "Europe",
        "Berlin": "Europe",
        "Vienna": "Europe",
        "Barcelona": "Europe",
        "Florence": "Europe",
        "Rome": "Europe",
        "Moscow": "Europe",
        "Stockholm": "Europe",
        "Helsinki": "Europe",
        # North America
        "New York": "North America",
        "Los Angeles": "North America",
        "Chicago": "North America",
        "Houston": "North America",
        "Atlanta": "North America",
        "Vancouver": "North America",
        "Toronto": "North America",
        "Portland": "North America",
        "Seattle": "North America",
        "San Francisco": "North America",
        # Asia
        "Tokyo": "Asia",
        "Shanghai": "Asia",
        "Hong Kong": "Asia",
        "Singapore": "Asia",
        "Bangkok": "Asia",
        "Seoul": "Asia",
        "Delhi": "Asia",
        "Mumbai": "Asia",
        "Osaka": "Asia",
        "Kolkata": "Asia",
        # Oceania
        "Sydney": "Oceania",
        # South America
        "São Paulo": "South America",
        "Rio de Janeiro": "South America",
        "Lima": "South America",
        "Buenos Aires": "South America",
        # Africa
        "Cape Town": "Africa",
        "Johannesburg": "Africa",
        "Cairo": "Africa",
        "Lagos": "Africa",
        "Abuja": "Africa",
    }
    
    for city, hint in hints.items():
        if city.lower() in location_name.lower():
            return hint
    
    # Default hint if city not recognized
    return "Unknown"


def get_timer_html(time_remaining: int, hint_text: str, hint_reveal_seconds: int, show_hint: bool) -> str:
    """Generate a JavaScript-powered timer that updates visually without Streamlit refreshes.
    
    The timer counts down in the browser. Streamlit only needs to check for expiration
    when the user interacts or in the final seconds.
    """
    hint_time = max(0, time_remaining - hint_reveal_seconds)
    
    return f"""
    <div id="timer-container" style="text-align: center; padding: 15px; background: linear-gradient(135deg, #22c55e22, #22c55e11); 
                border-radius: 10px; margin-bottom: 15px; border: 2px solid #22c55e; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <span id="timer-display" style="font-size: 28px; font-weight: bold; color: #22c55e;">
                ⏱️ {time_remaining}s
            </span>
            <span id="hint-display" style="font-size: 16px; color: #666;">
                💡 <span id="hint-text">{"" if show_hint else "Revealed in "}<span id="hint-countdown">{hint_text if show_hint else str(hint_time)}</span>{"" if show_hint else "s..."}</span>
            </span>
        </div>
        <div id="expired-msg" style="display: none; color: #ef4444; font-weight: bold; margin-top: 10px; font-size: 18px;">
            ⏰ Time's up! Click the map to end the round.
        </div>
    </div>
    
    <script>
    (function() {{
        let timeRemaining = {time_remaining};
        const hintRevealSeconds = {hint_reveal_seconds};
        const hintText = "{hint_text}";
        const showHint = {'true' if show_hint else 'false'};
        
        const timerDisplay = document.getElementById('timer-display');
        const timerContainer = document.getElementById('timer-container');
        const hintCountdown = document.getElementById('hint-countdown');
        const hintDisplay = document.getElementById('hint-text');
        const expiredMsg = document.getElementById('expired-msg');
        
        function updateDisplay() {{
            if (timeRemaining <= 0) {{
                timerDisplay.innerHTML = '⏱️ 0s';
                timerDisplay.style.color = '#ef4444';
                timerContainer.style.background = 'linear-gradient(135deg, #ef444422, #ef444411)';
                timerContainer.style.borderColor = '#ef4444';
                expiredMsg.style.display = 'block';
                hintDisplay.innerHTML = hintText;
                return;
            }}
            
            timerDisplay.innerHTML = '⏱️ ' + timeRemaining + 's';
            
            // Update color
            let color = timeRemaining > 30 ? '#22c55e' : (timeRemaining > 15 ? '#f59e0b' : '#ef4444');
            timerDisplay.style.color = color;
            timerContainer.style.background = 'linear-gradient(135deg, ' + color + '22, ' + color + '11)';
            timerContainer.style.borderColor = color;
            
            // Update hint
            if (timeRemaining <= hintRevealSeconds) {{
                hintDisplay.innerHTML = hintText;
            }} else if (!showHint) {{
                hintCountdown.innerHTML = (timeRemaining - hintRevealSeconds);
            }}
            
            timeRemaining--;
        }}
        
        // Update every second
        setInterval(updateDisplay, 1000);
    }})();
    </script>
    """


def new_game_state():
    import random
    return {
        "round": 0,
        "total_score": 0,
        "round_results": [],
        "current_location": None,
        "guess_submitted": False,
        "round_start_time": None,  # Track when round started for timer
        "timer_started": False,  # Timer only starts when user clicks Start Round
        "initial_heading": random.randint(0, 360),  # Store to prevent reset on rerender
        "time_expired": False,  # Flag for auto-submit on timeout
    }


def get_result_map_html(guess_lat: float, guess_lng: float, actual_lat: float, actual_lng: float, 
                         actual_name: str, distance_km: float) -> str:
    """Generate an HTML map showing the guess vs actual location with a line between them."""
    
    # Calculate center point between guess and actual
    center_lat = (guess_lat + actual_lat) / 2
    center_lng = (guess_lng + actual_lng) / 2
    
    # Determine zoom level based on distance
    if distance_km < 1:
        zoom = 14
    elif distance_km < 10:
        zoom = 11
    elif distance_km < 100:
        zoom = 8
    elif distance_km < 1000:
        zoom = 5
    elif distance_km < 5000:
        zoom = 3
    else:
        zoom = 2
    
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
        <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
        <style>
            #result-map {{
                width: 100%;
                height: 400px;
                border-radius: 12px;
                box-shadow: 0 4px 15px rgba(0,0,0,0.2);
            }}
        </style>
    </head>
    <body>
        <div id="result-map"></div>
        <script>
            var map = L.map('result-map').setView([{center_lat}, {center_lng}], {zoom});
            
            L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
                attribution: '© OpenStreetMap contributors'
            }}).addTo(map);
            
            // Your guess marker (blue)
            var guessIcon = L.divIcon({{
                html: '<div style="background:#3b82f6; width:24px; height:24px; border-radius:50%; border:3px solid white; box-shadow:0 2px 5px rgba(0,0,0,0.3);"></div>',
                iconSize: [24, 24],
                iconAnchor: [12, 12],
                className: 'guess-marker'
            }});
            L.marker([{guess_lat}, {guess_lng}], {{icon: guessIcon}})
                .addTo(map)
                .bindPopup('<b>📍 Your Guess</b>');
            
            // Actual location marker (green)
            var actualIcon = L.divIcon({{
                html: '<div style="background:#22c55e; width:24px; height:24px; border-radius:50%; border:3px solid white; box-shadow:0 2px 5px rgba(0,0,0,0.3);"></div>',
                iconSize: [24, 24],
                iconAnchor: [12, 12],
                className: 'actual-marker'
            }});
            L.marker([{actual_lat}, {actual_lng}], {{icon: actualIcon}})
                .addTo(map)
                .bindPopup('<b>📍 {actual_name}</b>');
            
            // Line between guess and actual
            var line = L.polyline([
                [{guess_lat}, {guess_lng}],
                [{actual_lat}, {actual_lng}]
            ], {{
                color: '#ef4444',
                weight: 3,
                opacity: 0.8,
                dashArray: '10, 10'
            }}).addTo(map);
            
            // Fit bounds to show both markers
            map.fitBounds(line.getBounds(), {{padding: [50, 50]}});
        </script>
    </body>
    </html>
    """


def show_auth_page():
    """Display a dedicated login/signup page (called after page config is set)."""
    
    # Custom CSS for auth page
    st.markdown("""
    <style>
    .main {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        min-height: 100vh;
    }
    .stButton button {
        background-color: #667eea;
        color: white;
        font-weight: bold;
        border-radius: 8px;
        border: none;
        padding: 12px 24px;
        width: 100%;
        transition: all 0.3s;
    }
    .stButton button:hover {
        background-color: #764ba2;
        transform: scale(1.02);
    }
    .auth-container {
        background: white;
        padding: 40px;
        border-radius: 20px;
        box-shadow: 0 10px 40px rgba(0,0,0,0.2);
        max-width: 450px;
        margin: 0 auto;
    }
    .auth-header {
        text-align: center;
        margin-bottom: 30px;
    }
    .auth-header h1 {
        color: #667eea;
        font-size: 28px;
        margin-bottom: 10px;
    }
    .auth-header p {
        color: #666;
        font-size: 14px;
    }
    div[data-testid="stTabs"] button {
        font-size: 16px;
        font-weight: 600;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Center the content
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("""
        <div style='text-align: center; padding: 20px 0 30px 0;'>
            <h1 style='font-size: 48px; margin-bottom: 5px;'>🌍</h1>
            <h1 style='color: #667eea; font-size: 32px; margin-bottom: 10px;'>Where Am I?</h1>
            <p style='color: #666; font-size: 16px;'>Test your geography skills with Google Street View</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Create tabs for Login and Register
        tab_login, tab_register = st.tabs(["🔓 Login", "📝 Register"])
        
        with tab_login:
            st.markdown("<br>", unsafe_allow_html=True)
            login_username = st.text_input("Username", key="login_user", placeholder="Enter your username")
            login_password = st.text_input("Password", type="password", key="login_pw", placeholder="Enter your password")
            
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("Login", use_container_width=True, key="login_btn"):
                if not login_username or not login_password:
                    st.error("Please enter username and password")
                else:
                    ok, token = login_user(login_username, login_password)
                    if ok and token:
                        st.session_state.token = token
                        st.success("Logged in successfully!")
                        time.sleep(0.5)
                        st.rerun()
                    else:
                        st.error(f"❌ Login failed: {token}")
        
        with tab_register:
            st.markdown("<br>", unsafe_allow_html=True)
            reg_username = st.text_input("Username", key="reg_user", placeholder="Choose a username")
            reg_password = st.text_input("Password", type="password", key="reg_pw", placeholder="Choose a password")
            reg_password2 = st.text_input("Confirm Password", type="password", key="reg_pw2", placeholder="Confirm your password")
            
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("Create Account", use_container_width=True, key="reg_btn"):
                if not reg_username or not reg_password:
                    st.error("Please enter username and password")
                elif reg_password != reg_password2:
                    st.error("Passwords do not match")
                elif len(reg_password) < 4:
                    st.error("Password must be at least 4 characters")
                else:
                    ok, resp = register_user(reg_username, reg_password)
                    if ok:
                        st.success("Account created! You can now login.")
                    else:
                        st.error(f"❌ Registration failed: {resp}")
        
        # Show leaderboard preview
        st.markdown("<br><hr><br>", unsafe_allow_html=True)
        st.markdown("### 🏆 Top Players")
        lb = api_get("/leaderboard", token=None)
        if lb and len(lb) > 0:
            for i, item in enumerate(lb[:5], 1):
                medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
                st.write(f"{medal} **{item['username']}** - {item['total_score']:,} pts")
        else:
            st.info("No scores yet. Be the first to play!")


def main():
    # Initialize session state first (before page config)
    if "token" not in st.session_state:
        st.session_state.token = None
    if "game" not in st.session_state:
        st.session_state.game = new_game_state()
    
    # Set page config based on auth status (must be first Streamlit command)
    if not st.session_state.token:
        st.set_page_config(page_title="Where Am I? - Login", layout="centered", initial_sidebar_state="collapsed")
        show_auth_page()
        return
    
    # User is logged in - show the game with wide layout
    st.set_page_config(page_title="Where Am I?", layout="wide", initial_sidebar_state="expanded")

    # Custom CSS for better styling
    st.markdown("""
    <style>
    .main {
        background-color: #f5f5f5;
    }
    .stButton button {
        background-color: #667eea;
        color: white;
        font-weight: bold;
        border-radius: 8px;
        border: none;
        padding: 10px 20px;
        transition: all 0.3s;
    }
    .stButton button:hover {
        background-color: #764ba2;
        transform: scale(1.05);
    }
    </style>
    """, unsafe_allow_html=True)

    # Remove duplicate session state init (already done above)
    
    # Header with emoji
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<h1>🌍 Where Am I? 🎯</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: #666;'>Test your geography skills with Google Street View</p>", unsafe_allow_html=True)

    # Sidebar: logout and leaderboard (user is already logged in)
    with st.sidebar:
        st.markdown("### 👤 Account")
        st.success(f"Logged in")
        if st.button("🚪 Logout", use_container_width=True):
            st.session_state.token = None
            st.session_state.game = new_game_state()
            st.rerun()

        st.markdown("---")
        st.subheader("🏆 Leaderboard")
        st.caption("Best single-game scores")
        lb = api_get("/leaderboard", token=st.session_state.token)
        if lb:
            for i, item in enumerate(lb, 1):
                medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
                games = item.get('games_played', 0)
                st.write(f"{medal} **{item['username']}** - {item['total_score']:,} pts ({games} games)")
        else:
            st.info("No leaderboard data yet. Complete a game to appear!")

    # Game layout
    col_main, col_stats = st.columns([2.5, 1], gap="large")

    with col_main:
        st.markdown(f"""
        <div class='game-card'>
        <h2>Round {st.session_state.game['round'] + 1} / {ROUNDS_PER_GAME}</h2>
        </div>
        """, unsafe_allow_html=True)

        # Fetch location if needed
        if st.session_state.game["current_location"] is None:
            with st.spinner("Loading new location..."):
                loc = api_get("/random_location", token=st.session_state.token)
            if not loc:
                st.error("❌ Failed to fetch location")
                return
            st.session_state.game["current_location"] = loc
            st.session_state.game["guess_submitted"] = False
            st.session_state.game["round_start_time"] = None  # Will be set when user clicks "Start Round"
            st.session_state.game["timer_started"] = False

        loc = st.session_state.game["current_location"]
        
        # Initialize initial_heading if not set
        if st.session_state.game.get("initial_heading") is None:
            import random
            st.session_state.game["initial_heading"] = random.randint(0, 360)
        
        # Check for time expiration
        if st.session_state.game.get("timer_started", False) and not st.session_state.game["guess_submitted"]:
            elapsed = time.time() - st.session_state.game["round_start_time"] if st.session_state.game["round_start_time"] else 0
            time_remaining = max(0, int(ROUND_TIME_SECONDS - elapsed))
            
            # Auto-end round if time expired (award 0 points, no guess)
            if time_remaining <= 0 and not st.session_state.game.get("time_expired", False):
                st.session_state.game["time_expired"] = True
                st.session_state.game["guess_submitted"] = True
                # Award 0 points for timeout - don't increment round yet (wait for Next Round click)
                st.session_state.game["round_results"].append({
                    "dist": None,  # No guess made
                    "pts": 0, 
                    "guess_lat": None, 
                    "guess_lng": None,
                    "timeout": True
                })
                st.rerun()
        else:
            time_remaining = ROUND_TIME_SECONDS
        
        show_hint = time_remaining <= HINT_REVEAL_SECONDS or st.session_state.game["guess_submitted"]
        hint = get_subtle_hint(loc['name'])
        
        # Initialize last_clicked to avoid unbound variable error
        last_clicked = None
        
        # Pre-round: Show "Start Round" button, hide Street View
        if not st.session_state.game.get("timer_started", False) and not st.session_state.game["guess_submitted"]:
            st.markdown("""
            <div style='text-align: center; padding: 40px; background: linear-gradient(135deg, #667eea22, #764ba211); 
                        border-radius: 15px; margin: 20px 0; border: 2px dashed #667eea'>
                <h3 style='color: #667eea; margin-bottom: 10px;'>🌍 Location Ready!</h3>
                <p style='color: #666;'>Click the button below to reveal the Street View and start the timer.</p>
            </div>
            """, unsafe_allow_html=True)
            
            if st.button("▶️ Start Round", use_container_width=True, type="primary"):
                st.session_state.game["round_start_time"] = time.time()
                st.session_state.game["timer_started"] = True
                st.session_state.game["time_expired"] = False
                st.rerun()
            
            st.info("💡 **Hint:** *Start the round to reveal hint countdown*")
            st.info("👆 Click **Start Round** above to begin guessing!")
        
        # During round or after submission
        else:
            # Only auto-refresh in the last 5 seconds to detect expiration
            # This prevents constant re-renders while the user is interacting with the map
            if st.session_state.game.get("timer_started", False) and not st.session_state.game["guess_submitted"]:
                if time_remaining <= 5 and time_remaining > 0:
                    # Refresh every second only in final 5 seconds
                    st_autorefresh(interval=1000, limit=10, key="timer_refresh_final")
                
                timer_html = get_timer_html(
                    time_remaining=time_remaining,
                    hint_text=hint,
                    hint_reveal_seconds=HINT_REVEAL_SECONDS,
                    show_hint=show_hint
                )
                st.components.v1.html(timer_html, height=80)
            elif st.session_state.game["guess_submitted"]:
                st.markdown(f"💡 **Hint:** {hint}")

            # Display interactive Street View panorama
            if GOOGLE_MAPS_API_KEY:
                streetview_html = get_interactive_streetview_html(
                    lat=loc["lat"],
                    lng=loc["lng"],
                    api_key=GOOGLE_MAPS_API_KEY,
                    initial_heading=st.session_state.game["initial_heading"]
                )
                st.components.v1.html(streetview_html, height=520, scrolling=False)
                st.caption("🎮 **Tip:** Drag to look around, click arrows to move along streets!")
            elif loc.get("image_url"):
                image_url = get_image_url(loc["image_url"])
                st.image(image_url, use_container_width=True, caption="📸 Street View - Click the map to guess!")
            else:
                st.warning("⚠️ No Street View available. Configure GOOGLE_MAPS_API_KEY for interactive view.")

            st.markdown("---")

            # Interactive guess map - show user's pin directly on this map
            m = folium.Map(location=[20, 0], zoom_start=2, tiles="OpenStreetMap")
            
            # Show actual location marker after guess is submitted
            if st.session_state.game["guess_submitted"]:
                folium.Marker(
                    location=[loc["lat"], loc["lng"]],
                    popup=f"<b>{loc['name']}</b>",
                    icon=folium.Icon(color='green', icon='check', prefix='fa'),
                    tooltip="Actual Location"
                ).add_to(m)
            
            # Add click popup to show coordinates
            m.add_child(folium.LatLngPopup())
            st.components.v1.html("<style>.leaflet-container { cursor: crosshair !important; }</style>", height=0)
            
            # Instructions for guessing
            if not st.session_state.game["guess_submitted"]:
                st.caption("📍 **Click on the map to place your guess, then click Submit**")
            
            map_data = st_folium(m, width=700, height=450, key=f"map_{st.session_state.game['round']}_{st.session_state.game['timer_started']}")
            last_clicked = map_data.get("last_clicked") if map_data else None

        # Handle guess submission - no confirmation map, just show coordinates and submit button
        if last_clicked and not st.session_state.game["guess_submitted"]:
            guess_lat = last_clicked["lat"]
            guess_lng = last_clicked["lng"]
            
            # Show selected coordinates and submit button in a compact format
            col_coords, col_submit = st.columns([2, 1])
            with col_coords:
                st.markdown(f"📍 **Your guess:** `{guess_lat:.4f}, {guess_lng:.4f}`")
            with col_submit:
                if st.button("Submit Guess", use_container_width=True, type="primary", key=f"submit_{st.session_state.game['round']}"):
                    payload = {"location_id": loc["id"], "guess_lat": guess_lat, "guess_lng": guess_lng}
                    result = api_post("/submit_guess", token=st.session_state.token, json_body=payload)
                    if result:
                        dist = result["distance_meters"]
                        dist_km = dist / 1000
                        pts = result["points_awarded"]
                        st.session_state.game["total_score"] += pts
                        st.session_state.game["round_results"].append({"dist": dist, "pts": pts, "guess_lat": guess_lat, "guess_lng": guess_lng})
                        st.session_state.game["guess_submitted"] = True
                        st.rerun()
        
        # Show results after submission (not timeout)
        if st.session_state.game["guess_submitted"] and st.session_state.game["round_results"]:
            last_result = st.session_state.game["round_results"][-1]
            if not last_result.get("timeout", False):
                dist = last_result["dist"]
                pts = last_result["pts"]
                guess_lat = last_result["guess_lat"]
                guess_lng = last_result["guess_lng"]
                dist_km = dist / 1000
                
                # Show confetti and feedback
                show_confetti()
                
                dist_str = format_distance(dist)
                if dist < 1000:  # Less than 1km
                    st.success(f"🎯 **Amazing!** {pts:,} points | Distance: {dist_str}")
                elif dist < 50000:  # Less than 50km
                    st.info(f"👍 **Great!** {pts:,} points | Distance: {dist_str}")
                elif dist < 500000:  # Less than 500km
                    st.warning(f"📍 Good try! {pts:,} points | Distance: {dist_str}")
                else:
                    st.error(f"🌐 Keep practicing! {pts:,} points | Distance: {dist_str}")
                
                st.markdown(f"🎲 **Actual location:** {loc['name']}")
                
                # Show result map with guess vs actual location
                st.markdown("### 🗺️ Result Map")
                result_map_html = get_result_map_html(
                    guess_lat=guess_lat,
                    guess_lng=guess_lng,
                    actual_lat=loc["lat"],
                    actual_lng=loc["lng"],
                    actual_name=loc["name"],
                    distance_km=dist_km
                )
                st.components.v1.html(result_map_html, height=420)
                
                # Game over check - use number of results
                rounds_completed = len(st.session_state.game["round_results"])
                if rounds_completed >= ROUNDS_PER_GAME:
                    # Submit final game score to update leaderboard
                    final_score = st.session_state.game['total_score']
                    game_result = api_post("/submit_game_score", token=st.session_state.token, json_body={"game_score": final_score})
                    
                    time.sleep(2)
                    st.balloons()
                    st.markdown("---")
                    st.markdown(f"<h2 style='text-align: center; color: #667eea;'>🎉 Game Over! 🎉</h2>", unsafe_allow_html=True)
                    st.markdown(f"<p style='text-align: center; font-size: 32px; color: #764ba2;'>Final Score: {final_score:,} points</p>", unsafe_allow_html=True)
                    
                    # Show if this is a new personal best
                    if game_result and game_result.get("is_new_best"):
                        st.success("🏆 **New Personal Best!**")
                    elif game_result:
                        st.info(f"Your best score: {game_result.get('best_game_score', 0):,} points")
                    
                    if st.button("🔄 Play Again", use_container_width=True):
                        st.session_state.game = new_game_state()
                        st.rerun()
                else:
                    st.markdown("---")
                    if st.button("➡️ Next Round", use_container_width=True, key=f"next_{st.session_state.game['round']}_{rounds_completed}"):
                        import random
                        st.session_state.game["round"] += 1  # Increment round only when clicking Next
                        st.session_state.game["current_location"] = None
                        st.session_state.game["timer_started"] = False
                        st.session_state.game["round_start_time"] = None
                        st.session_state.game["initial_heading"] = random.randint(0, 360)
                        st.session_state.game["time_expired"] = False
                        st.session_state.game["guess_submitted"] = False
                        st.rerun()
        elif st.session_state.game["guess_submitted"]:
            # Check if this was a timeout
            last_result = st.session_state.game["round_results"][-1] if st.session_state.game["round_results"] else None
            is_timeout = last_result and last_result.get("timeout", False)
            
            if is_timeout:
                # Show timeout message
                st.error("⏰ **Time's Up!** You didn't submit a guess in time.")
                st.markdown(f"**0 points** awarded for this round.")
                st.markdown(f"🎲 **The location was:** {loc['name']}")
                
                # Show just the actual location on a map
                timeout_map = folium.Map(location=[loc["lat"], loc["lng"]], zoom_start=6, tiles="OpenStreetMap")
                folium.Marker(
                    location=[loc["lat"], loc["lng"]],
                    popup=f"<b>{loc['name']}</b>",
                    icon=folium.Icon(color='green', icon='check', prefix='fa'),
                    tooltip="Actual Location"
                ).add_to(timeout_map)
                st_folium(timeout_map, width=700, height=400)
            
            # Game over check - use number of results to check completion
            rounds_completed = len(st.session_state.game["round_results"])
            if rounds_completed >= ROUNDS_PER_GAME:
                # Submit final game score to update leaderboard
                final_score = st.session_state.game['total_score']
                game_result = api_post("/submit_game_score", token=st.session_state.token, json_body={"game_score": final_score})
                
                st.balloons()
                st.markdown("---")
                st.markdown(f"<h2 style='text-align: center; color: #667eea;'>🎉 Game Over! 🎉</h2>", unsafe_allow_html=True)
                st.markdown(f"<p style='text-align: center; font-size: 32px; color: #764ba2;'>Final Score: {final_score:,} points</p>", unsafe_allow_html=True)
                
                # Show if this is a new personal best
                if game_result and game_result.get("is_new_best"):
                    st.success("🏆 **New Personal Best!**")
                elif game_result:
                    st.info(f"Your best score: {game_result.get('best_game_score', 0):,} points")
                
                if st.button("🔄 Play Again", use_container_width=True):
                    st.session_state.game = new_game_state()
                    st.rerun()
            else:
                # Show next round button
                st.markdown("---")
                if st.button("➡️ Next Round", use_container_width=True, key=f"next_{st.session_state.game['round']}_{rounds_completed}"):
                    import random
                    st.session_state.game["round"] += 1  # Increment round here
                    st.session_state.game["current_location"] = None
                    st.session_state.game["timer_started"] = False
                    st.session_state.game["round_start_time"] = None
                    st.session_state.game["initial_heading"] = random.randint(0, 360)
                    st.session_state.game["time_expired"] = False
                    st.session_state.game["guess_submitted"] = False
                    st.rerun()

    with col_stats:
        st.subheader("📊 Your Stats")
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Points", f"{st.session_state.game['total_score']:,}")
        with col2:
            # Show current round number (1-indexed) vs total
            current_round = st.session_state.game['round'] + 1
            st.metric("Round", f"{current_round}/{ROUNDS_PER_GAME}")
        
        st.divider()
        st.subheader("📈 Recent Results")
        if st.session_state.game["round_results"]:
            results = st.session_state.game["round_results"][-5:]  # Last 5 results
            total_results = len(st.session_state.game["round_results"])
            for i, r in enumerate(reversed(results)):
                round_num = total_results - i  # Calculate from total results
                if r.get("timeout", False):
                    st.write(f"**Round {round_num}:** ⏰ Timeout | 0 pts")
                else:
                    dist_str = format_distance(r['dist'])
                    st.write(f"**Round {round_num}:** {r['pts']:,} pts | {dist_str} away")
        else:
            st.info("No results yet")


if __name__ == "__main__":
    main()
