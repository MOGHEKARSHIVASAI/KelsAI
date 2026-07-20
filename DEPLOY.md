# Deploying KelsAI

KelsAI is designed to be easily deployable in a multi-user environment. It uses a local SQLite database for each user to store their data (jobs, resumes, API keys, etc.) securely.

## Important Note on API Keys

**API keys are now managed entirely per-user via the UI.** 
You do **not** need to set `GEMINI_API_KEY`, `OPENROUTER_API_KEY`, `RAPIDAPI_KEY`, etc., in your server environment variables. Users will log in, navigate to **🔑 API Keys**, and paste their own keys. The app routes keys securely per-session.

---

## Deployment Options

### 1. Streamlit Community Cloud (Recommended & Free)
The easiest way to deploy for personal or small team use.
1. Push your repository to GitHub.
2. Go to [share.streamlit.io](https://share.streamlit.io) and connect your GitHub account.
3. Click "New app", select your KelsAI repository, and set the main file path to `app.py`.
4. Click **Deploy**.

> **Note on Persistence**: Streamlit Cloud can sometimes wipe local files when the container sleeps or restarts. Since KelsAI uses local SQLite files in `database/users/`, data might be lost on restart. For permanent persistence, use Railway or Render with a mounted volume.

### 2. Railway / Render (Persistent Storage)
If you need guaranteed data persistence, use a service like Railway or Render and attach a persistent disk.

**For Railway:**
1. Connect your GitHub repo.
2. Add a Volume and mount it to `/app/database`.
3. Set the start command to: `streamlit run app.py --server.port $PORT --server.address 0.0.0.0`

### 3. Docker (Self-Hosted)
A `Dockerfile` is the best way to self-host KelsAI. 

1. Create a simple `Dockerfile`:
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 8501
CMD ["streamlit", "run", "app.py", "--server.port", "8501", "--server.address", "0.0.0.0"]
```
2. Build and run, mounting the database directory:
```bash
docker build -t kelsai .
docker run -p 8501:8501 -v $(pwd)/database:/app/database kelsai
```

---

## Security
- User databases are stored in `database/users/kelsai_<username>.db`.
- API keys are stored in plain text inside these SQLite files.
- If you are deploying this to the public internet for strangers, you should consider encrypting the database files or using a hosted Postgres/MySQL database instead of SQLite. For personal use or a group of trusted friends, the current setup is perfect.
