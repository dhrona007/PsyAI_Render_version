# PsyAI

PsyAI is an AI-powered mental wellness web app that combines chat, voice support, adaptive assessment, and mood intelligence in one continuous user flow.

## Tech Stack

- Backend: Flask, Flask-CORS, Flask-SocketIO
- Production server: Gunicorn + Eventlet
- AI Provider: Groq API
- Frontend: HTML, Bootstrap 5, vanilla JavaScript
- Charts: Chart.js
- Report generation: jsPDF

## Project Structure

```text
PsyAI_Render_version/
|- app.py
|- index.html
|- README.md
|- FEATURE_USAGE.md
|- requirements.txt
|- Procfile
|- render.yaml
|- runtime.txt
|- static/
|  |- js/app.js
|  |- data/
|  |  |- assessment_questions.json
|  |  |- model_benchmark.json
|  |  |- mood/
```

## Local Setup

1. Create and activate a virtual environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Create a local `.env` file (do not commit it):

```env
GROQ_API_KEY=your_groq_api_key
GROQ_MODEL=llama-3.3-70b-versatile
FLASK_SECRET_KEY=your_secret_key
FLASK_DEBUG=1
```

4. Run the app:

```bash
python app.py
```

Open `http://localhost:5000`.

## GitHub Ready Checklist

- `.env` is already ignored by `.gitignore`.
- Runtime mood JSON files are ignored (`static/data/mood/*.json`).
- A safe template file is included: `.env.example`.
- Render service config is included: `render.yaml`.

## Push to GitHub

```bash
git init
git add .
git commit -m "Prepare PsyAI for GitHub and Render deployment"
git branch -M main
git remote add origin <your-github-repo-url>
git push -u origin main
```

If the repo is already initialized, skip `git init` and only run add/commit/push commands.

## Deploy on Render

### Option A: Blueprint deploy (recommended)

1. In Render, choose **New +** -> **Blueprint**.
2. Connect the GitHub repository.
3. Render reads `render.yaml` and creates the web service.
4. Set required secret values when prompted:
   - `GROQ_API_KEY`
5. Deploy.

### Option B: Manual Web Service

1. In Render, choose **New +** -> **Web Service**.
2. Select this GitHub repo.
3. Configure:
   - Environment: `Python`
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `gunicorn --worker-class eventlet -w 1 --bind 0.0.0.0:$PORT app:app`
4. Add environment variables:
   - `GROQ_API_KEY` (required)
   - `GROQ_MODEL=llama-3.3-70b-versatile` (optional)
   - `FLASK_SECRET_KEY` (required)
   - `FLASK_DEBUG=0`
   - `PYTHON_VERSION=3.11.11`
5. Deploy.

## Main API Endpoints

- `GET /`
- `POST /api/chat`
- `GET /api/assessment_questions?type=general|detailed`
- `POST /api/assessment_analysis`
- `POST /api/mood/log`
- `GET /api/mood/entries`
- `GET /api/mood/stats/overview`
- `GET /api/mood/ai_insights`
- `GET /api/mood/export?format=json|csv`
- `GET /api/model_benchmark`
- `POST /api/emergency_alert`

## Storage Note

Mood logs are file-backed (`static/data/mood/`). On Render, filesystem changes are ephemeral unless you attach a persistent disk and point storage to that path.
