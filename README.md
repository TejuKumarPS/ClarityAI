# ClarityAI — Meeting Intelligence Platform

ClarityAI is an asynchronous meeting intelligence tool designed as a layered monolith with background task processing. It accepts meeting transcripts via text paste or file upload, extracts structured intelligence using an LLM pipeline, and presents summaries, action items, owners, deadlines, and downloadable PDF reports.

## Architecture

- **Frontend**: React + Vite + Tailwind CSS
- **Backend API**: FastAPI (Python 3.13)
- **Database**: PostgreSQL (SQLAlchemy + Alembic) *(Upcoming in Milestone 1)*
- **Authentication**: JWT + bcrypt *(Upcoming in Milestone 2)*
- **Task Queue**: Celery + Redis *(Upcoming in Milestone 5)*
- **LLM Pipeline**: LangChain + OpenAI *(Upcoming in Milestone 6)*
- **PDF Generation**: ReportLab *(Upcoming in Milestone 8)*

---

## Project Structure

```text
ClarityAI/
├── .env.example
├── .gitignore
├── README.md
├── Documents/
│   └── ClarityAI_Project_Document.docx
├── backend/
│   ├── .venv/               # Python 3.13 virtual environment (gitignored)
│   ├── .env                 # Local backend configuration (gitignored)
│   ├── .env.example         # Committed environment template
│   ├── requirements.txt     # Python dependencies for current milestone
│   ├── app/
│   │   ├── api/
│   │   │   └── v1/
│   │   │       ├── health.py
│   │   │       └── __init__.py
│   │   ├── core/
│   │   │   └── config.py
│   │   └── main.py
│   └── tests/
│       ├── conftest.py
│       └── test_health.py
└── frontend/
    ├── package.json
    ├── vite.config.js
    ├── index.html
    └── src/
        ├── App.jsx
        ├── index.css
        └── main.jsx
```

---

## Local Development Setup

### 1. Backend Setup (Windows PowerShell)

```powershell
# Navigate to backend directory
cd backend

# Create Python 3.13 virtual environment (if not already created)
python -m venv .venv

# Activate virtual environment
.\.venv\Scripts\Activate.ps1

# Install milestone dependencies
pip install -r requirements.txt

# Copy environment variables
Copy-Item .env.example .env

# Run automated tests
pytest tests -v

# Start FastAPI development server
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### 2. Frontend Setup

```powershell
# Navigate to frontend directory
cd frontend

# Install Node dependencies
npm install

# Start Vite development server
npm run dev
```

The frontend will run at `http://localhost:5173` and proxy requests to the backend API at `http://127.0.0.1:8000`.

---

## Milestone Progress

- [x] **Milestone 0: Project Foundation & Environment Setup** (Backend FastAPI + Frontend React/Vite + Health Endpoint + CORS)
- [ ] **Milestone 1: Database Foundation & Schema Migrations** (PostgreSQL + SQLAlchemy + Alembic)
- [ ] **Milestone 2: Authentication & Authorization** (JWT + bcrypt)
- [ ] **Milestone 3: Modular Transcript Input Handlers** (OCP Architecture)
- [ ] **Milestone 4: Transcript Ingestion API** (`POST /jobs`)
- [ ] **Milestone 5: Asynchronous Worker Infrastructure** (Celery + Redis)
- [ ] **Milestone 6: LangChain LLM Meeting Intelligence Pipeline**
- [ ] **Milestone 7: Result Tracking, Polling & Interactive Dashboard**
- [ ] **Milestone 8: Meeting History & PDF Report Export**
- [ ] **Milestone 9: Reliability, Rate Limiting & Resilience**
- [ ] **Milestone 10: Dockerization & Docker Compose**
- [ ] **Milestone 11: Final End-to-End Quality Pass**
