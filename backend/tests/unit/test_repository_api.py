import uuid
from datetime import UTC, datetime
from http import HTTPStatus
from types import SimpleNamespace

import pytest
from httpx import AsyncClient

from app.api.v1.repositories import get_repository_service
from app.main import app


class FakeRepositoryService:
    def __init__(self) -> None:
        now = datetime.now(UTC)
        self.repository = SimpleNamespace(
            id=uuid.uuid4(),
            owner="octocat",
            name="Hello-World",
            full_name="octocat/Hello-World",
            branch="main",
            clone_path="data/repos/octocat/Hello-World",
            private=False,
            default_branch="main",
            last_synced=now,
            created_at=now,
        )
        self.synced = False

    async def import_repository(self, repository: str, branch: str | None = None):
        assert repository == "octocat/Hello-World"
        assert branch is None
        return self.repository

    async def list_repositories(self):
        return [self.repository]

    async def get_repository(self, repository_id: uuid.UUID):
        assert repository_id == self.repository.id
        return self.repository

    async def sync_repository(self, repository_id: uuid.UUID):
        assert repository_id == self.repository.id
        self.synced = True
        return self.repository


@pytest.mark.asyncio
async def test_repository_routes(async_client: AsyncClient) -> None:
    service = FakeRepositoryService()
    app.dependency_overrides[get_repository_service] = lambda: service
    try:
        import_response = await async_client.post(
            "/api/v1/repositories/import",
            json={"repository": "octocat/Hello-World"},
        )
        assert import_response.status_code == HTTPStatus.CREATED
        payload = import_response.json()
        assert payload["full_name"] == "octocat/Hello-World"
        assert payload["clone_path"] == "data/repos/octocat/Hello-World"

        list_response = await async_client.get("/api/v1/repositories")
        assert list_response.status_code == HTTPStatus.OK
        assert list_response.json()[0]["id"] == payload["id"]

        detail_response = await async_client.get(f"/api/v1/repositories/{payload['id']}")
        assert detail_response.status_code == HTTPStatus.OK
        assert detail_response.json()["name"] == "Hello-World"

        sync_response = await async_client.post(f"/api/v1/repositories/{payload['id']}/sync")
        assert sync_response.status_code == HTTPStatus.OK
        assert sync_response.json()["id"] == payload["id"]
        assert service.synced is True
    finally:
        app.dependency_overrides.clear()
