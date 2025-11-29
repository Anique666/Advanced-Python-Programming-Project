# Setup Guide for Street Smarts

This guide walks you through setting up the project for local development or sharing with others.

## 1. Get Google Street View API Key

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project (or select existing one)
3. Enable the **Street View Static API**:
   - Search for "Street View Static API" in the search bar
   - Click "Enable"
4. Create an API key:
   - Go to **Credentials** tab
   - Click **Create Credentials** → **API Key**
   - Copy your key
5. **IMPORTANT**: Enable billing on your Google Cloud project
   - Go to **Billing** tab
   - Set up a payment method
   - The free tier covers ~1,000 images/month

## 2. Clone Repository

```bash
git clone https://github.com/Adithya-Git05/Advanced-Python-Programming---Project.git
cd Advanced-Python-Programming---Project
```

## 3. Create Virtual Environment

### Windows (PowerShell)
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### macOS/Linux (Bash)
```bash
python -m venv venv
source venv/bin/activate
```

## 4. Install Dependencies

```bash
pip install -r requirements.txt
```

## 5. Setup Environment Variables

### Option A: Create .env file from template
```bash
cp .env.example .env
```

Then edit `.env` and add your Google API key:
```
GOOGLE_STREETVIEW_KEY=YOUR_API_KEY_HERE
JWT_SECRET=your-secret-key-here
BACKEND_URL=http://localhost:8000
```

### Option B: Set as system environment variables

**Windows PowerShell:**
```powershell
$env:GOOGLE_STREETVIEW_KEY = 'your_api_key_here'
$env:JWT_SECRET = 'your_secret_here'
$env:BACKEND_URL = 'http://localhost:8000'
```

**macOS/Linux Bash:**
```bash
export GOOGLE_STREETVIEW_KEY='your_api_key_here'
export JWT_SECRET='your_secret_here'
export BACKEND_URL='http://localhost:8000'
```

## 6. Run the Application

### Terminal 1: Start Backend
```powershell
# Windows PowerShell
.\venv\Scripts\Activate.ps1
uvicorn backend.main:app --host 0.0.0.0 --port 8000

# macOS/Linux Bash
source venv/bin/activate
uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

You should see:
```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
Seeding 40 locations with cached Google Street View images...
...
Images cached locally - minimal API charges going forward
```

### Terminal 2: Start Frontend
```powershell
# Windows PowerShell
.\venv\Scripts\Activate.ps1
streamlit run frontend/app.py --server.port=8501

# macOS/Linux Bash
source venv/bin/activate
streamlit run frontend/app.py --server.port=8501
```

You should see:
```
  You can now view your Streamlit app in your browser.

  Local URL: http://localhost:8501
  Network URL: http://192.168.x.x:8501
```

## 7. Access the Application

Open your browser and go to: **http://localhost:8501**

- **Backend API Docs**: http://localhost:8000/docs
- **Backend ReDoc**: http://localhost:8000/redoc

## 8. First Run Notes

On the first run, the backend will:
1. Create SQLite database (`backend/app.db`)
2. Download and cache 40 Google Street View images (~$0.007 cost)
3. Seed locations with cached images

Subsequent runs will use cached images (zero API cost).

## Troubleshooting

### "API key not found" error
- Ensure you've created `.env` file or set environment variables
- Check that `GOOGLE_STREETVIEW_KEY` is set correctly
- Verify the key is from Google Cloud Street View Static API

### "Street View Static API is not enabled" error
- Go to Google Cloud Console
- Search for "Street View Static API"
- Click "Enable"

### Port already in use
- Change the port numbers:
  - Backend: `uvicorn backend.main:app --port 8001`
  - Frontend: `streamlit run frontend/app.py --server.port=8502`

### Database locked error
- Stop both services
- Delete `backend/app.db`
- Restart backend (it will re-seed)

### Images not showing
- Verify billing is enabled on Google Cloud project
- Check that API key has Street View Static API enabled
- Ensure cache directory exists: `backend/cache/`

## Next Steps

- Customize the game (see Configuration section in README.md)
- Add more locations by editing `get_fallback_locations()` in `backend/main.py`
- Deploy to cloud (Heroku, AWS, Google Cloud, etc.)
- Share with friends!

## For Sharing with Others

1. **Push to GitHub** (without .env file - use .env.example template)
2. **Provide setup instructions** - share this SETUP.md file
3. **Share your Google Cloud tips** - help them set up API key
4. **Create an issue template** for bug reports

Good luck! 🚀
