# AI Career Platform — Backend

FastAPI app with PostgreSQL, JWT auth, resume upload (PDF + Gemini analysis), and a LangGraph-powered mock interview (Gemini) with persisted scores.

## Setup

1. Copy `.env.example` to `.env` and set at least:
   - `DATABASE_URL` — PostgreSQL connection string
   - `SECRET_KEY` — long random string for JWT signing (change the dev default in production)
   - `GOOGLE_API_KEY` — [Google AI Studio](https://aistudio.google.com/apikey) key for Gemini (Mock Interview)
   - `GROQ_API_KEY` — [Groq Console](https://console.groq.com/keys) key for Study Assistant (RAG + roadmaps)

2. Create a virtual environment and install dependencies:

```powershell
cd ai-career-platform/backend
python -m venv venv
.\venv\Scripts\pip install -r requirements.txt
```

3. Run the API (from this folder):

```powershell
.\venv\Scripts\uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Open http://127.0.0.1:8000/docs for interactive API docs.

## Frontend

Run the Vite app from `../frontend` (`npm run dev`). It proxies `/api` to this server on port 8000.

## Main routes

| Prefix | Purpose |
|--------|---------|
| `/auth/register`, `/auth/login` | Users + JWT |
| `/resume/upload` | PDF → text + Gemini summary + DB + optional Chroma embedding |
| `/interview/start`, `/interview/answer`, `/interview/next` | Mock interview workflow |
| `/interview/history`, `/interview/dashboard` | Analytics data for the signed-in user |
| `/study/upload-pdf`, `/study/ask`, `/study/roadmap` | Study Assistant (Groq + Chroma RAG) |
