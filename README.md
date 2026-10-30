# My Mock Interview

AI-powered mock interview platform. Upload your resume and a job description — the app generates a tailored interview, asks questions, and evaluates your answers using an LLM.

**HR interview mode** reverses the roles: you interview a fictional AI candidate. Open **HR interview mode** in the sidebar or visit `/app/#/hr`. Set a candidate name, target role, junior/mid/senior experience level, 1–12 skills, and an optional background. Role presets provide editable starting points. No resume or object storage is needed for this mode.

Ask your own questions, use the skill-based question starters, and follow up on the candidate’s answers. The candidate keeps their profile and conversation context. **Finish & get feedback** reviews your interviewing technique, question quality, follow-ups, and coverage of the selected skills. Sessions allow up to 30 questions; feedback is about the interviewer, not a hiring assessment of the fictional candidate.

HR profiles, conversations and feedback are saved in the database. Recent session shortcuts are stored in this browser under `laycall.hr.sessions.v1`; drafts stay in the current tab’s session storage. Reopen a session from **Recent HR interviews** or its `/app/#/hr/{uuid}` URL. There is no account or ownership layer: anyone with a session URL can access it, so use fictional practice profiles. If a model call fails, retry the question or feedback; question retries reuse the same request ID to avoid duplicate turns. Existing installations must run `cd backend && alembic upgrade head` to add the HR sessions table. The backend and OpenRouter configuration below are required for AI responses.

The interview academy adds **30 courses, 90 lessons and 180 guided practice questions** covering foundations, behavioral answers, interview formats, technical interviews, role-specific preparation and career moves. Each lesson includes an explanation, actionable steps, an illustrative example and an exercise.

Open **Courses & guides** in the app sidebar or visit `/app/#/courses`. Search the library, save courses, complete lessons, and practice common questions at `/app/#/questions`. Course and lesson links can be shared directly. The library requires no resume upload, API key or running backend; it is bundled with the frontend and loaded when opened. Mock interviews still require the backend and LLM configuration below.

Learning progress, bookmarks and notes are stored in this browser under `laycall.learning.v1`; they do not sync between devices and clearing browser storage removes them. Practice answers in the course library are self-guided and are not sent for AI scoring. The mock interview list remains in memory and resets on reload.

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

The default compose file reuses the MinIO that the **decalove** project already
runs (`decalove-minio` on the `decalove_default` network), so that stack must be
up first. Set `DECALOVE_NETWORK` and `MINIO_ENDPOINT` in `.env` if the project or
service names differ.

```bash
# 0. Start decalove's MinIO if it is not already running
(cd ../decalove/api && docker compose up -d minio)

# 1. Clone and enter the project
cd Interviewer

# 2. Create your env file
cp .env.example .env

# 3. Set your OpenRouter API key (required) and MinIO credentials
#    Edit .env → OPENROUTER_API_KEY=your_key_here
#    Get a key at https://openrouter.ai/keys

# 4. Start all services
docker compose up -d

# 5. Verify
curl http://localhost:8000/health
# → {"status":"healthy","env":"production"}
```

No decalove deployment available? `docker-compose.full.yml` is the same stack
with its own PostgreSQL and MinIO, and needs nothing else on the host:

```bash
docker compose -f docker-compose.full.yml up -d
```

Run one stack or the other, not both — they publish the same host ports.

The app is now available at **http://localhost:3000** (landing page), **http://localhost:3000/app/** (the interview itself) and **http://localhost:8000/docs** (API docs).

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
# → http://localhost:5173      landing page
# → http://localhost:5173/app/  the interview app
```

You'll need a running PostgreSQL and a MinIO instance (the default compose file
points at decalove's, or run the self-contained set with `docker compose -f
docker-compose.full.yml up -d db minio minio-init`).

## Tests

The backend suite needs no database, object storage or API key: SQLite stands
in for PostgreSQL, and the OpenRouter and MinIO clients are stubbed at their
boundaries.

```bash
cd backend
pytest              # unit + integration tests
pytest --cov        # with coverage; settings live in .coveragerc
```

`.coveragerc` names `app` and `main` as the measured source and fails the run
below **90%** coverage. The suite currently sits at **99%**, so the floor
catches a real regression without failing the build over a refactor.

Nothing is excluded from measurement. Two statements are simply never reached,
and are left visible in the report rather than hidden behind an exclusion — so
the report shows 2 missed statements on purpose, and a third is a real gap:

| Line | Why |
|---|---|
| `app/llm/client.py:115` | The retry loop returns or raises before reaching it; the source says so too. |
| `app/agents/utils.py:36` | Reads a Pydantic field alias, and no agent schema declares one. Kept because it is what would make an alias work the day one is added. |

Tests are split by what they touch:

| Directory | What runs |
|---|---|
| `tests/unit/` | One module at a time, with its collaborators stubbed. |
| `tests/integration/` | Endpoints and services against a real SQLite schema, with only the LLM and object storage stubbed. |

Fixtures live in `tests/conftest.py`: a per-test schema, an async HTTP client
with `get_db` and the LLM client overridden, and one fake LLM payload that
satisfies every agent schema at once.

To run the same tests against a real PostgreSQL instance:

```bash
TEST_DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/interview_test pytest
```

Frontend:

```bash
cd frontend
npm install
npm run lint
npm test      # API client and interview UI regression tests
npm run build
```

## Services

| Service | Port | URL |
|---|---|---|
| Landing page | `3000` | http://localhost:3000 |
| Interview app | `3000` | http://localhost:3000/app/ |
| Backend API | `8000` | http://localhost:8000 |
| API Docs (Swagger) | `8000` | http://localhost:8000/docs |
| API Docs (ReDoc) | `8000` | http://localhost:8000/redoc |
| MinIO Console (decalove) | `4531` | http://localhost:4531 |
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
| `MINIO_ACCESS_KEY` | No | Credentials for the decalove MinIO server |
| `MINIO_SECRET_KEY` | No | Credentials for the decalove MinIO server |
| `MINIO_BUCKET` | No | Bucket created inside that server (default: `interview`) |
| `DECALOVE_NETWORK` | No | Compose network decalove runs on (default: `decalove_default`) |
| `MINIO_PUBLIC_URL` | No | Browser-facing base URL for resume links (default: `http://localhost:4530`) |

When running with Docker, the database and MinIO connection details are pre-configured — you only need to set `OPENROUTER_API_KEY`. `docker-compose.full.yml` (the self-contained stack) reads `MINIO_ROOT_USER` / `MINIO_ROOT_PASSWORD` for its own MinIO instead.

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

The interview keeps its conversation and question position when switching
sessions in the sidebar. After an evaluation fails, use **Retry Evaluation**
to score the saved answer. **Retry Results** retries a missing final report.
Reports are generated only after the latest answer to every question has an
evaluation. Resume uploads require readable text; DOCX tables are supported.

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
    ├── nginx.conf            # Route split, SPA serving + API proxy
    ├── index.html            # Landing page (static, no JavaScript)
    ├── app/index.html        # React app entry, served at /app/
    ├── src/                  # React application
    └── public/               # Copied to the site root as-is
        ├── robots.txt        # Allows /, disallows /app/
        ├── sitemap.xml       # Sitemap containing 35 indexable URLs (landing, sections & 30 courses)
        └── og.png            # 1200x630 social preview
```

## Pages and SEO

The site serves static landing content alongside crawlable React SPA pages:

| Route | What it is | Indexed |
|---|---|---|
| `/` | Landing page. Plain HTML, inlined CSS, no JavaScript, so the copy is in the bytes a crawler receives. | Yes |
| `/courses`, `/courses/{id}` | Interview courses and guides in the React SPA. | Yes |
| `/questions` | Question bank in the React SPA. | Yes |
| `/hr` | HR interview practice in the React SPA. | Yes |
| `/app/` | Mock interview app shell. | Yes |
| `/api/` | Backend REST endpoints. | No — `robots.txt` disallows it |

Every absolute URL is written out as a literal — crawlers and social scrapers
need them absolute — so moving the site off `interview.nevatal.id` is a
find-and-replace over three files:

- `frontend/index.html` — the canonical link, `og:url`, `og:image`,
  `twitter:image`, the JSON-LD `url`, and the domain shown in the footer
- `frontend/public/robots.txt` — the `Sitemap:` line
- `frontend/public/sitemap.xml` — the `<loc>` tags

Renaming the product is the same kind of edit: "My Mock Interview" appears nine
times in `frontend/index.html` (title, the Open Graph and Twitter tags, the
JSON-LD `name`, the header wordmark, the footer) and nowhere else on the
landing page.

When page content changes, bump `<lastmod>` in `sitemap.xml` and resubmit
it in Google Search Console.

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
| `POST` | `/api/v1/hr-interviews` | Create a fictional candidate session from a profile |
| `GET` | `/api/v1/hr-interviews/{uuid}` | Restore an HR conversation and any feedback |
| `POST` | `/api/v1/hr-interviews/{uuid}/questions` | Ask the candidate a question with conversation context |
| `POST` | `/api/v1/hr-interviews/{uuid}/finish` | Complete the session and coach the interviewer |
