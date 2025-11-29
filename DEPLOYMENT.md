# Deployment Guide

Instructions for deploying Street Smarts to cloud platforms.

## Heroku (Easiest Option)

### Prerequisites
- Heroku account (free tier available)
- Heroku CLI installed

### Steps

1. **Create Heroku app**
```bash
heroku login
heroku create your-app-name
```

2. **Add buildpacks**
```bash
heroku buildpacks:add heroku/python
```

3. **Set environment variables**
```bash
heroku config:set GOOGLE_STREETVIEW_KEY=your_key_here
heroku config:set JWT_SECRET=your_secret_here
heroku config:set BACKEND_URL=https://your-app-name.herokuapp.com
```

4. **Create Procfile**
```
web: uvicorn backend.main:app --host 0.0.0.0 --port $PORT
```

5. **Deploy**
```bash
git push heroku main
```

6. **Run frontend on Streamlit Cloud**
- Go to [Streamlit Cloud](https://streamlit.io/cloud)
- Connect GitHub repo
- Deploy `frontend/app.py`
- Update `BACKEND_URL` in Streamlit secrets

## Railway (Modern Alternative)

1. Go to [Railway.app](https://railway.app/)
2. New Project → Deploy from GitHub
3. Connect repo
4. Add environment variables
5. Railway auto-detects Python and runs

## Google Cloud Run (Scalable)

1. **Install Google Cloud SDK**
```bash
gcloud auth login
gcloud config set project your-project-id
```

2. **Create app.yaml**
```yaml
runtime: python39
entrypoint: uvicorn backend.main:app --host 0.0.0.0 --port $PORT
env_variables:
  GOOGLE_STREETVIEW_KEY: "your_key_here"
  JWT_SECRET: "your_secret_here"
```

3. **Deploy backend**
```bash
gcloud app deploy
```

4. **Deploy frontend on Streamlit Cloud**
- Update backend URL to your Cloud Run URL

## AWS (Lambda + API Gateway)

More complex setup - use Serverless Framework or Zappa.

```bash
pip install zappa
zappa init
zappa deploy production
```

## Docker Deployment (Any Platform)

### Create Dockerfile
```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Build and run
```bash
docker build -t street-smarts .
docker run -p 8000:8000 -e GOOGLE_STREETVIEW_KEY=your_key street-smarts
```

## Production Checklist

- [ ] Change JWT_SECRET to strong random string
- [ ] Enable HTTPS/SSL
- [ ] Set up database backups
- [ ] Configure CORS appropriately
- [ ] Add rate limiting
- [ ] Monitor API usage and costs
- [ ] Set up logging/error tracking
- [ ] Add domain name
- [ ] Test gameplay thoroughly

## Cost Estimates

| Service | Monthly Cost |
|---------|-------------|
| Google Street View API | ~$0.50-5 (40 images + gameplay) |
| Heroku backend | Free-$7 |
| Streamlit frontend | Free |
| Database (SQLite) | Free |
| **Total** | **~$0-15/month** |

## Monitoring

Add simple monitoring:
```python
# In main.py
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@app.get("/health")
def health_check():
    return {"status": "healthy"}
```

Then set up uptime monitoring at:
- [UptimeRobot](https://uptimerobot.com/) (free)
- [Pingdom](https://www.pingdom.com/)
- [Statuspage.io](https://www.statuspage.io/)

Happy deploying! 🚀
