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
