import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.core.config.settings import settings
from app.schemas.repository import RepositoryImportRequest, RepositoryResponse
from app.services.github import CloneService, GitHubClient, RepositoryService

router = APIRouter(prefix="/repositories", tags=["repositories"])
DbSessionDep = Depends(get_db)


def get_repository_service(session: AsyncSession = DbSessionDep) -> RepositoryService:
    return RepositoryService(
        session=session,
        github_client=GitHubClient(token=settings.github_token),
        clone_service=CloneService(
            storage_root=settings.repo_storage_path,
            token=settings.github_token,
        ),
    )


RepositoryServiceDep = Depends(get_repository_service)


@router.post("/import", response_model=RepositoryResponse, status_code=status.HTTP_201_CREATED)
async def import_repository(
    payload: RepositoryImportRequest,
    service: RepositoryService = RepositoryServiceDep,
) -> RepositoryResponse:
    repository = await service.import_repository(payload.repository, payload.branch)
    return RepositoryResponse.model_validate(repository)


@router.get("", response_model=list[RepositoryResponse])
async def list_repositories(
    service: RepositoryService = RepositoryServiceDep,
) -> list[RepositoryResponse]:
    repositories = await service.list_repositories()
    return [RepositoryResponse.model_validate(repository) for repository in repositories]


@router.get("/{repository_id}", response_model=RepositoryResponse)
async def get_repository(
    repository_id: uuid.UUID,
    service: RepositoryService = RepositoryServiceDep,
) -> RepositoryResponse:
    repository = await service.get_repository(repository_id)
    return RepositoryResponse.model_validate(repository)


@router.post("/{repository_id}/sync", response_model=RepositoryResponse)
async def sync_repository(
    repository_id: uuid.UUID,
    service: RepositoryService = RepositoryServiceDep,
) -> RepositoryResponse:
    repository = await service.sync_repository(repository_id)
    return RepositoryResponse.model_validate(repository)
