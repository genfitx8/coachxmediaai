from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.config import settings

limiter = Limiter(key_func=get_remote_address, default_limits=["100/minute"])


def setup_middleware(app: FastAPI) -> None:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
