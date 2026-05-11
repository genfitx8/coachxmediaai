# CoachX Media AI

AI-powered media coaching platform — golf lesson video editor with smart transcription, highlight extraction, and subscription billing.

---

## Repository Structure

```
coachxmediaai/
├── backend/          # FastAPI service (production API)
├── frontend/         # Next.js 16 (App Router) + Tailwind CSS frontend
├── app.py            # Legacy Flask demo (not actively used)
└── templates/        # Legacy Flask templates
```

---

## Quick Start — Local Development

### Prerequisites

- **Docker & Docker Compose** (for the backend)
- **Node.js ≥ 20** + **npm ≥ 10** (for the frontend)

---

### 1. Start the Backend

```bash
cd backend
cp .env.example .env
# Edit .env and fill in your secrets (see backend/README.md)
docker compose up --build
```

The FastAPI service will be available at **http://localhost:8000**.  
Interactive API docs: **http://localhost:8000/docs**

Run database migrations (first time only):

```bash
docker compose exec api alembic upgrade head
```

---

### 2. Start the Frontend

```bash
cd frontend
cp .env.example .env.local
# NEXT_PUBLIC_API_BASE_URL defaults to http://localhost:8000/api/v1
npm install
npm run dev
```

The Next.js development server will start at **http://localhost:3000**.

---

## Environment Variables

### Backend (backend/.env)

See [backend/README.md](backend/README.md) for the full list. Key variables:

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://...` | Async PostgreSQL URL |
| `SECRET_KEY` | `changeme-secret-key` | JWT signing secret |
| `STRIPE_SECRET_KEY` | `` | Stripe secret key |
| `CORS_ORIGINS` | `["http://localhost:3000"]` | Allowed CORS origins |
| `ADMIN_EMAIL` | `` | E-mail of the auto-created admin account |
| `ADMIN_PASSWORD` | `` | Password for the auto-created admin account |

### Frontend (frontend/.env.local)

| Variable | Default | Description |
|---|---|---|
| `NEXT_PUBLIC_API_BASE_URL` | `http://localhost:8000/api/v1` | FastAPI base URL |

---

## Frontend Pages

| Route | Description |
|---|---|
| `/login` | Email + password login |
| `/signup` | New account registration |
| `/projects` | List, create, and delete projects |
| `/projects/[id]` | View and edit a single project |
| `/projects/[id]/media` | Upload and manage media files |
| `/jobs` | Submit AI jobs and poll status |
| `/billing` | Stripe checkout and billing portal |

---

## Backend API

All routes are prefixed with `/api/v1`. See [backend/README.md](backend/README.md) for the full endpoint reference.

---

## Vercel Deployment (Frontend Only)

This repository is a hybrid app. Only the **Next.js frontend** (`frontend/`) should run on Vercel.  
The FastAPI backend requires PostgreSQL, Redis, and Celery workers, so it must be hosted separately.

### Correct Vercel setup for this repo

1. Import this GitHub repository into Vercel.
2. In **Project Settings → General**, set **Root Directory** to `frontend`.
3. Keep Framework Preset as **Next.js**.
4. Add `NEXT_PUBLIC_API_BASE_URL=https://api.your-domain.com/api/v1` in Vercel environment variables.
5. Deploy.

> Note: For this monorepo structure, setting the Vercel Root Directory to `frontend` is required. A root-level `vercel.json` that builds via `cd frontend` is not the recommended setup.

---

## Administrator Account

To bootstrap an initial admin account, add the following to `backend/.env`:

```env
ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD=change-me-in-production
```

The API will create (or promote) this account automatically on the next startup.
Log in with the same credentials at `POST /api/v1/auth/login`.

See [backend/README.md](backend/README.md#admin-account-bootstrap) for full details.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 16 (App Router), TypeScript, Tailwind CSS |
| Backend | FastAPI, SQLAlchemy (async), PostgreSQL |
| Auth | JWT (access + refresh tokens) |
| Storage | AWS S3 / LocalStack / local filesystem |
| Payments | Stripe |
| Task Queue | Celery + Redis |

---

## Legacy Demo

The `app.py` file at the repo root is a **Flask demo** for the original golf-video comparison tool. It is not connected to the FastAPI backend. Run it separately if needed:

```bash
pip install -r requirements.txt
python app.py
# Available at http://localhost:5000
```
