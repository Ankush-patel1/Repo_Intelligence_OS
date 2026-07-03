import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.core.config.settings import settings
from app.schemas.repository import (
    RepositoryFileResponse,
    RepositoryImportRequest,
    RepositoryIndexResponse,
    RepositoryPipelineResponse,
    RepositoryResponse,
    RepositoryStatistics,
)
from app.services.github import CloneService, GitHubClient, RepositoryService
from app.services.indexing import FileScanner, RepositoryIndexer
from app.services.orchestration import RepositoryPipeline

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


def get_indexer_service(session: AsyncSession = DbSessionDep) -> RepositoryIndexer:
    return RepositoryIndexer(session=session, file_scanner=FileScanner())


def get_pipeline_service(session: AsyncSession = DbSessionDep) -> RepositoryPipeline:
    return RepositoryPipeline(session=session)


IndexerServiceDep = Depends(get_indexer_service)
PipelineServiceDep = Depends(get_pipeline_service)


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


@router.post("/{repository_id}/index", response_model=RepositoryIndexResponse, status_code=status.HTTP_202_ACCEPTED)
async def index_repository(
    repository_id: uuid.UUID,
    indexer: RepositoryIndexer = IndexerServiceDep,
) -> RepositoryIndexResponse:
    """Index or re-index a repository's files.

    Scans the repository filesystem and persists file metadata to the database.
    Re-indexing will delete old file records and create new ones.
    """
    statistics = await indexer.index_repository_by_id(repository_id)
    return RepositoryIndexResponse(
        repository_id=repository_id,
        statistics=RepositoryStatistics(**statistics),
    )


@router.get("/{repository_id}/files", response_model=list[RepositoryFileResponse])
async def list_repository_files(
    repository_id: uuid.UUID,
    indexer: RepositoryIndexer = IndexerServiceDep,
) -> list[RepositoryFileResponse]:
    """List all indexed files for a repository.

    Returns files sorted by relative path.
    """
    files = await indexer.list_files(repository_id)
    return [RepositoryFileResponse.model_validate(file) for file in files]


@router.get("/{repository_id}/files/{file_id}", response_model=RepositoryFileResponse)
async def get_repository_file(
    repository_id: uuid.UUID,
    file_id: uuid.UUID,
    indexer: RepositoryIndexer = IndexerServiceDep,
) -> RepositoryFileResponse:
    """Get metadata for a specific file.

    Returns detailed information about a single indexed file.
    """
    file = await indexer.get_file(repository_id, file_id)
    return RepositoryFileResponse.model_validate(file)


@router.get("/{repository_id}/statistics", response_model=RepositoryStatistics)
async def get_repository_statistics(
    repository_id: uuid.UUID,
    indexer: RepositoryIndexer = IndexerServiceDep,
) -> RepositoryStatistics:
    """Get statistics about repository files.

    Returns aggregated information including file counts by language,
    total size, and largest files.
    """
    statistics = await indexer.get_statistics(repository_id)
    return RepositoryStatistics(**statistics)


@router.post("/{repository_id}/analyze", response_model=RepositoryPipelineResponse, status_code=status.HTTP_202_ACCEPTED)
async def analyze_repository(
    repository_id: uuid.UUID,
    pipeline: RepositoryPipeline = PipelineServiceDep,
    session: AsyncSession = DbSessionDep,
) -> RepositoryPipelineResponse:
    """Run complete analysis pipeline: Index → Parse → Build Graph.

    This is the recommended endpoint for full repository analysis.
    Performs all steps in sequence:
    1. Index repository (scan files)
    2. Parse symbols (extract code symbols)
    3. Build knowledge graph (create nodes and edges)

    Args:
        repository_id: UUID of the repository

    Returns:
        RepositoryPipelineResponse with statistics from all stages
    """
    results = await pipeline.run_full_pipeline(repository_id)
    await session.commit()
    return RepositoryPipelineResponse(**results)


@router.post("/{repository_id}/rebuild-graph", status_code=status.HTTP_202_ACCEPTED)
async def rebuild_repository_graph(
    repository_id: uuid.UUID,
    pipeline: RepositoryPipeline = PipelineServiceDep,
    session: AsyncSession = DbSessionDep,
) -> dict:
    """Rebuild knowledge graph without re-indexing.

    Useful when:
    - Graph logic has been updated
    - Graph needs to be regenerated from existing data
    - You want to rebuild graph without re-parsing files

    Args:
        repository_id: UUID of the repository

    Returns:
        Dictionary with graph build statistics
    """
    results = await pipeline.rebuild_graph(repository_id)
    await session.commit()
    return results


@router.get("/{repository_id}/pipeline-status")
async def get_pipeline_status(
    repository_id: uuid.UUID,
    pipeline: RepositoryPipeline = PipelineServiceDep,
) -> dict:
    """Get status of pipeline stages for a repository.

    Shows which pipeline stages have been completed:
    - Indexed (files scanned and symbols extracted)
    - Graph built (nodes and edges created)

    Args:
        repository_id: UUID of the repository

    Returns:
        Dictionary with pipeline status and statistics
    """
    return await pipeline.get_pipeline_status(repository_id)
