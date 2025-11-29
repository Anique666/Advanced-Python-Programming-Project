# Street Smarts: Guess The Location

A FastAPI backend + Streamlit frontend geography guessing game powered by Google Street View. Players are shown Street View images and must click on a map to guess the location. Features JWT authentication, scoring system, and leaderboard.

## Features

- 🎮 **5-round gameplay** with real-time scoring based on distance accuracy
- 📍 **Interactive map** powered by Folium with click-to-guess mechanics
- 🔐 **Secure authentication** with JWT tokens and PBKDF2 hashing
- 🗺️ **Google Street View imagery** with smart on-demand caching
- 🎉 **Confetti animations** on correct guesses
- 💡 **Subtle location hints** - regional clues, not literal city names
- 🏆 **Leaderboard** tracking top players
- 📱 **Responsive design** with light-gray clean UI
- ⚡ **Efficient image caching** - downloads only images that are played

## Tech Stack

- **Backend**: FastAPI, SQLAlchemy ORM, SQLite
- **Frontend**: Streamlit 1.51.0, Folium (interactive maps), streamlit-folium
- **Authentication**: OAuth2 with JWT tokens
- **Hashing**: PBKDF2-SHA256
- **Images**: Google Street View Static API (downloaded on-demand, cached locally)

## Prerequisites

- Python 3.8+
- Google Street View API key (free tier available at [Google Cloud Console](https://console.cloud.google.com/))
  - Note: Requires billing enabled (but free tier covers ~1,000 images/month)

## Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/Adithya-Git05/Advanced-Python-Programming---Project.git
   cd Advanced-Python-Programming---Project
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   .\venv\Scripts\Activate.ps1  # Windows PowerShell
   # or
   source venv/bin/activate     # macOS/Linux
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Setup environment variables**
   ```bash
   cp .env.example .env
   ```
   
   Edit `.env` and add your Google Street View API key:
   ```
   GOOGLE_STREETVIEW_KEY=your_api_key_here
   JWT_SECRET=your_secret_key_here
   BACKEND_URL=http://localhost:8000
   ```

## Running the Application

### Option 1: PowerShell (Windows)
```powershell
# Terminal 1: Backend
.\venv\Scripts\Activate.ps1
uvicorn backend.main:app --host 0.0.0.0 --port 8000

# Terminal 2: Frontend
.\venv\Scripts\Activate.ps1
streamlit run frontend/app.py --server.port=8501
```

### Option 2: Bash (macOS/Linux)
```bash
# Terminal 1: Backend
source venv/bin/activate
uvicorn backend.main:app --host 0.0.0.0 --port 8000

# Terminal 2: Frontend
source venv/bin/activate
streamlit run frontend/app.py --server.port=8501
```

3. **Open in browser**
   - Frontend: http://localhost:8501
   - Backend API docs: http://localhost:8000/docs

## How to Play

1. **Register** with a username and password (min 8 characters)
2. **Login** with your credentials
3. **Start Game** - You'll play 5 rounds
4. **View Street View** image
5. **Click on the map** where you think the location is
6. **Submit your guess** - Get instant feedback on accuracy
7. **Earn points** based on distance from actual location (max 5000 points)
8. **Check leaderboard** to see top players

## Scoring System

Points are calculated using exponential decay based on distance:

$$\text{Points} = 5000 \times e^{-\text{distance\_meters} / 20000}$$

- **Perfect guess (0m)**: 5,000 points
- **100m away**: ~4,757 points
- **1km away**: ~2,313 points
- **10km away**: ~68 points

## Image Caching Strategy

To minimize Google Street View API costs:

- **On-demand caching**: Images are downloaded only when a location is played for the first time
- **Cached storage**: Downloaded images are stored in `backend/cache/` directory for future use
- **Zero subsequent API calls**: Once cached, images are served locally with no additional API charges
- **40 locations available**: 40 well-known cities are available for gameplay

This strategy means you only pay for images that are actually used during gameplay!

## API Endpoints

### Authentication
- `POST /register` - Register new user
- `POST /token` - Login and get JWT token

### Gameplay
- `GET /random_location` - Get random location with cached image
- `POST /submit_guess` - Submit location guess
- `GET /leaderboard` - Get top 10 players

### Debug
- `GET /debug` - View cached images and system info

See full API docs at http://localhost:8000/docs

## Project Structure

```
Advanced-Python-Programming---Project/
├── backend/
│   ├── main.py           # FastAPI app, routes, game logic
│   ├── app.db            # SQLite database (auto-generated)
│   └── cache/            # Cached Google Street View images
├── frontend/
│   └── app.py            # Streamlit UI
├── .env                  # Environment variables (create from .env.example)
├── .env.example          # Template for .env
├── requirements.txt      # Python dependencies
└── README.md            # This file
```

## Database Schema

### Users Table
```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    username VARCHAR UNIQUE NOT NULL,
    hashed_password VARCHAR NOT NULL,
    total_score INTEGER DEFAULT 0,
    rounds_played INTEGER DEFAULT 0
);
```

### Locations Table
```sql
CREATE TABLE locations (
    id INTEGER PRIMARY KEY,
    name VARCHAR NOT NULL,
    lat FLOAT NOT NULL,
    lng FLOAT NOT NULL,
    image_url VARCHAR,
    image_filename VARCHAR
);
```

## Configuration

### Environment Variables
- `GOOGLE_STREETVIEW_KEY` - Your Google API key (required)
- `JWT_SECRET` - Secret for JWT tokens (change in production!)
- `BACKEND_URL` - Backend URL (default: http://localhost:8000)

### Game Settings (in `backend/main.py`)
- `MAX_POINTS` - Maximum points per guess (default: 5000)
- `SCORE_SCALE_METERS` - Distance decay scale (default: 20000m)

## Troubleshooting

### Images not loading
- Verify your Google Street View API key is valid
- Check that billing is enabled on your Google Cloud project
- Ensure cache directory exists: `backend/cache/`

### Database locked error
- Restart both backend and frontend
- Delete `backend/app.db` to force re-seed

### Port already in use
- Change ports in startup commands:
  - Backend: `--port 8000`
  - Frontend: `--server.port 8501`

## Future Enhancements

- [ ] Real Street View image coverage (currently using fixed 40 locations)
- [ ] Multiplayer support with real-time guessing
- [ ] More map layers and satellite view option
- [ ] User profiles and statistics
- [ ] Custom game settings (rounds, difficulty, regions)
- [ ] Mobile responsive design improvements

## Contributing

Feel free to fork, modify, and share! Some ideas:
- Add more locations to seed
- Implement difficulty levels
- Create custom location sets
- Improve UI/UX

## License

MIT License - feel free to use and modify for personal or educational purposes.

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Verify all dependencies are installed: `pip install -r requirements.txt`
3. Ensure Google API key has Street View Static API enabled
4. Check that both backend and frontend are running

---

**Enjoy the game! 🌍**

## Notes & Security

- This project is a demonstration and not secure for production as-is.
- Tokens are created without expiry for simplicity; in production add `exp` claims and token refresh.
- Keep your Google Street View API key and `JWT_SECRET` secure.
- Use environment variables to manage secrets, never hardcode them.

## Next Steps / Improvements

- Add pagination and filtering to leaderboard
- Add per-round timing and better UX for map interactions
- Implement difficulty levels (easy/medium/hard based on regions)
- Add user profiles with gameplay statistics
- Improve mobile responsive design
- Add more location varieties across continents