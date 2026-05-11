# CoachX Media AI — Backend

Production-ready FastAPI backend for the CoachX Media AI platform.

---

## Overview

This backend provides a RESTful API for uploading, processing, and managing media content using AI. It features JWT-based authentication (with Google OAuth), project-based media management, an async AI job queue via Celery/Redis, S3-compatible storage, and Stripe subscription billing.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Web framework | FastAPI 0.111 |
| ORM | SQLAlchemy 2 (async) |
| Database | PostgreSQL 15 |
| Migrations | Alembic |
| Task queue | Celery 5 + Redis 7 |
| Auth | JWT (python-jose) + Google OAuth (authlib) |
| Storage | AWS S3 / LocalStack / local filesystem |
| Payments | Stripe |
| Rate limiting | SlowAPI |
| Containerisation | Docker + Docker Compose |

---

## Quick Start

### Prerequisites

- Docker & Docker Compose

### 1. Clone and configure

```bash
git clone https://github.com/your-org/coachxmediaai.git
cd coachxmediaai/backend
cp .env.example .env
# Edit .env and fill in your secrets
```

### 2. Start all services

```bash
docker compose up --build
```

The API will be available at **http://localhost:8000**.  
Interactive docs: **http://localhost:8000/docs**

### 3. Run database migrations

```bash
docker compose exec api alembic upgrade head
```

---

## Render Deployment (Backend)

This repository includes a Render blueprint at the repo root: `render.yaml`.

### Render services (monorepo-safe)

- **API Web Service**
  - `rootDir`: `backend`
  - Build command: `pip install -r requirements.txt`
  - Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- **Celery Worker** (optional but recommended for AI job processing)
  - `rootDir`: `backend`
  - Build command: `pip install -r requirements.txt`
  - Start command: `celery -A app.workers.celery_app worker --loglevel=info`

### Required environment variables for Render

| Variable | Required | Notes |
|---|---|---|
| `DATABASE_URL` | Yes | Use async format: `postgresql+asyncpg://...` |
| `REDIS_URL` | Yes | Redis connection string for Celery broker/backend |
| `SECRET_KEY` | Yes | Long random JWT signing secret |
| `CORS_ORIGINS` | Yes | JSON list, e.g. `["https://your-frontend.vercel.app"]` |
| `ADMIN_EMAIL` | Recommended | Auto-creates/promotes admin account on startup |
| `ADMIN_PASSWORD` | Recommended | Password for the bootstrap admin account |
| `ADMIN_FULL_NAME` | Optional | Defaults to `Administrator` |

Other variables from the table below (OAuth, Stripe, S3) are optional unless you use those features.

### First deploy checklist on Render

1. Create/provision PostgreSQL and Redis on Render.
2. Create services from `render.yaml`.
3. Set required environment variables.
4. Run migrations once after initial deploy (from the API service shell):

```bash
alembic upgrade head
```

5. Verify health and docs:
   - `GET /health`
   - `GET /docs`

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://...` | Async PostgreSQL connection string |
| `REDIS_URL` | `redis://redis:6379/0` | Redis connection string (broker + backend) |
| `SECRET_KEY` | `changeme-secret-key` | JWT signing secret — **change in production** |
| `ALGORITHM` | `HS256` | JWT algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | Access token lifetime |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `30` | Refresh token lifetime |
| `GOOGLE_CLIENT_ID` | `` | Google OAuth client ID |
| `GOOGLE_CLIENT_SECRET` | `` | Google OAuth client secret |
| `GOOGLE_REDIRECT_URI` | `http://localhost:8000/...` | Google OAuth redirect URI |
| `AWS_ACCESS_KEY_ID` | `` | AWS key (leave empty for local filesystem) |
| `AWS_SECRET_ACCESS_KEY` | `` | AWS secret |
| `AWS_REGION` | `us-east-1` | AWS region |
| `S3_BUCKET` | `coachxmedia-uploads` | S3 bucket name |
| `S3_ENDPOINT_URL` | `` | Override S3 endpoint (e.g. LocalStack) |
| `STRIPE_SECRET_KEY` | `` | Stripe secret key |
| `STRIPE_WEBHOOK_SECRET` | `` | Stripe webhook signing secret |
| `STRIPE_PRICE_ID_PRO` | `` | Stripe Price ID for the Pro plan |
| `CORS_ORIGINS` | `["http://localhost:3000"]` | Allowed CORS origins (JSON list) |
| `MAX_UPLOAD_SIZE_MB` | `500` | Maximum direct upload size in MB |
| `ADMIN_EMAIL` | `` | E-mail of the auto-created admin account (bootstrap skipped if empty) |
| `ADMIN_PASSWORD` | `` | Password for the auto-created admin account |
| `ADMIN_FULL_NAME` | `Administrator` | Display name for the auto-created admin account |

---

## Admin Account Bootstrap

The API can automatically create an initial administrator account when it starts up.
Set the following variables in `backend/.env` (or as real environment variables in
production) **before** the first run:

```env
ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD=change-me-in-production
ADMIN_FULL_NAME=Administrator   # optional, defaults to "Administrator"
```

**Behavior:**

| Scenario | Result |
|---|---|
| `ADMIN_EMAIL` or `ADMIN_PASSWORD` not set | Bootstrap is skipped silently |
| E-mail does **not** exist in the database | Account is created with `role="admin"`, active, verified |
| E-mail **already exists** with `role="user"` | Role is promoted to `"admin"`; password is **not** changed |
| E-mail already exists with `role="admin"` | No changes (fully idempotent) |

> **Security note:** Use a strong, unique password and change it immediately after
> the first login. For production deployments store `ADMIN_PASSWORD` in a secrets
> manager (e.g. AWS SSM Parameter Store) and never commit it to source control.

Once the account is created, log in with your admin e-mail and password at
`POST /api/v1/auth/login`.

---

## API Endpoints

All routes are prefixed with `/api/v1`.

### Auth
| Method | Path | Description |
|---|---|---|
| POST | `/auth/signup` | Register with email + password |
| POST | `/auth/login` | Login, receive access + refresh tokens |
| POST | `/auth/refresh` | Exchange refresh token for new tokens |
| GET | `/auth/google/login` | Redirect to Google OAuth |
| GET | `/auth/google/callback` | Handle Google OAuth callback |
| POST | `/auth/logout` | Logout (client discards tokens) |

### Users
| Method | Path | Description |
|---|---|---|
| GET | `/users/me` | Get current user profile |
| PATCH | `/users/me` | Update name / avatar |

### Projects
| Method | Path | Description |
|---|---|---|
| POST | `/projects` | Create a project |
| GET | `/projects` | List your projects |
| GET | `/projects/{id}` | Get a project |
| PUT | `/projects/{id}` | Update a project |
| DELETE | `/projects/{id}` | Delete a project |

### Media
| Method | Path | Description |
|---|---|---|
| POST | `/media/upload` | Direct multipart upload |
| POST | `/media/presigned-url` | Get S3 pre-signed PUT URL |
| POST | `/media/confirm-upload` | Confirm pre-signed upload |
| GET | `/media/{id}` | Get media metadata |
| GET | `/projects/{project_id}/media` | List media for a project |
| DELETE | `/media/{id}` | Delete media |

### AI Jobs
| Method | Path | Description |
|---|---|---|
| POST | `/jobs` | Submit an AI job |
| GET | `/jobs` | List your jobs |
| GET | `/jobs/{id}` | Get job status + result |
| DELETE | `/jobs/{id}` | Cancel/delete a job |

### Payments
| Method | Path | Description |
|---|---|---|
| POST | `/payments/create-checkout-session` | Start Stripe checkout |
| GET | `/payments/subscription` | Get subscription status |
| POST | `/payments/webhook` | Stripe webhook receiver |
| POST | `/payments/portal` | Open Stripe billing portal |

---

## Running Tests

```bash
# Install dependencies locally (or use the container)
pip install -r requirements.txt

# Run tests
pytest tests/ -v
```

Tests use an in-memory SQLite database (via aiosqlite) and mock the storage layer so no real AWS or PostgreSQL credentials are needed.

---

## How to Add a New OAuth Provider

1. Register your OAuth app and get `CLIENT_ID` / `CLIENT_SECRET`.
2. Add the new settings to `app/config.py`.
3. Register the provider with authlib in `app/api/v1/auth.py`:

```python
oauth.register(
    name="github",
    client_id=settings.GITHUB_CLIENT_ID,
    client_secret=settings.GITHUB_CLIENT_SECRET,
    access_token_url="https://github.com/login/oauth/access_token",
    authorize_url="https://github.com/login/oauth/authorize",
    client_kwargs={"scope": "user:email"},
)
```

4. Add `/auth/github/login` and `/auth/github/callback` endpoints following the same pattern as Google.

---

## How to Plug In Real AI Models

The stub processor functions live in `app/services/ai_processor.py`. Replace the return values with real API calls:

```python
# Example: OpenAI Whisper transcription
import openai

def transcribe(media_key: str) -> dict:
    # Download file from storage, then call Whisper API
    audio_file = download_from_storage(media_key)
    result = openai.audio.transcriptions.create(model="whisper-1", file=audio_file)
    return {"transcript": result.text, "language": result.language}
```

The `process_ai_job` Celery task in `app/workers/tasks.py` already routes to these functions based on `job_type`—no changes needed there.

---

## Project Structure

```
backend/
├── app/
│   ├── main.py          # FastAPI app factory
│   ├── config.py        # Pydantic settings
│   ├── database.py      # Async SQLAlchemy engine + session
│   ├── models/          # SQLAlchemy ORM models
│   ├── schemas/         # Pydantic request/response schemas
│   ├── api/v1/          # Route handlers
│   ├── core/            # Auth, middleware, dependencies
│   ├── services/        # Storage, AI processor, Stripe
│   └── workers/         # Celery app + tasks
├── alembic/             # Database migrations
├── tests/               # pytest test suite
├── Dockerfile
├── Dockerfile.worker
├── docker-compose.yml
├── requirements.txt
└── .env.example
```
