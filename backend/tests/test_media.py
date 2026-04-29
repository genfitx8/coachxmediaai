import io

import pytest
from httpx import AsyncClient

from app.models.user import User


@pytest.mark.asyncio
async def test_create_project(client: AsyncClient, auth_headers: dict):
    response = await client.post(
        "/api/v1/projects",
        json={"name": "My Test Project", "description": "A project for testing"},
        headers=auth_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "My Test Project"
    assert "id" in data


@pytest.mark.asyncio
async def test_upload_media(client: AsyncClient, auth_headers: dict):
    # Create a project first
    project_resp = await client.post(
        "/api/v1/projects",
        json={"name": "Media Project"},
        headers=auth_headers,
    )
    assert project_resp.status_code == 201
    project_id = project_resp.json()["id"]

    file_content = b"fake video content"
    response = await client.post(
        "/api/v1/media/upload",
        data={"project_id": project_id},
        files={"file": ("test_video.mp4", io.BytesIO(file_content), "video/mp4")},
        headers=auth_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["filename"] == "test_video.mp4"
    assert data["content_type"] == "video/mp4"
    assert data["size_bytes"] == len(file_content)
    assert data["project_id"] == project_id
    return data["id"]


@pytest.mark.asyncio
async def test_get_media_owner_access(client: AsyncClient, auth_headers: dict):
    # Create project and upload media
    project_resp = await client.post(
        "/api/v1/projects",
        json={"name": "Owner Access Project"},
        headers=auth_headers,
    )
    project_id = project_resp.json()["id"]

    upload_resp = await client.post(
        "/api/v1/media/upload",
        data={"project_id": project_id},
        files={"file": ("clip.mp4", io.BytesIO(b"data"), "video/mp4")},
        headers=auth_headers,
    )
    media_id = upload_resp.json()["id"]

    response = await client.get(f"/api/v1/media/{media_id}", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["id"] == media_id


@pytest.mark.asyncio
async def test_get_media_other_user_forbidden(
    client: AsyncClient,
    auth_headers: dict,
    second_auth_headers: dict,
):
    # Owner creates project and uploads media
    project_resp = await client.post(
        "/api/v1/projects",
        json={"name": "Private Project"},
        headers=auth_headers,
    )
    project_id = project_resp.json()["id"]

    upload_resp = await client.post(
        "/api/v1/media/upload",
        data={"project_id": project_id},
        files={"file": ("private.mp4", io.BytesIO(b"secret"), "video/mp4")},
        headers=auth_headers,
    )
    media_id = upload_resp.json()["id"]

    # Other user tries to access
    response = await client.get(f"/api/v1/media/{media_id}", headers=second_auth_headers)
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_list_project_media(client: AsyncClient, auth_headers: dict):
    project_resp = await client.post(
        "/api/v1/projects",
        json={"name": "List Media Project"},
        headers=auth_headers,
    )
    project_id = project_resp.json()["id"]

    for i in range(2):
        await client.post(
            "/api/v1/media/upload",
            data={"project_id": project_id},
            files={"file": (f"file{i}.mp4", io.BytesIO(b"data"), "video/mp4")},
            headers=auth_headers,
        )

    response = await client.get(
        f"/api/v1/projects/{project_id}/media", headers=auth_headers
    )
    assert response.status_code == 200
    assert len(response.json()) >= 2


@pytest.mark.asyncio
async def test_delete_media(client: AsyncClient, auth_headers: dict):
    project_resp = await client.post(
        "/api/v1/projects",
        json={"name": "Delete Media Project"},
        headers=auth_headers,
    )
    project_id = project_resp.json()["id"]

    upload_resp = await client.post(
        "/api/v1/media/upload",
        data={"project_id": project_id},
        files={"file": ("todelete.mp4", io.BytesIO(b"data"), "video/mp4")},
        headers=auth_headers,
    )
    media_id = upload_resp.json()["id"]

    delete_resp = await client.delete(f"/api/v1/media/{media_id}", headers=auth_headers)
    assert delete_resp.status_code == 204

    get_resp = await client.get(f"/api/v1/media/{media_id}", headers=auth_headers)
    assert get_resp.status_code == 404
