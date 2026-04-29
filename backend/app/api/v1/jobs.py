import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_active_user
from app.database import get_db
from app.models.job import AIJob
from app.models.user import User
from app.schemas.job import JobCreate, JobRead

router = APIRouter(prefix="/jobs", tags=["jobs"])

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
