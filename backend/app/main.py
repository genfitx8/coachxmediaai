from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from sqlalchemy import text

from app.api.v1.router import router as v1_router
from app.core.middleware import limiter, setup_middleware
from app.database import engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: verify DB connectivity
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception as exc:
        import logging
        logging.getLogger("uvicorn").warning(f"DB health check failed at startup: {exc}")
    yield
    # Shutdown: dispose engine
    await engine.dispose()


app = FastAPI(
    title="CoachX Media AI",
    description="Production-ready FastAPI backend for CoachX Media AI platform",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

setup_middleware(app)

app.include_router(v1_router, prefix="/api/v1")


@app.get("/health", tags=["health"])
async def health_check():
    return JSONResponse({"status": "ok"})
