import uuid
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions.base import AppError
from app.core.exceptions.codes import RESOURCE_NOT_FOUND
from app.db.models.repository import Repository
from app.services.github.clone_service import CloneService
from app.services.github.github_client import GitHubClient
from app.services.indexing.file_scanner import FileScanner
from app.services.indexing.repository_indexer import RepositoryIndexer


class RepositoryService:
    def __init__(
        self,
        session: AsyncSession,
        github_client: GitHubClient,
        clone_service: CloneService,
    ) -> None:
        self.session = session
        self.github_client = github_client
        self.clone_service = clone_service

    async def import_repository(self, repository: str, branch: str | None = None) -> Repository:
        metadata = await self.github_client.fetch_repository_metadata(repository)
        target_branch = branch or metadata.default_branch
        clone_path = self.clone_service.clone_or_update(metadata, target_branch)

        existing = await self._find_by_owner_name_branch(metadata.owner, metadata.name, target_branch)
        now = datetime.now(UTC)
        if existing is not None:
            existing.full_name = metadata.full_name
            existing.clone_path = str(clone_path)
            existing.private = metadata.private
            existing.default_branch = metadata.default_branch
            existing.last_synced = now
            await self.session.flush()
            await self.session.refresh(existing)
            
            # Automatically index repository after successful clone/update
            indexer = RepositoryIndexer(self.session, FileScanner())
            await indexer.index_repository(existing)
            
            return existing

        repository_model = Repository(
            owner=metadata.owner,
            name=metadata.name,
            full_name=metadata.full_name,
            branch=target_branch,
            clone_path=str(clone_path),
            private=metadata.private,
            default_branch=metadata.default_branch,
            last_synced=now,
        )
        self.session.add(repository_model)
        await self.session.flush()
        await self.session.refresh(repository_model)
        
        # Automatically index repository after successful clone
        indexer = RepositoryIndexer(self.session, FileScanner())
        await indexer.index_repository(repository_model)
        
        return repository_model

    async def list_repositories(self) -> list[Repository]:
        result = await self.session.execute(select(Repository).order_by(Repository.created_at.desc()))
        return list(result.scalars().all())

    async def get_repository(self, repository_id: uuid.UUID) -> Repository:
        repository = await self.session.get(Repository, repository_id)
        if repository is None:
            raise AppError(
                RESOURCE_NOT_FOUND,
                "Repository was not found.",
                {"repository_id": str(repository_id)},
            )
        return repository

    async def sync_repository(self, repository_id: uuid.UUID) -> Repository:
        repository = await self.get_repository(repository_id)
        self.clone_service.pull(Path(repository.clone_path))
        repository.last_synced = datetime.now(UTC)
        await self.session.flush()
        await self.session.refresh(repository)
        
        # Automatically index repository after successful sync
        indexer = RepositoryIndexer(self.session, FileScanner())
        await indexer.index_repository(repository)
        
        return repository

    async def _find_by_owner_name_branch(
        self,
        owner: str,
        name: str,
        branch: str,
    ) -> Repository | None:
        result = await self.session.execute(
            select(Repository).where(
                Repository.owner == owner,
                Repository.name == name,
                Repository.branch == branch,
            )
        )
        return result.scalar_one_or_none()
