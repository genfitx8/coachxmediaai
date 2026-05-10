# CoachX Media AI — Developer Makefile
# Run `make help` to see available targets.

.PHONY: help backend-up backend-down backend-migrate backend-test \
        frontend-install frontend-dev frontend-build lint-backend

help:
	@echo ""
	@echo "CoachX Media AI — available make targets"
	@echo ""
	@echo "  make backend-up        Start all backend services (API, DB, Redis, Celery)"
	@echo "  make backend-down      Stop and remove backend containers"
	@echo "  make backend-migrate   Run Alembic migrations (requires running DB)"
	@echo "  make backend-test      Run the backend pytest suite"
	@echo "  make frontend-install  Install frontend npm dependencies"
	@echo "  make frontend-dev      Start the Next.js development server"
	@echo "  make frontend-build    Build the Next.js production bundle"
	@echo ""

# ── Backend ────────────────────────────────────────────────────────────────

backend-up:
	cd backend && docker compose up --build -d

backend-down:
	cd backend && docker compose down

backend-migrate:
	cd backend && docker compose exec api alembic upgrade head

backend-test:
	cd backend && pip install -r requirements.txt -q && pytest tests/ -v

# ── Frontend ───────────────────────────────────────────────────────────────

frontend-install:
	cd frontend && npm install

frontend-dev:
	cd frontend && npm run dev

frontend-build:
	cd frontend && npm run build
