import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_active_user
from app.database import get_db
from app.models.project import Project
from app.models.user import User
from app.schemas.project import ProjectCreate, ProjectRead, ProjectUpdate

router = APIRouter(prefix="/projects", tags=["projects"])


@router.post("", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
async def create_project(
    payload: ProjectCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    project = Project(
        id=uuid.uuid4(),
        owner_id=current_user.id,
        name=payload.name,
        description=payload.description,
    )
    db.add(project)
    await db.commit()
    await db.refresh(project)
    return project


@router.get("", response_model=list[ProjectRead])
async def list_projects(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    result = await db.execute(
        select(Project).where(Project.owner_id == current_user.id)
    )
    return result.scalars().all()


@router.get("/{project_id}", response_model=ProjectRead)
async def get_project(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    project = await _get_owned_project(project_id, current_user.id, db)
    return project


@router.put("/{project_id}", response_model=ProjectRead)
async def update_project(
    project_id: uuid.UUID,
    payload: ProjectUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    project = await _get_owned_project(project_id, current_user.id, db)
    if payload.name is not None:
        project.name = payload.name
    if payload.description is not None:
        project.description = payload.description
    if payload.is_active is not None:
        project.is_active = payload.is_active
    db.add(project)
    await db.commit()
    await db.refresh(project)
    return project


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    project = await _get_owned_project(project_id, current_user.id, db)
    await db.delete(project)
    await db.commit()


async def _get_owned_project(
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
