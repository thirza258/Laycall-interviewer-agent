# My Mock Interview — Backend

FastAPI backend for an AI-powered mock interview platform. Handles resume parsing, interview specification building, question generation, and answer evaluation via OpenRouter LLM.

## Tech Stack

- **Framework**: FastAPI
- **Database**: PostgreSQL (async via SQLAlchemy + asyncpg)
- **Migrations**: Alembic
- **Storage**: MinIO (S3-compatible)
- **LLM**: OpenRouter (via OpenAI-compatible SDK)

## Prerequisites

- Python 3.11+
- PostgreSQL (running and accessible)
- MinIO instance (or any S3-compatible storage)
- [OpenRouter](https://openrouter.ai) API key

## Setup

### 1. Clone & enter the project

```bash
cd backend
```

### 2. Create a virtual environment

```bash
python -m venv venv
source venv/bin/activate   # Linux/macOS
venv\Scripts\activate      # Windows
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

Edit the `.env` file at the project root:

```env
DEBUG=True

DB_USER=interview_user
DB_PASSWORD=interview_password
DB_HOST=localhost
DB_PORT=5432
DB_NAME=interview_db

OPENROUTER_API_KEY=sk-or-v1-...
OPENROUTER_MODEL=google/gemma-4-26b-a4b-it

MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=your_access_key
MINIO_SECRET_KEY=your_secret_key
MINIO_BUCKET=interview
MINIO_SECURE=False
MINIO_PUBLIC_URL=http://localhost:9000
```

| Variable | Description |
|---|---|
| `DB_*` | PostgreSQL connection details |
| `DATABASE_URL` | Complete SQLAlchemy URL; replaces the `DB_*` values when set |
| `OPENROUTER_API_KEY` | Your OpenRouter API key |
| `OPENROUTER_MODEL` | Model identifier on OpenRouter — used by every agent |
| `OPENROUTER_TIMEOUT` | Read timeout per LLM call, seconds (default `90`) |
| `OPENROUTER_CONNECT_TIMEOUT` | Connect timeout, seconds (default `10`) |
| `OPENROUTER_MAX_RETRIES` | Retries for transient upstream failures (default `3`) |
| `QUESTION_GENERATION_TIMEOUT` | Ceiling for the full question pipeline, seconds (default `240`) |
| `MINIO_*` | S3-compatible storage credentials and bucket. Unset, the app still starts and uploads fail with "Object storage is not configured" |

### 5. Run database migrations

```bash
alembic upgrade head
```

### 6. Start the server

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The API is now running at `http://localhost:8000`.

### 7. Verify

```bash
curl http://localhost:8000/health
# {"status":"healthy","env":"development"}
```

Interactive docs are available at `http://localhost:8000/docs`.

## Tests

No database, object storage or API key required — SQLite stands in for
PostgreSQL and the OpenRouter and MinIO clients are stubbed:

```bash
pytest                                          # unit + integration
pytest --cov=app --cov=main --cov-report=term    # with coverage
TEST_DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/interview_test pytest
```

`tests/unit` covers each module in isolation, `tests/integration` drives the
endpoints and services against a real (SQLite) session, and
`tests/integration/test_flow_end_to_end.py` runs one interview from resume
upload to final report.

## Project Structure

```
backend/
├── main.py                  # FastAPI app entry point
├── app/
│   ├── api/
│   │   └── endpoints/       # Route handlers (resumes, interviews, answers)
│   ├── agents/              # LLM-powered agents (resume analysis, question gen, etc.)
│   ├── core/
│   │   ├── config.py        # Pydantic settings from .env
│   │   └── minio_client.py  # MinIO singleton client
│   ├── db/
│   │   ├── base.py          # SQLAlchemy declarative base
│   │   ├── session.py       # Async engine & session factory
│   │   └── models/          # ORM models
│   ├── llm/
│   │   ├── client.py        # OpenRouter async client wrapper
│   │   ├── models.py        # LLM request/response Pydantic models
│   │   └── exceptions.py    # LLM-specific exceptions
│   ├── schemas/             # Pydantic request/response schemas
│   ├── services/            # Business logic layer
│   └── storage/             # File storage abstraction
├── alembic/
│   ├── env.py               # Alembic environment config
│   └── versions/            # Migration scripts
└── alembic.ini              # Alembic configuration
```

## API Endpoints

All routes are mounted under `/api/v1`.

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Health check (not versioned) |
| `POST` | `/api/v1/interviews` | Create an interview and store its job description |
| `POST` | `/api/v1/resumes` | Upload a resume, extract its text and generate the questions |
| `GET` | `/api/v1/interviews/{id}/question` | Next question (`?last_question_id=` for the one after it) |
| `POST` | `/api/v1/interviews/{id}/answers` | Submit an answer |
| `POST` | `/api/v1/interviews/{id}/answers/{answer_id}/evaluate` | Score an answer; the last one also writes the final report |
| `GET` | `/api/v1/interviews/{id}/results` | Final report (scores are null until every question is answered) |

Full schema available at `/docs` and `/redoc`.
