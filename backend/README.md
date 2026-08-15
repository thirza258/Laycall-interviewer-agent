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

There is no lock file in the repo. Install the required packages manually:

```bash
pip install fastapi uvicorn[standard] sqlalchemy[asyncio] asyncpg alembic pydantic-settings python-dotenv openai minio python-multipart
```

### 4. Configure environment variables

Edit the `.env` file at the project root:

```env
DEBUG=True

DB_USER=interview_user
DB_PASSWORD=interview_password
DB_HOST=100.104.41.9
DB_PORT=5500
DB_NAME=interview_db

OPENROUTER_API_KEY=sk-or-v1-...
OPENROUTER_MODEL=google/gemma-4-26b-a4b-it

MINIO_ENDPOINT=s3.nevatal.tech
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=ubuntuadminpassword
MINIO_BUCKET=interview
MINIO_SECURE=True
MINIO_PUBLIC_URL=https://s3.nevatal.tech
```

| Variable | Description |
|---|---|
| `DB_*` | PostgreSQL connection details |
| `OPENROUTER_API_KEY` | Your OpenRouter API key |
| `OPENROUTER_MODEL` | Model identifier on OpenRouter — used by every agent |
| `OPENROUTER_TIMEOUT` | Read timeout per LLM call, seconds (default `90`) |
| `OPENROUTER_CONNECT_TIMEOUT` | Connect timeout, seconds (default `10`) |
| `OPENROUTER_MAX_RETRIES` | Retries for transient upstream failures (default `3`) |
| `QUESTION_GENERATION_TIMEOUT` | Ceiling for the full question pipeline, seconds (default `240`) |
| `MINIO_*` | S3-compatible storage credentials and bucket |

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

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Health check |
| `POST` | `/resumes/upload` | Upload & parse a resume |
| `POST` | `/interviews` | Create an interview spec |
| `GET` | `/interviews/{id}` | Get interview details |
| `POST` | `/interviews/{id}/start` | Start an interview session |
| `POST` | `/answers/{question_id}` | Submit an answer for evaluation |
| `GET` | `/interviews/{id}/result` | Get final interview result |

Full schema available at `/docs` and `/redoc`.
