"""
Streamlit frontend for Street Smarts - a geography guessing game.

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

load_dotenv()

import time
import requests
import streamlit as st
from streamlit_folium import st_folium
import folium
import json
from datetime import datetime

# --------------------
# Configuration
# --------------------
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
ROUNDS_PER_GAME = 5  # 5 rounds per game


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
    """Generate a subtle hint instead of revealing the exact city
    
    Examples:
    - "Paris, France" -> "Somewhere in Europe"
    - "Tokyo, Japan" -> "Somewhere in Asia"
    - "New York, USA" -> "Somewhere in North America"
    """
    hints = {
        "Paris": "🇫🇷 Western Europe",
        "London": "🇬🇧 British Isles",
        "Berlin": "🇩🇪 Central Europe",
        "Vienna": "🇦🇹 Central Europe",
        "Barcelona": "🇪🇸 Mediterranean",
        "Florence": "🇮🇹 Southern Europe",
        "Rome": "🇮🇹 Southern Europe",
        "Moscow": "🇷🇺 Eastern Europe",
        "Stockholm": "🇸🇪 Northern Europe",
        "Helsinki": "🇫🇮 Nordic Region",
        "New York": "🇺🇸 North America (East Coast)",
        "Los Angeles": "🇺🇸 North America (West Coast)",
        "Chicago": "🇺🇸 North America (Midwest)",
        "Houston": "🇺🇸 North America (South)",
        "Atlanta": "🇺🇸 North America (South)",
        "Vancouver": "🇨🇦 North America",
        "Toronto": "🇨🇦 North America",
        "Portland": "🇺🇸 North America (West Coast)",
        "Seattle": "🇺🇸 North America (West Coast)",
        "San Francisco": "🇺🇸 North America (West Coast)",
        "Tokyo": "🇯🇵 East Asia",
        "Shanghai": "🇨🇳 East Asia",
        "Hong Kong": "🇭🇰 East Asia",
        "Singapore": "🇸🇬 Southeast Asia",
        "Bangkok": "🇹🇭 Southeast Asia",
        "Seoul": "🇰🇷 East Asia",
        "Delhi": "🇮🇳 South Asia",
        "Mumbai": "🇮🇳 South Asia",
        "Osaka": "🇯🇵 East Asia",
        "Kolkata": "🇮🇳 South Asia",
        "Sydney": "🇦🇺 Oceania",
        "São Paulo": "🇧🇷 South America",
        "Rio de Janeiro": "🇧🇷 South America",
        "Lima": "🇵🇪 South America",
        "Buenos Aires": "🇦🇷 South America",
        "Cape Town": "🇿🇦 Southern Africa",
        "Johannesburg": "🇿🇦 Southern Africa",
        "Cairo": "🇪🇬 North Africa",
        "Lagos": "🇳🇬 West Africa",
        "Abuja": "🇳🇬 West Africa",
    }
    
    for city, hint in hints.items():
        if city.lower() in location_name.lower():
            return hint
    
    # Default hint if city not recognized
    return "🗺️ Somewhere in the world"


def new_game_state():
    return {
        "round": 0,
        "total_score": 0,
        "round_results": [],
        "current_location": None,
        "guess_submitted": False,
    }


def main():
    st.set_page_config(page_title="Street Smarts - Guess The Location", layout="wide", initial_sidebar_state="expanded")

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

    if "token" not in st.session_state:
        st.session_state.token = None
    if "game" not in st.session_state:
        st.session_state.game = new_game_state()

    # Header with emoji
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<h1>🌍 Street Smarts - Guess The Location 🎯</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: #666;'>Test your geography skills with Google Street View</p>", unsafe_allow_html=True)

    # Sidebar: login / register / leaderboard
    with st.sidebar:
        st.markdown("### 👤 Account")
        if not st.session_state.token:
            choice = st.radio("Select Action", ["Login", "Register"], key="auth_choice")
            username = st.text_input("Username", key="auth_user")
            password = st.text_input("Password", type="password", key="auth_pw")
            if choice == "Register":
                if st.button("✅ Register", use_container_width=True):
                    if not username or not password:
                        st.error("Please enter username and password")
                    else:
                        ok, resp = register_user(username, password)
                        if ok:
                            st.success("✅ Account created! Now you can log in.")
                        else:
                            st.error(f"❌ Registration failed: {resp}")
            else:
                if st.button("🔓 Login", use_container_width=True):
                    if not username or not password:
                        st.error("Please enter username and password")
                    else:
                        ok, token = login_user(username, password)
                        if ok and token:
                            st.session_state.token = token
                            st.success("✅ Logged in!")
                            st.rerun()
                        else:
                            st.error(f"❌ Login failed: {token}")
        else:
            st.success(f"✅ Logged in")
            if st.button("🚪 Logout", use_container_width=True):
                st.session_state.token = None
                st.session_state.game = new_game_state()
                st.rerun()

        st.markdown("---")
        st.subheader("🏆 Leaderboard")
        lb = api_get("/leaderboard", token=st.session_state.token)
        if lb:
            for i, item in enumerate(lb, 1):
                medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
                st.write(f"{medal} **{item['username']}** - {item['total_score']:,} pts")
        else:
            st.info("No leaderboard data yet")

    # Main gameplay area
    if not st.session_state.token:
        st.info("👉 **Log in to start playing!** Use the sidebar to register or log in.")
        return

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
            with st.spinner(""):
                show_loading_animation()
            loc = api_get("/random_location", token=st.session_state.token)
            if not loc:
                st.error("❌ Failed to fetch location")
                return
            st.session_state.game["current_location"] = loc
            st.session_state.game["guess_submitted"] = False

        loc = st.session_state.game["current_location"]

        # Subtle hint instead of exact location
        hint = get_subtle_hint(loc['name'])
        st.markdown(f"💡 **Hint:** {hint}")

        # Display the cached image
        if loc.get("image_url"):
            st.image(loc["image_url"], use_container_width=True, caption="📸 Street View - Click the map to guess!")
        else:
            st.warning("⚠️ No Street View image available for this location.")

        st.markdown("---")

        # Interactive map with actual location pin
        m = folium.Map(location=[20, 0], zoom_start=2, tiles="OpenStreetMap")
        
        # Add the ACTUAL location as a hidden marker (for pinning after guess)
        # But don't show it during the guess
        if st.session_state.game["guess_submitted"]:
            # Show the actual location pin after guess submitted
            folium.Marker(
                location=[loc["lat"], loc["lng"]],
                popup=f"<b>{loc['name']}</b>",
                icon=folium.Icon(color='green', icon='check', prefix='fa'),
                tooltip="Actual Location"
            ).add_to(m)
        
        # Show click popup
        m.add_child(folium.LatLngPopup())
        
        # Instruction
        st.components.v1.html("<style>.leaflet-container { cursor: crosshair !important; }</style>", height=0)
        
        map_data = st_folium(m, width=700, height=500)
        last_clicked = map_data.get("last_clicked") if map_data else None

        # Show clicked location with marker on new map for confirmation
        if last_clicked and not st.session_state.game["guess_submitted"]:
            guess_lat = last_clicked["lat"]
            guess_lng = last_clicked["lng"]
            
            # Show confirmation map with their guess
            st.markdown(f"📍 **Your guess:** {guess_lat:.4f}, {guess_lng:.4f}")
            
            # Show mini map with their guess pinned
            confirm_map = folium.Map(location=[guess_lat, guess_lng], zoom_start=10, tiles="OpenStreetMap")
            folium.Marker(
                location=[guess_lat, guess_lng],
                popup="Your Guess",
                icon=folium.Icon(color='blue', icon='map-pin', prefix='fa')
            ).add_to(confirm_map)
            st_folium(confirm_map, width=700, height=300)
            
            if st.button("✅ Submit This Guess", use_container_width=True, key=f"submit_{st.session_state.game['round']}"):
                payload = {"location_id": loc["id"], "guess_lat": guess_lat, "guess_lng": guess_lng}
                result = api_post("/submit_guess", token=st.session_state.token, json_body=payload)
                if result:
                    dist = result["distance_meters"]
                    pts = result["points_awarded"]
                    st.session_state.game["total_score"] += pts
                    st.session_state.game["round_results"].append({"dist": dist, "pts": pts})
                    st.session_state.game["guess_submitted"] = True
                    
                    # Show confetti and feedback
                    show_confetti()
                    
                    if dist < 100:
                        st.success(f"🎯 **Amazing!** {pts:,} points | Distance: {dist:,.0f}m")
                    elif dist < 5000:
                        st.info(f"👍 **Great!** {pts:,} points | Distance: {dist:,.0f}m")
                    elif dist < 50000:
                        st.warning(f"📍 Good try! {pts:,} points | Distance: {dist:,.0f}m")
                    else:
                        st.error(f"🌐 Keep practicing! {pts:,} points | Distance: {dist:,.0f}m")
                    
                    st.markdown(f"🎲 **Actual location:** {loc['name']}")
                    
                    st.session_state.game["round"] += 1
                    
                    # Game over check
                    if st.session_state.game["round"] >= ROUNDS_PER_GAME:
                        time.sleep(2)
                        st.balloons()
                        st.markdown("---")
                        st.markdown(f"<h2 style='text-align: center; color: #667eea;'>🎉 Game Over! 🎉</h2>", unsafe_allow_html=True)
                        st.markdown(f"<p style='text-align: center; font-size: 32px; color: #764ba2;'>Final Score: {st.session_state.game['total_score']:,} points</p>", unsafe_allow_html=True)
                        
                        if st.button("🔄 Play Again", use_container_width=True):
                            st.session_state.game = new_game_state()
                            st.rerun()
                    else:
                        st.markdown("---")
                        if st.button("➡️ Next Round", use_container_width=True, key=f"next_{st.session_state.game['round']}"):
                            st.session_state.game["current_location"] = None
                            st.rerun()
        elif st.session_state.game["guess_submitted"]:
            # After submission, show next round button
            st.markdown("---")
            if st.button("➡️ Next Round", use_container_width=True, key=f"next_{st.session_state.game['round']}"):
                st.session_state.game["current_location"] = None
                st.rerun()

    with col_stats:
        st.subheader("📊 Your Stats")
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Points", f"{st.session_state.game['total_score']:,}")
        with col2:
            st.metric("Rounds", f"{st.session_state.game['round']}/{ROUNDS_PER_GAME}")
        
        st.divider()
        st.subheader("📈 Recent Results")
        if st.session_state.game["round_results"]:
            for i, r in enumerate(reversed(st.session_state.game["round_results"][-5:]), 1):
                st.write(f"**Round {st.session_state.game['round']-i}:** {r['pts']:,} pts | {r['dist']:,.0f}m away")
        else:
            st.info("No results yet")


if __name__ == "__main__":
    main()
