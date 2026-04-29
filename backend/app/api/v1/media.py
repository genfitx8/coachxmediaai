import asyncio
import io
import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.dependencies import get_current_active_user
from app.database import get_db
from app.models.media import Media
from app.models.project import Project
from app.models.user import User
from app.schemas.media import (
    ConfirmUploadRequest,
    MediaRead,
    PresignedUrlRequest,
    PresignedUrlResponse,
)
from app.services.storage import get_storage_service

router = APIRouter(tags=["media"])


@router.post("/media/upload", response_model=MediaRead, status_code=status.HTTP_201_CREATED)
async def upload_media(
    project_id: uuid.UUID = Form(...),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    file_bytes = await file.read()
    if len(file_bytes) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds maximum size of {settings.MAX_UPLOAD_SIZE_MB} MB",
        )

    await _assert_project_owner(project_id, current_user.id, db)

    storage = get_storage_service()
    storage_key = f"uploads/{current_user.id}/{project_id}/{uuid.uuid4()}_{file.filename}"
    await _run_sync(storage.upload_file, io.BytesIO(file_bytes), storage_key, file.content_type or "application/octet-stream")

    media = Media(
        id=uuid.uuid4(),
        project_id=project_id,
        owner_id=current_user.id,
        filename=file.filename or "unknown",
        content_type=file.content_type or "application/octet-stream",
        size_bytes=len(file_bytes),
        storage_key=storage_key,
    )
    db.add(media)
    await db.commit()
    await db.refresh(media)
    return media


@router.post("/media/presigned-url", response_model=PresignedUrlResponse)
async def generate_presigned_url(
    payload: PresignedUrlRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    await _assert_project_owner(payload.project_id, current_user.id, db)
    storage = get_storage_service()
    storage_key = f"uploads/{current_user.id}/{payload.project_id}/{uuid.uuid4()}_{payload.filename}"
    upload_url = await _run_sync(
        storage.generate_presigned_put_url, storage_key, payload.content_type
    )
    return PresignedUrlResponse(upload_url=upload_url, storage_key=storage_key)


@router.post("/media/confirm-upload", response_model=MediaRead, status_code=status.HTTP_201_CREATED)
async def confirm_upload(
    payload: ConfirmUploadRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    await _assert_project_owner(payload.project_id, current_user.id, db)
    media = Media(
        id=uuid.uuid4(),
        project_id=payload.project_id,
        owner_id=current_user.id,
        filename=payload.filename,
        content_type=payload.content_type,
        size_bytes=payload.size_bytes,
        storage_key=payload.storage_key,
    )
    db.add(media)
    await db.commit()
    await db.refresh(media)
    return media


@router.get("/media/{media_id}", response_model=MediaRead)
async def get_media(
    media_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    media = await _get_owned_media(media_id, current_user.id, db)
    return media


@router.get("/projects/{project_id}/media", response_model=list[MediaRead])
async def list_project_media(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    await _assert_project_owner(project_id, current_user.id, db)
    result = await db.execute(select(Media).where(Media.project_id == project_id))
    return result.scalars().all()


@router.delete("/media/{media_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_media(
    media_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    media = await _get_owned_media(media_id, current_user.id, db)
    storage = get_storage_service()
    await _run_sync(storage.delete_file, media.storage_key)
    await db.delete(media)
    await db.commit()


async def _assert_project_owner(
    project_id: uuid.UUID,
    owner_id: uuid.UUID,
    db: AsyncSession,
) -> Project:
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    if project.owner_id != owner_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    return project


async def _get_owned_media(
    media_id: uuid.UUID,
    owner_id: uuid.UUID,
    db: AsyncSession,
) -> Media:
    result = await db.execute(select(Media).where(Media.id == media_id))
    media = result.scalar_one_or_none()
    if not media:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Media not found")
    if media.owner_id != owner_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    return media


async def _run_sync(func, *args):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, func, *args)
