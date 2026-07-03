import uuid
from collections import Counter

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions.base import AppError
from app.core.exceptions.codes import RESOURCE_NOT_FOUND
from app.db.models.repository import Repository
from app.db.models.repository_file import RepositoryFile
from app.services.indexing.file_scanner import FileScanner, ScannedFile
from app.services.indexing.symbol_extractor import SymbolExtractor

LARGEST_FILE_LIMIT = 5


class RepositoryIndexer:
    def __init__(
        self,
        session: AsyncSession,
        file_scanner: FileScanner | None = None,
        symbol_extractor: SymbolExtractor | None = None,
    ) -> None:
        self.session = session
        self.file_scanner = file_scanner or FileScanner()
        self.symbol_extractor = symbol_extractor or SymbolExtractor(session)

    async def index_repository(self, repository: Repository) -> dict:
        # Scan files
        scanned_files = self.file_scanner.scan(repository.clone_path)

        # Delete existing files and symbols (cascade delete handles symbols)
        await self.session.execute(
            delete(RepositoryFile).where(RepositoryFile.repository_id == repository.id)
        )

        # Create file models
        models = [self._to_model(repository.id, scanned_file) for scanned_file in scanned_files]
        self.session.add_all(models)
        await self.session.flush()

        # Extract symbols from each file
        symbol_stats = await self._extract_symbols_from_files(models)

        # Build and return statistics
        stats = self.build_statistics(scanned_files)
        stats["symbols"] = symbol_stats

        return stats

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

    async def _extract_symbols_from_files(
        self, repository_files: list[RepositoryFile]
    ) -> dict:
        """Extract symbols from all repository files.

        Args:
            repository_files: List of RepositoryFile models to parse

        Returns:
            Dictionary with symbol extraction statistics
        """
        total_symbols = 0
        files_parsed = 0
        files_skipped = 0
        parse_errors = 0
        symbols_by_language = {}

        for repo_file in repository_files:
            result = await self.symbol_extractor.extract_and_store_symbols(repo_file)

            if result["success"]:
                files_parsed += 1
                total_symbols += result["symbols_extracted"]

                # Track symbols by language
                language = result["language"]
                if language not in symbols_by_language:
                    symbols_by_language[language] = 0
                symbols_by_language[language] += result["symbols_extracted"]
            elif result["reason"] == "parse_error":
                parse_errors += 1
            else:
                files_skipped += 1

        return {
            "total_symbols": total_symbols,
            "files_parsed": files_parsed,
            "files_skipped": files_skipped,
            "parse_errors": parse_errors,
            "symbols_by_language": symbols_by_language,
        }
