# ClarityAI — Permanent Architectural Project State Reference

**Current Project State:** Complete (Milestone 17 FINAL)  
**Architecture Pattern:** Layered Monolith with Background Worker Execution & Single-LLM-Call Invariant  
**Testing Status:** 226/226 Pytest Tests Passing (100%), Production Frontend Build Passing (100%), Docker Compose Healthy (100%)

---

## 1. System Architecture

```text
                                  ┌─────────────────────────────┐
                                  │   React 19 / Tailwind SPA   │
                                  │      (Port 5173 / Vite)     │
                                  └──────────────┬──────────────┘
                                                 │ HTTP / JSON (JWT)
                                                 ▼
                                  ┌─────────────────────────────┐
                                  │    FastAPI API Gateway      │
                                  │        (Port 8000)          │
                                  └──────┬───────────────┬──────┘
                                         │               │
                    SQLAlchemy 2.0 / DDL │               │ Enqueue Task
                                         ▼               ▼
                        ┌───────────────────┐    ┌─────────────────┐
                        │   PostgreSQL 16   │    │  Redis 7 Broker │
                        │  (clarityai_dev)  │    └────────┬────────┘
                        └───────────────────┘             │
                                                          │ Worker Pull
                                                          ▼
                                                 ┌─────────────────┐
                                                 │  Celery Worker  │
                                                 │ (Pipeline Exec) │
                                                 └─────────────────┘
```

---

## 2. Processing Pipeline Specification

The processing pipeline implements an Open-Closed Principle (OCP) architecture where stages execute sequentially on a shared `ProcessingContext`:

1. **`NormalizeStage`:** Sanitizes whitespace, normalizes line endings (`\r\n` -> `\n`), strips non-printable control characters.
2. **`AnalyzeStage`:** Computes document statistics (`character_count`, `word_count`, `line_count`).
3. **`ChunkStage`:** Partitions transcript into overlapping character chunks (`chunk_size_chars: 4000`, `chunk_overlap_chars: 400`).
4. **`RetrievalStage`:** Tokenizes keywords, scores and ranks chunks, constructing grounded context for the LLM.
5. **`AIAnalysisStage`:** Dispatches grounded context to the configured `LLMProvider` (OpenAI or FakeLLM).

**Strict Pipeline Invariant:** Exactly **ONE** LLM call per job.

---

## 3. Database Schema & Indexing

### `users` Table
- `id` (UUID, Primary Key, default `uuid4`)
- `email` (String, Unique, Index)
- `password_hash` (String)
- `created_at` (DateTime, UTC)

### `jobs` Table
- `id` (UUID, Primary Key, default `uuid4`)
- `user_id` (UUID, ForeignKey `users.id`, Index)
- `input_type` (String: `text_paste`, `txt_file`, `pdf_file`)
- `raw_transcript` (Text, Privacy-Protected)
- `status` (String: `pending`, `processing`, `complete`, `failed`)
- `result` (JSONB: stores `ProcessingResult` payload)
- `retry_count` (Integer, default 0)
- `created_at` (DateTime, UTC)
- `processing_started_at` (DateTime, UTC, nullable)
- `processing_duration_ms` (Integer, nullable)
- `llm_provider` (String, nullable)
- `llm_model` (String, nullable)
- `llm_input_tokens` (Integer, nullable)
- `llm_output_tokens` (Integer, nullable)
- `llm_total_tokens` (Integer, nullable)
- `error_code` (String, nullable)
- `completed_at` (DateTime, UTC, nullable)

### Indexes
- `ix_users_email` on `users(email)`
- `ix_jobs_user_id` on `jobs(user_id)`
- `ix_jobs_user_id_created_at_id` on `jobs(user_id, created_at, id)` *(Composite index for deterministic pagination)*

### Alembic Migration History
1. `b57f49cc814f`: Initial `users` and `jobs` tables with foreign keys and indexes.
2. `a959a0f88633`: Job observability fields (`llm_provider`, `llm_model`, `processing_duration_ms`, `error_code`, etc.).
3. `c748a1ef902b`: Composite index `ix_jobs_user_id_created_at_id` on `jobs(user_id, created_at, id)`.

---

## 4. API Endpoints

- `POST /api/v1/auth/register` — Register user with email and password
- `POST /api/v1/auth/login` — Login with credentials, returns JWT
- `GET /api/v1/auth/me` — Retrieve current authenticated user
- `POST /api/v1/jobs` — Create and enqueue transcript processing job
- `GET /api/v1/jobs` — Paginated job history (`page`, `page_size`, total metadata, deterministic ordering)
- `GET /api/v1/jobs/{job_id}` — Inspect individual job status, operational metadata, and AI intelligence result
- `GET /health` & `GET /api/v1/health` — Application healthchecks

---

## 5. Structured Meeting Intelligence Output Schema

```json
{
  "processor": "clarityai-pipeline",
  "version": "0.6.0",
  "job_id": "<uuid>",
  "metadata": {
    "character_count": 1450,
    "word_count": 230,
    "line_count": 18
  },
  "chunking_metadata": {
    "chunk_count": 1,
    "chunk_size_chars": 4000,
    "chunk_overlap_chars": 400
  },
  "retrieval_metadata": {
    "retrieval_strategy": "keyword",
    "retrieved_count": 1,
    "query": "meeting decisions action items risks questions"
  },
  "ai_analysis": {
    "summary": "Executive summary of the transcript...",
    "key_points": ["Point 1", "Point 2"],
    "decisions": [
      { "decision": "Decision title", "rationale": "Decision rationale" }
    ],
    "action_items": [
      { "task": "Task description", "owner": "Assignee name" }
    ],
    "risks": [
      { "description": "Risk description", "severity": "low | medium | high" }
    ],
    "open_questions": [
      { "question": "Unresolved question", "owner": "Person responsible" }
    ],
    "sentiment": "positive | neutral | negative | mixed"
  },
  "llm_usage": {
    "input_tokens": 320,
    "output_tokens": 140,
    "total_tokens": 460
  },
  "llm_provider": "openai",
  "llm_model": "gpt-4o-mini"
}
```

---

## 6. Testing & Quality Invariants

- **Total Tests:** 226 unit and integration tests across 11 test modules.
- **Pass Rate:** 100% (0 failures, 0 warnings).
- **Execution Time:** ~28.5 seconds.
- **Privacy Assurance:** Raw transcripts, password hashes, and backend connection strings are never exposed in list or detail API responses.
- **Safe Error Handling:** Domain exceptions map to standard error codes (`LLM_CONFIGURATION_ERROR`, `LLM_INPUT_TOO_LARGE`, `LLM_RESPONSE_INVALID`, `LLM_PROVIDER_ERROR`) without leaking stack traces or secrets.
- **Docker Compose:** All 5 services (`backend`, `frontend`, `postgres`, `redis`, `worker`) start cleanly with automated healthchecks and dependency coordination.
