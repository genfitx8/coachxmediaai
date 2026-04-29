from fastapi import APIRouter

from app.api.v1 import auth, users, projects, media, jobs, payments

router = APIRouter()

router.include_router(auth.router)
router.include_router(users.router)
router.include_router(projects.router)
router.include_router(media.router)
router.include_router(jobs.router)
router.include_router(payments.router)
