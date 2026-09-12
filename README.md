# ClarityAI — Asynchronous Meeting Intelligence Platform

[![Backend Tests](https://img.shields.io/badge/pytest-241%20passed-emerald)](backend/tests)
[![Architecture](https://img.shields.io/badge/architecture-layered%20monolith-blue)](backend/app)
[![Pipeline](https://img.shields.io/badge/processing%20pipeline-5--stage%20deterministic-purple)](backend/app/processing)
[![Docker](https://img.shields.io/badge/docker-compose%20v2-orange)](docker-compose.yml)

**ClarityAI** is a production-grade, asynchronous meeting intelligence and transcript processing platform built with a layered monolith architecture. It ingests meeting transcripts (raw text paste, `.txt`, or `.pdf`), processes them through a deterministic 5-stage pipeline, grounds context using keyword retrieval, and extracts structured intelligence (executive summary, key takeaways, decisions with rationale, action items with owners, risk severity ratings, open questions, and sentiment analysis) via a single structured LLM call.

---

## 📑 Table of Contents

1. [Architecture Overview](#-architecture-overview)
2. [Processing Pipeline](#-processing-pipeline)
3. [Technology Stack](#-technology-stack)
4. [Key Engineering Highlights](#-key-engineering-highlights)
5. [API Specification](#-api-specification)
6. [Local Development Setup](#-local-development-setup)
7. [Docker Development Environment](#-docker-development-environment)
8. [Automated Testing & Verification](#-automated-testing--verification)

---

## 🏛 Architecture Overview

ClarityAI adheres to strict separation of concerns across presentation, API, domain processing, background workers, and persistent storage:

```text
Browser (React 19 + Tailwind CSS)
   │
   ├── /login & /register (JWT Auth)
   ├── /jobs (Dashboard & Paginated History)
   └── /jobs/:jobId (Live Status Polling & Structured Results)
         │
         ▼
FastAPI Application Gateway (Port 8000)
   ├── Auth Controller (/api/v1/auth/*)
   ├── Jobs Controller (/api/v1/jobs/*)
   └── Health Controller (/health, /api/v1/health)
         │
   ┌─────┴───────────────────────────────┐
   ▼                                     ▼
PostgreSQL 16 Database            Redis 7 Broker & Result Backend
- users (email, bcrypt hash)             │
- jobs (metadata, status, jsonb)         ▼
- composite index (user_id, created_at, id)   Celery Asynchronous Worker
                                         │
                                         ▼
                                   ProcessingPipeline
                                   (5 Deterministic Stages)
```

---

## ⚙️ Processing Pipeline

The core document processing engine operates on an extensible Open-Closed (OCP) pipeline:

```text
Input Transcript (Text / .txt / .pdf)
               │
               ▼
   [ Stage 1: NormalizeStage ]  ──> Sanitizes whitespace, unifies line endings, strips non-printable chars
               │
               ▼
   [ Stage 2: AnalyzeStage ]    ──> Calculates deterministic character, word, and line metrics
               │
               ▼
   [ Stage 3: ChunkStage ]      ──> Splits document into character-bounded chunks with sliding overlap
               │
               ▼
   [ Stage 4: RetrievalStage ]  ──> Scores & ranks chunks via tokenized keyword retrieval for grounded context
               │
               ▼
   [ Stage 5: AIAnalysisStage ] ──> Invokes LLM provider (OpenAI Structured Outputs / FakeLLM)
               │
               ▼
      ProcessingResult v0.6.0
      ├── Executive Summary
      ├── Key Points
      ├── Decisions (decision + rationale)
      ├── Action Items (task + owner)
      ├── Risks (description + severity rating)
      ├── Open Questions (question + owner)
      └── Sentiment (positive, neutral, negative, mixed)
```

> **Strict Pipeline Invariant:** Exactly **ONE** LLM call is executed per job to maintain cost efficiency, deterministic latency, and predictable reliability.

---

## 🛠 Technology Stack

| Layer | Technology | Description |
| :--- | :--- | :--- |
| **Frontend** | React 19, Vite, Tailwind CSS v4 | SPA with client routing, JWT persistence, live polling, and rich intelligence cards |
| **Backend Framework** | FastAPI, Python 3.13, Pydantic v2 | High-performance asynchronous REST API with automatic schema validation |
| **Database & ORM** | PostgreSQL 16, SQLAlchemy 2.0, Alembic | Relational storage with JSONB intelligence results and composite indexing |
| **Task Queue & Broker** | Celery 5.4, Redis 7 Alpine | Asynchronous background job processing with task retry and error classification |
| **LLM Integration** | OpenAI Python SDK (`gpt-4o-mini`), FakeLLM | Structured output parsing with strict Pydantic models and complete unit isolation |
| **Containerization** | Docker, Docker Compose v2 | Multi-container stack with automated healthchecks and dependency chaining |
| **Testing** | Pytest, HTTPX, AnyIO | 226 unit and integration tests covering auth, DB, jobs, LLM, worker, and pipeline |

---

## 🌟 Key Engineering Highlights

- **Single-Call Structured LLM Intelligence:** Leverages OpenAI Structured Outputs (`client.beta.chat.completions.parse`) with strict Pydantic schemas, eliminating json-parsing hallucination errors.
- **Resilient Error Classification:** Classifies upstream LLM errors into typed domain exceptions (`LLMConfigurationError`, `LLMInputTooLargeError`, `LLMResponseValidationError`, `LLMProviderError`) without leaking API keys or internal stack traces.
- **SQL-Level Deterministic Pagination:** Implements `GET /api/v1/jobs` with `created_at DESC, id DESC` stable tiebreaker ordering supported by a composite index `ix_jobs_user_id_created_at_id`.
- **Zero-Dependency Frontend Polling:** Features a custom `useJobPolling` hook that queries the backend status every 2 seconds during `pending`/`processing` states and halts automatically on terminal states.
- **Strict User Ownership Isolation:** All queries, job retrievals, and list endpoints enforce tenant isolation at the SQL layer (`WHERE user_id = current_user.id`).
- **Comprehensive Test Suite:** 241 tests with 100% pass rate, including mock LLM isolation, database constraints, Celery task retries, PDF generation, per-user rate limiting, and API boundaries.

---

## 📡 API Specification

### Authentication Endpoints
- `POST /api/v1/auth/register`: Create user account with email and password (`min 8 characters`).
- `POST /api/v1/auth/login`: Authenticate credentials and return JWT access token.
- `GET /api/v1/auth/me`: Retrieve current authenticated user profile.

### Jobs Endpoints
- `POST /api/v1/jobs`: Ingest transcript content (`text_paste`, `.txt`, `.pdf`) and enqueue Celery task. Rate-limited per authenticated user (`20/hour` default).
- `GET /api/v1/jobs?page=1&page_size=20`: Retrieve paginated job history for authenticated user.
- `GET /api/v1/jobs/{job_id}`: Retrieve detailed status, structured intelligence result, and operational metadata.
- `DELETE /api/v1/jobs/{job_id}`: Delete a job owned by the authenticated user (`204 No Content`).
- `GET /api/v1/jobs/{job_id}/download`: Export a complete job's structured intelligence result as a formatted PDF document. Returns `409 Conflict` if the job is not complete.

### System Endpoints
- `GET /health`: Basic service healthcheck.
- `GET /api/v1/health`: API subsystem status.

---

## 🚀 Local Development Setup

### Prerequisites
- Python 3.13+
- Node.js 22+
- PostgreSQL 16 & Redis 7 (or running via Docker)

### 1. Backend Setup
```powershell
# Navigate to backend
cd backend

# Create & activate virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Configure environment
Copy-Item .env.example .env

# Run database migrations
alembic upgrade head

# Run tests
pytest -v

# Start FastAPI server
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### 2. Celery Worker Setup
```powershell
# In a new terminal with backend .venv active
cd backend
celery -A app.worker.celery_app worker --loglevel=info
```

### 3. Frontend Setup
```powershell
# Navigate to frontend
cd frontend

# Install dependencies
npm install

# Start Vite dev server
npm run dev
```

---

## 🐳 Docker Development Environment

Run the entire ClarityAI platform with a single command:

```powershell
# Start all 5 containerized services
docker compose up -d

# Verify service health
docker compose ps

# Run database migrations inside container
docker compose exec backend alembic upgrade head

# View real-time logs
docker compose logs -f
```

### Service Mapping
- **Frontend Dashboard:** `http://localhost:5173`
- **Backend API:** `http://localhost:8000`
- **API Documentation (Swagger):** `http://localhost:8000/docs`
- **PostgreSQL:** `localhost:5432`
- **Redis:** `localhost:6379`

---

## 🧪 Automated Testing & Verification

Run the full backend test suite:
```powershell
pytest -v
```

Run frontend production bundle validation:
```powershell
cd frontend
npm run build
```
