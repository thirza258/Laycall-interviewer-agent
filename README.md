# My Mock Interview

AI-powered mock interview platform. Upload your resume and a job description — the app generates a tailored interview, asks questions, and evaluates your answers using an LLM.

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 19, Vite 8, Tailwind CSS 4 |
| Backend | FastAPI (Python 3.12), SQLAlchemy (async), Pydantic v2 |
| Database | PostgreSQL 16 |
| Storage | MinIO (S3-compatible) |
| LLM | OpenRouter (OpenAI-compatible SDK) |
| Migrations | Alembic |

## Quick Start (Docker)

The easiest way to run the entire stack. Works on any device with Docker installed.

```bash
# 1. Clone and enter the project
cd Interviewer

# 2. Create your env file
cp .env.example .env

# 3. Set your OpenRouter API key (required)
#    Edit .env → OPENROUTER_API_KEY=your_key_here
#    Get a key at https://openrouter.ai/keys

# 4. Start all services
docker compose up -d

# 5. Verify
curl http://localhost:8000/health
# → {"status":"healthy","env":"production"}
```

The app is now available at **http://localhost:3000** (frontend) and **http://localhost:8000/docs** (API docs).

```bash
# Stop everything
docker compose down

# Stop and wipe all data
docker compose down -v
```

## Local Development

### Backend

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate   # Linux/macOS
venv\Scripts\activate      # Windows

# Install dependencies
pip install -r requirements.txt

# Configure environment (edit values as needed)
cp ../.env.example .env

# Run migrations
alembic upgrade head

# Start dev server
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend

```bash
cd frontend

npm install
npm run dev
# → http://localhost:5173
```

You'll need a running PostgreSQL and MinIO instance (or use `docker compose up db minio minio-init` from the root to run just those).

## Tests

The backend suite needs no database, object storage or API key: SQLite stands
in for PostgreSQL, and the OpenRouter and MinIO clients are stubbed at their
boundaries.

```bash
cd backend
pytest                                          # unit + integration
pytest --cov=app --cov=main --cov-report=term    # with coverage
```

To run the same tests against a real PostgreSQL instance:

```bash
TEST_DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/interview_test pytest
```

Frontend:

```bash
cd frontend
npm install
npm run lint
npm test      # api client unit tests
npm run build
```

## Services

| Service | Port | URL |
|---|---|---|
| Frontend | `3000` | http://localhost:3000 |
| Backend API | `8000` | http://localhost:8000 |
| API Docs (Swagger) | `8000` | http://localhost:8000/docs |
| API Docs (ReDoc) | `8000` | http://localhost:8000/redoc |
| MinIO Console | `9001` | http://localhost:9001 |
| PostgreSQL | `5432` | localhost:5432 |

## Environment Variables

Copy `.env.example` to `.env` and fill in the values:

| Variable | Required | Description |
|---|---|---|
| `OPENROUTER_API_KEY` | **Yes** | API key from [openrouter.ai](https://openrouter.ai) |
| `OPENROUTER_MODEL` | No | Model ID used by every agent (default: `google/gemma-4-26b-a4b-it`) |
| `OPENROUTER_TIMEOUT` | No | Read timeout per LLM call in seconds (default: `90`) |
| `OPENROUTER_CONNECT_TIMEOUT` | No | Connect timeout in seconds (default: `10`) |
| `OPENROUTER_MAX_RETRIES` | No | Retries for transient upstream failures (default: `3`) |
| `QUESTION_GENERATION_TIMEOUT` | No | Ceiling for the full question pipeline in seconds (default: `240`) |
| `DATABASE_URL` | No | Complete SQLAlchemy URL; replaces the `DB_*` values below |
| `DB_USER` | No | PostgreSQL user |
| `DB_PASSWORD` | No | PostgreSQL password |
| `DB_NAME` | No | PostgreSQL database name |
| `MINIO_ROOT_USER` | No | MinIO access key |
| `MINIO_ROOT_PASSWORD` | No | MinIO secret key |
| `MINIO_BUCKET` | No | MinIO bucket name |

When running with Docker, the database and MinIO connection details are pre-configured — you only need to set `OPENROUTER_API_KEY`.

### Troubleshooting: the app "loses" the model

Question generation runs five LLM calls in sequence, and a single call can take
a minute. If an interview will not start, or evaluations come back with
"Could not reach the model", check the backend logs first:

```bash
docker compose logs backend | grep -iE "openrouter|LLM"
```

| What you see | What to do |
|---|---|
| Timed out | Raise `OPENROUTER_TIMEOUT` |
| 429 / rate limit | Retries already back off — wait, or pick a less busy model |
| 401 or 402 | The key is invalid or the account is out of credits. No timeout or retry setting fixes this — replace the key or top up |

If an interview ends up with no questions, asking for the first question retries
the pipeline automatically.

## Project Structure

```
Interviewer/
├── docker-compose.yml        # Docker orchestration
├── .env.example              # Environment template
├── backend/
│   ├── Dockerfile
│   ├── entrypoint.sh         # Migrations + server start
│   ├── requirements.txt
│   ├── main.py               # FastAPI entry point
│   ├── alembic.ini
│   ├── alembic/              # Database migrations
│   └── app/
│       ├── api/endpoints/    # REST route handlers
│       ├── agents/           # LLM agents (resume, questions, evaluation)
│       ├── core/             # Config, MinIO client
│       ├── db/               # SQLAlchemy models & session
│       ├── llm/              # OpenRouter client
│       ├── schemas/          # Pydantic schemas
│       ├── services/         # Business logic
│       └── storage/          # File upload handling
└── frontend/
    ├── Dockerfile
    ├── nginx.conf            # SPA serving + API proxy
    ├── src/                  # React application
    └── public/               # Static assets
```

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Health check |
| `POST` | `/api/v1/interviews` | Create an interview and store its job description |
| `POST` | `/api/v1/resumes` | Upload a resume, extract its text and generate the questions |
| `GET` | `/api/v1/interviews/{id}/question` | Next question (`?last_question_id=` for the one after it) |
| `POST` | `/api/v1/interviews/{id}/answers` | Submit an answer |
| `POST` | `/api/v1/interviews/{id}/answers/{answer_id}/evaluate` | Score an answer; the last one also writes the final report |
| `GET` | `/api/v1/interviews/{id}/results` | Final report (scores are null until every question is answered) |
