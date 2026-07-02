import uuid
from collections import Counter
from pathlib import Path

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions.base import AppError
from app.core.exceptions.codes import RESOURCE_NOT_FOUND
from app.db.models.repository import Repository
from app.db.models.repository_file import RepositoryFile
from app.services.indexing.file_scanner import FileScanner, ScannedFile

LARGEST_FILE_LIMIT = 5


class RepositoryIndexer:
    def __init__(self, session: AsyncSession, file_scanner: FileScanner | None = None) -> None:
        self.session = session
        self.file_scanner = file_scanner or FileScanner()

    async def index_repository(self, repository: Repository) -> dict:
        scanned_files = self.file_scanner.scan(repository.clone_path)
        await self.session.execute(
            delete(RepositoryFile).where(RepositoryFile.repository_id == repository.id)
        )
        models = [self._to_model(repository.id, scanned_file) for scanned_file in scanned_files]
        self.session.add_all(models)
        await self.session.flush()
        return self.build_statistics(scanned_files)

    async def index_repository_by_id(self, repository_id: uuid.UUID) -> dict:
        repository = await self._get_repository(repository_id)
        return await self.index_repository(repository)

    async def list_files(self, repository_id: uuid.UUID) -> list[RepositoryFile]:
        await self._get_repository(repository_id)
        result = await self.session.execute(
            select(RepositoryFile)
            .where(RepositoryFile.repository_id == repository_id)
            .order_by(RepositoryFile.relative_path.asc())
        )
        return list(result.scalars().all())

    async def get_file(self, repository_id: uuid.UUID, file_id: uuid.UUID) -> RepositoryFile:
        await self._get_repository(repository_id)
        result = await self.session.execute(
            select(RepositoryFile).where(
                RepositoryFile.id == file_id,
                RepositoryFile.repository_id == repository_id,
            )
        )
        repository_file = result.scalar_one_or_none()
        if repository_file is None:
            raise AppError(
                RESOURCE_NOT_FOUND,
                "Repository file was not found.",
                {"repository_id": str(repository_id), "file_id": str(file_id)},
            )
        return repository_file

    async def get_statistics(self, repository_id: uuid.UUID) -> dict:
        await self._get_repository(repository_id)
        files = await self.list_files(repository_id)
        return self.build_statistics_from_models(files)

    @staticmethod
    def build_statistics(scanned_files: list[ScannedFile]) -> dict:
        files_per_language = Counter(file.language for file in scanned_files)
        largest_files = sorted(scanned_files, key=lambda file: file.size_bytes, reverse=True)[
            :LARGEST_FILE_LIMIT
        ]
        return {
            "total_files": len(scanned_files),
            "files_per_language": dict(sorted(files_per_language.items())),
            "total_bytes": sum(file.size_bytes for file in scanned_files),
            "largest_files": [
                {
                    "relative_path": file.relative_path,
                    "language": file.language,
                    "size_bytes": file.size_bytes,
                }
                for file in largest_files
            ],
            "binary_file_count": sum(1 for file in scanned_files if file.is_binary),
        }

    @staticmethod
    def build_statistics_from_models(repository_files: list[RepositoryFile]) -> dict:
        files_per_language = Counter(file.language for file in repository_files)
        largest_files = sorted(repository_files, key=lambda file: file.size_bytes, reverse=True)[
            :LARGEST_FILE_LIMIT
        ]
        return {
            "total_files": len(repository_files),
            "files_per_language": dict(sorted(files_per_language.items())),
            "total_bytes": sum(file.size_bytes for file in repository_files),
            "largest_files": [
                {
                    "relative_path": file.relative_path,
                    "language": file.language,
                    "size_bytes": file.size_bytes,
                }
                for file in largest_files
            ],
            "binary_file_count": sum(1 for file in repository_files if file.is_binary),
        }

    async def _get_repository(self, repository_id: uuid.UUID) -> Repository:
        repository = await self.session.get(Repository, repository_id)
        if repository is None:
            raise AppError(
                RESOURCE_NOT_FOUND,
                "Repository was not found.",
                {"repository_id": str(repository_id)},
            )
        return repository

    @staticmethod
    def _to_model(repository_id: uuid.UUID, scanned_file: ScannedFile) -> RepositoryFile:
        return RepositoryFile(
            repository_id=repository_id,
            relative_path=scanned_file.relative_path,
            absolute_path=scanned_file.absolute_path,
            file_name=scanned_file.file_name,
            extension=scanned_file.extension,
            language=scanned_file.language,
            size_bytes=scanned_file.size_bytes,
            line_count=scanned_file.line_count,
            sha256_hash=scanned_file.sha256_hash,
            last_modified=scanned_file.last_modified,
            is_binary=scanned_file.is_binary,
        )
