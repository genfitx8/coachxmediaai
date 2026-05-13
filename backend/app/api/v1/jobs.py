import asyncio
import os
import tempfile
import uuid

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    HTTPException,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_active_user
from app.database import get_db
from app.models.job import AIJob
from app.models.user import User
from app.schemas.job import JobCreate, JobRead

router = APIRouter(prefix="/jobs", tags=["jobs"])

# Cap input size for the synchronous comparison endpoint to keep us within
# the Render free plan's 100s request budget and 512 MB RAM ceiling.
MAX_COMPARISON_UPLOAD_BYTES = 50 * 1024 * 1024  # 50 MB per file
ALLOWED_VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v"}

VALID_JOB_TYPES = {"transcription", "summary", "analysis"}


@router.post("", response_model=JobRead, status_code=status.HTTP_201_CREATED)
async def submit_job(
    payload: JobCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    if payload.job_type not in VALID_JOB_TYPES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid job_type. Must be one of: {', '.join(VALID_JOB_TYPES)}",
        )
    job = AIJob(
        id=uuid.uuid4(),
        owner_id=current_user.id,
        media_id=payload.media_id,
        job_type=payload.job_type,
        status="pending",
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    # Dispatch to Celery (fire-and-forget)
    try:
        from app.workers.tasks import process_ai_job
        task = process_ai_job.delay(str(job.id))
        job.celery_task_id = task.id
        db.add(job)
        await db.commit()
        await db.refresh(job)
    except Exception:
        # Celery not available in test/dev without broker; job remains pending
        pass

    return job


@router.get("", response_model=list[JobRead])
async def list_jobs(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    result = await db.execute(
        select(AIJob).where(AIJob.owner_id == current_user.id)
    )
    return result.scalars().all()


@router.get("/{job_id}", response_model=JobRead)
async def get_job(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    return await _get_owned_job(job_id, current_user.id, db)


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_job(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    job = await _get_owned_job(job_id, current_user.id, db)
    if job.celery_task_id:
        try:
            from app.workers.celery_app import celery_app
            celery_app.control.revoke(job.celery_task_id, terminate=True)
        except Exception:
            pass
    await db.delete(job)
    await db.commit()


def _safe_ext(filename: str | None) -> str:
    if not filename:
        return ""
    _, ext = os.path.splitext(filename)
    return ext.lower()


async def _save_upload_to_tempfile(upload: UploadFile, suffix: str) -> str:
    """Stream an UploadFile to a temp file, enforcing the size cap."""
    fd, path = tempfile.mkstemp(suffix=suffix)
    written = 0
    try:
        with os.fdopen(fd, "wb") as f:
            while chunk := await upload.read(1024 * 1024):
                written += len(chunk)
                if written > MAX_COMPARISON_UPLOAD_BYTES:
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail=(
                            "Each video must be 50 MB or less for the synchronous "
                            "comparison endpoint."
                        ),
                    )
                f.write(chunk)
    except Exception:
        try:
            os.unlink(path)
        except OSError:
            pass
        raise
    return path


@router.post("/comparison")
async def create_comparison_job(
    background_tasks: BackgroundTasks,
    before: UploadFile = File(...),
    after: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
):
    """Render a side-by-side before/after MP4 synchronously.

    Phase 1 endpoint: keeps inputs and output as temp files on the API host
    (no S3, no Celery). Suitable for short clips (<= ~30s) on free hosting.
    """
    before_ext = _safe_ext(before.filename) or ".mp4"
    after_ext = _safe_ext(after.filename) or ".mp4"
    if before_ext not in ALLOWED_VIDEO_EXTENSIONS or after_ext not in ALLOWED_VIDEO_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=(
                "Unsupported video format. Allowed: "
                + ", ".join(sorted(ALLOWED_VIDEO_EXTENSIONS))
            ),
        )

    before_path = await _save_upload_to_tempfile(before, before_ext)
    after_path = await _save_upload_to_tempfile(after, after_ext)
    output_path = tempfile.mkstemp(suffix=".mp4")[1]

    def _cleanup() -> None:
        for p in (before_path, after_path, output_path):
            try:
                os.unlink(p)
            except OSError:
                pass

    background_tasks.add_task(_cleanup)

    # moviepy is fully synchronous and CPU-bound; off-load to a thread so we
    # don't block the event loop.
    from app.services.video_processor import create_comparison_video

    try:
        await asyncio.to_thread(
            create_comparison_video, before_path, after_path, output_path
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Video processing failed: {exc}",
        ) from exc

    return FileResponse(
        output_path,
        media_type="video/mp4",
        filename="comparison.mp4",
    )


async def _get_owned_job(
    job_id: uuid.UUID,
    owner_id: uuid.UUID,
    db: AsyncSession,
) -> AIJob:
    result = await db.execute(select(AIJob).where(AIJob.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    if job.owner_id != owner_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    return job
