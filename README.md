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
| `OPENROUTER_MODEL` | No | Model ID (default: `google/gemma-4-26b-a4b-it`) |
| `DB_USER` | No | PostgreSQL user |
| `DB_PASSWORD` | No | PostgreSQL password |
| `DB_NAME` | No | PostgreSQL database name |
| `MINIO_ROOT_USER` | No | MinIO access key |
| `MINIO_ROOT_PASSWORD` | No | MinIO secret key |
| `MINIO_BUCKET` | No | MinIO bucket name |

When running with Docker, the database and MinIO connection details are pre-configured — you only need to set `OPENROUTER_API_KEY`.

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
| `POST` | `/api/v1/resumes` | Upload and parse a resume |
| `POST` | `/api/v1/interviews` | Create an interview |
| `GET` | `/api/v1/interviews/{id}` | Get interview details |
| `POST` | `/api/v1/interviews/{id}/start` | Start interview session |
| `POST` | `/api/v1/answers/{question_id}` | Submit an answer |
| `GET` | `/api/v1/interviews/{id}/result` | Get final evaluation |
