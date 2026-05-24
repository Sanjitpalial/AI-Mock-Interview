# CareerAI Frontend

Each page and component has **its own CSS file** next to its `.jsx` file. No shared `styles/` folder.

## Run

```bash
cd ai-career-platform/frontend
npm install
npm run dev
```

The dev server runs at **http://localhost:5173**. API requests use the **`/api` prefix**, which Vite proxies to the FastAPI backend at **http://127.0.0.1:8000** (see `vite.config.js`). Start the backend from `ai-career-platform/backend` with `uvicorn app.main:app --reload --host 127.0.0.1 --port 8000`.

Optional: set `VITE_API_URL=http://127.0.0.1:8000` in `.env` to talk to the API without the proxy (see `.env.example`).

**Full stack:** Register or log in → upload resume (PDF) on Mock Interview → start interview. Questions and scoring use **Gemini** via the backend; results and history are stored in **PostgreSQL** and shown on **Analytics**.

## Edit styles per file

| JSX | CSS (imported at top of JSX) |
|-----|------------------------------|
| `pages/Home.jsx` | `pages/Home.css` |
| `pages/MockInterview.jsx` | `pages/MockInterview.css` |
| `pages/StudyAssistant.jsx` | `pages/StudyAssistant.css` |
| `pages/Analytics.jsx` | `pages/Analytics.css` |
| `pages/Login.jsx` | `pages/Login.css` |
| `pages/Register.jsx` | `pages/Register.css` |
| `pages/NotFound.jsx` | `pages/NotFound.css` |
| `components/Navbar.jsx` | `components/Navbar.css` |
| `components/Footer.jsx` | `components/Footer.css` |
| `components/Layout.jsx` | `components/Layout.css` |
| `App.jsx` | `App.css` (shell + toasts only) |

Example: change the home page → edit **`src/pages/Home.css`** only.

Each CSS file includes its own colors and buttons for that screen. Navbar/Footer styles are in their component CSS files.
