import os
from dotenv import load_dotenv

load_dotenv()

import math
import io
import random
import csv
import hashlib
import shutil
from typing import Optional
from pathlib import Path

from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from pydantic import BaseModel
from sqlalchemy import Column, Integer, String, Float
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from passlib.context import CryptContext
import requests
import jwt

# --------------------
# Configuration
# --------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "app.db")
CACHE_DIR = os.path.join(BASE_DIR, "cache")
os.makedirs(CACHE_DIR, exist_ok=True)

JWT_SECRET = os.getenv("JWT_SECRET")
if not JWT_SECRET:
    raise ValueError("JWT_SECRET environment variable is required. Please set it in your .env file.")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # not enforced in this simple example

# Google Street View API key
GOOGLE_STREETVIEW_KEY = os.getenv("GOOGLE_STREETVIEW_KEY")
if not GOOGLE_STREETVIEW_KEY:
    raise ValueError("GOOGLE_STREETVIEW_KEY environment variable is required. Please set it in your .env file.")

MAX_POINTS = 5000
SCORE_SCALE_METERS = 20000.0  # decay scale for exponential scoring

# --------------------
# Database setup
# --------------------
SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_PATH}"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    total_score = Column(Integer, default=0)
    rounds_played = Column(Integer, default=0)


class Location(Base):
    __tablename__ = "locations"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    lat = Column(Float, nullable=False)
    lng = Column(Float, nullable=False)
    image_filename = Column(String, nullable=True)  # cached image filename (deprecated)
    image_url = Column(String, nullable=True)  # cached SVG data URI or image URL


Base.metadata.create_all(bind=engine)

# --------------------
# Security
# --------------------
# Use PBKDF2-SHA256 by default to avoid system bcrypt backend issues and
# the 72-byte bcrypt input limit on some platforms. PBKDF2 is secure and
# easier to install cross-platform for this demo. For production consider
# Argon2 or a managed identity provider.
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/token")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    return pwd_context.hash(password)


def create_access_token(data: dict):
    # NOTE: For simplicity token does not expire in this example; add exp claim in production
    return jwt.encode(data, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str):
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.PyJWTError:
        return None


def get_user_by_username(db: Session, username: str):
    return db.query(User).filter(User.username == username).first()


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authentication credentials")
    username = payload.get("sub")
    if username is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authentication payload")
    user = get_user_by_username(db, username)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


# --------------------
# Pydantic schemas
# --------------------


class RegisterRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class RandomLocationResponse(BaseModel):
    id: int
    name: str
    lat: float
    lng: float
    image_url: str
    image_error: Optional[str] = None


class GuessRequest(BaseModel):
    location_id: int
    guess_lat: float
    guess_lng: float


class GuessResponse(BaseModel):
    distance_meters: float
    points_awarded: int
    total_score: int


class FetchImageRequest(BaseModel):
    lat: float
    lng: float
    location_id: Optional[int] = None


class FetchImageResponse(BaseModel):
    image_url: str


app = FastAPI(title="Street Smarts API")
app.mount("/cache", StaticFiles(directory=CACHE_DIR), name="cache")


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


@app.post("/register", status_code=201)
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    # Create a new user with a securely hashed password
    if get_user_by_username(db, req.username):
        raise HTTPException(status_code=400, detail="Username already registered")
    # Basic server-side password validation: enforce reasonable length to
    # avoid very large inputs and improve UX. PBKDF2 does not have bcrypt's
    # 72-byte limit, but keeping a cap is still sensible.
    if not isinstance(req.password, str) or len(req.password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters long")
    if len(req.password) > 256:
        raise HTTPException(status_code=400, detail="Password too long; maximum is 256 characters")
    hashed = get_password_hash(req.password)
    user = User(username=req.username, hashed_password=hashed)
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"msg": "user created"}


@app.post("/token", response_model=TokenResponse)
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    # Standard OAuth2 password flow endpoint returning a JWT
    user = get_user_by_username(db, form_data.username)
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect username or password")
    token = create_access_token({"sub": user.username})
    return {"access_token": token}


def haversine_distance(lat1, lon1, lat2, lon2):
    # Returns distance in meters between two lat/lng pairs
    R = 6371000  # earth radius in meters
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def compute_points(distance_meters: float) -> int:
    # Exponentially decaying scoring: max at zero distance, decays with distance
    points = MAX_POINTS * math.exp(-distance_meters / SCORE_SCALE_METERS)
    return max(0, int(round(points)))


def cache_gsv_image(lat: float, lng: float) -> Optional[str]:
    """Download and cache Google Street View image locally.
    
    Returns absolute file path if successful, None otherwise.
    Caches based on coordinates to avoid duplicate downloads.
    """
    # Generate cache filename from coordinates
    cache_key = f"gsv_{lat}_{lng}".replace(".", "_").replace("-", "m")
    cache_file = os.path.join(CACHE_DIR, f"{cache_key}.jpg")
    
    # Return existing cache if available (use absolute path)
    if os.path.exists(cache_file):
        return cache_file
    
    try:
        # Download image from Google Street View Static API
        url = (
            f"https://maps.googleapis.com/maps/api/streetview?"
            f"size=400x300"
            f"&location={lat},{lng}"
            f"&key={GOOGLE_STREETVIEW_KEY}"
        )
        resp = requests.get(url, timeout=10)
        
        if resp.status_code == 200 and resp.headers.get("content-type", "").startswith("image"):
            # Save to cache directory
            with open(cache_file, "wb") as f:
                f.write(resp.content)
            print(f"  Cached: {cache_key}")
            return cache_file  # Return absolute path
        else:
            print(f"  Failed to cache {cache_key}: HTTP {resp.status_code}")
            return None
    except Exception as e:
        print(f"  Error caching image for ({lat}, {lng}): {e}")
        return None


def fetch_google_streetview_url(lat: float, lng: float, size: str = "400x300") -> str:
    """Generate a Google Street View static image URL for the given coordinates."""
    return (
        f"https://maps.googleapis.com/maps/api/streetview?"
        f"size={size}"
        f"&location={lat},{lng}"
        f"&key={GOOGLE_STREETVIEW_KEY}"
    )













@app.get("/random_location", response_model=RandomLocationResponse)
def random_location(db: Session = Depends(get_db)):
    # Return a random location, downloading and caching image if needed
    locations = db.query(Location).all()
    if not locations:
        raise HTTPException(status_code=404, detail="No locations available")
    loc = random.choice(locations)
    
    # Check if image is already cached
    image_url = loc.image_url
    image_error = None
    
    # If no image cached or it's a URL (not a file path), try to download and cache
    if not image_url or image_url.startswith("http"):
        print(f"Downloading image for {loc.name}...")
        cached_path = cache_gsv_image(loc.lat, loc.lng)
        if cached_path:
            # Update database with cached path
            loc.image_url = cached_path
            db.commit()
            image_url = cached_path
        else:
            image_error = "Failed to download image"
    
    return RandomLocationResponse(id=loc.id, name=loc.name, lat=loc.lat, lng=loc.lng, image_url=image_url, image_error=image_error)


@app.get("/debug")
def debug_info():
    # Return useful debug information about API key and cache contents
    files = []
    try:
        files = [f for f in os.listdir(CACHE_DIR) if os.path.isfile(os.path.join(CACHE_DIR, f))]
    except Exception as e:
        files = [f"error listing cache: {e}"]
    return {
        "cache_files": files,
    }


@app.post("/submit_guess", response_model=GuessResponse)
def submit_guess(guess: GuessRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # Validate location
    loc = db.query(Location).filter(Location.id == guess.location_id).first()
    if not loc:
        raise HTTPException(status_code=404, detail="Location not found")
    distance = haversine_distance(loc.lat, loc.lng, guess.guess_lat, guess.guess_lng)
    points = compute_points(distance)
    # Update user score and rounds
    current_user.total_score = (current_user.total_score or 0) + points
    current_user.rounds_played = (current_user.rounds_played or 0) + 1
    db.add(current_user)
    db.commit()
    db.refresh(current_user)
    return GuessResponse(distance_meters=distance, points_awarded=points, total_score=current_user.total_score)


@app.get("/leaderboard")
def leaderboard(limit: int = 10, db: Session = Depends(get_db)):
    # Return top users by total_score
    users = db.query(User).order_by(User.total_score.desc()).limit(limit).all()
    return [{"username": u.username, "total_score": u.total_score, "rounds_played": u.rounds_played} for u in users]


# --------------------
# Helper: seed sample locations from CSV if empty
# --------------------
def get_fallback_locations(limit: int = 300) -> list:
    """Return a curated list of well-known locations.
    
    These are real cities and landmarks used as fallback locations.
    """
    fallback = [
        # Europe
        (48.8566, 2.3522, "Paris, France"),
        (51.5074, -0.1278, "London, UK"),
        (52.5200, 13.4050, "Berlin, Germany"),
        (48.2082, 16.3738, "Vienna, Austria"),
        (41.3851, 2.1734, "Barcelona, Spain"),
        (43.7615, 11.2558, "Florence, Italy"),
        (41.9028, 12.4964, "Rome, Italy"),
        (55.7558, 37.6173, "Moscow, Russia"),
        (59.3293, 18.0686, "Stockholm, Sweden"),
        (60.1699, 24.9384, "Helsinki, Finland"),
        # North America
        (40.7128, -74.0060, "New York, USA"),
        (34.0522, -118.2437, "Los Angeles, USA"),
        (41.8781, -87.6298, "Chicago, USA"),
        (29.7604, -95.3698, "Houston, USA"),
        (33.7490, -84.3880, "Atlanta, USA"),
        (49.2827, -123.1207, "Vancouver, Canada"),
        (43.6532, -79.3832, "Toronto, Canada"),
        (45.5017, -122.6750, "Portland, USA"),
        (47.6062, -122.3321, "Seattle, USA"),
        (38.2975, -122.2869, "San Francisco, USA"),
        # Asia
        (35.6762, 139.6503, "Tokyo, Japan"),
        (31.2304, 121.4737, "Shanghai, China"),
        (22.3193, 114.1694, "Hong Kong"),
        (1.3521, 103.8198, "Singapore"),
        (13.7563, 100.5018, "Bangkok, Thailand"),
        (37.5665, 126.9780, "Seoul, South Korea"),
        (28.6139, 77.2090, "Delhi, India"),
        (19.0760, 72.8777, "Mumbai, India"),
        (34.7465, 135.5228, "Osaka, Japan"),
        (22.5431, 88.3660, "Kolkata, India"),
        # South America
        (-33.8688, 151.2093, "Sydney, Australia"),
        (-23.5505, -46.6333, "São Paulo, Brazil"),
        (-22.9068, -43.1729, "Rio de Janeiro, Brazil"),
        (-12.0464, -77.0428, "Lima, Peru"),
        (-34.6037, -58.3816, "Buenos Aires, Argentina"),
        # Africa
        (-33.9249, 18.4241, "Cape Town, South Africa"),
        (-25.2744, 28.2381, "Johannesburg, South Africa"),
        (30.0444, 31.2357, "Cairo, Egypt"),
        (6.4969, 3.3669, "Lagos, Nigeria"),
        (9.0765, 7.3986, "Abuja, Nigeria"),
    ]
    return fallback[:limit]


def seed_locations_if_needed(csv_path: str = None):
    """Populate locations table with 40 well-known locations.

    Images will be downloaded and cached on-demand during gameplay.
    This avoids upfront API charges and stores only images that are used.
    """
    db = SessionLocal()
    try:
        count = db.query(Location).count()
        if count > 0:
            print(f"Locations table already populated with {count} records; skipping seed")
            return
        
        print("Seeding 40 well-known locations...")
        fallback = get_fallback_locations(40)
        
        seeded_count = 0
        for lat, lng, name in fallback:
            # Store location without image - will download on first use
            loc = Location(name=name, lat=lat, lng=lng, image_url=None)
            db.add(loc)
            seeded_count += 1
            print(f"  ✓ {name}")
        
        db.commit()
        print(f"\nSeeded {seeded_count} locations")
        print("Images will be downloaded and cached as they are played")
    except Exception as e:
        print(f"Error seeding locations: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


# Seed on startup with cached images
seed_locations_if_needed()


if __name__ == "__main__":
    print("Run this app with: uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000")
