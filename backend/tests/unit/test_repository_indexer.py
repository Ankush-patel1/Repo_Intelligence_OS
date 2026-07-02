"""Unit tests for RepositoryIndexer service."""

import tempfile
import uuid
from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions.base import AppError
from app.core.exceptions.codes import RESOURCE_NOT_FOUND
from app.db.models.repository import Repository
from app.db.models.repository_file import RepositoryFile
from app.services.indexing.file_scanner import FileScanner, ScannedFile
from app.services.indexing.repository_indexer import LARGEST_FILE_LIMIT, RepositoryIndexer


class TestRepositoryIndexer:
    """Test suite for RepositoryIndexer."""

    @pytest.fixture
    async def repository(self, session: AsyncSession) -> Repository:
        """Create a test repository."""
        repo = Repository(
            owner="testuser",
            name="testrepo",
            full_name="testuser/testrepo",
            branch="main",
            clone_path="/tmp/test-repo",
            private=False,
            default_branch="main",
        )
        session.add(repo)
        await session.flush()
        await session.refresh(repo)
        return repo

    @pytest.fixture
    def indexer(self, session: AsyncSession) -> RepositoryIndexer:
        """Create a RepositoryIndexer instance."""
        return RepositoryIndexer(session=session)

    @pytest.fixture
    def mock_scanned_files(self) -> list[ScannedFile]:
        """Create mock scanned files for testing."""
        return [
            ScannedFile(
                relative_path="src/main.py",
                absolute_path="/tmp/test-repo/src/main.py",
                file_name="main.py",
                extension=".py",
                language="Python",
                size_bytes=1024,
                line_count=50,
                sha256_hash="abc123def456",
                last_modified=datetime.now(UTC),
                is_binary=False,
            ),
            ScannedFile(
                relative_path="src/utils.py",
                absolute_path="/tmp/test-repo/src/utils.py",
                file_name="utils.py",
                extension=".py",
                language="Python",
                size_bytes=512,
                line_count=25,
                sha256_hash="def456abc123",
                last_modified=datetime.now(UTC),
                is_binary=False,
            ),
            ScannedFile(
                relative_path="app.js",
                absolute_path="/tmp/test-repo/app.js",
                file_name="app.js",
                extension=".js",
                language="JavaScript",
                size_bytes=2048,
                line_count=100,
                sha256_hash="js123456",
                last_modified=datetime.now(UTC),
                is_binary=False,
            ),
            ScannedFile(
                relative_path="data.bin",
                absolute_path="/tmp/test-repo/data.bin",
                file_name="data.bin",
                extension=".bin",
                language="Unknown",
                size_bytes=4096,
                line_count=None,
                sha256_hash="bin789abc",
                last_modified=datetime.now(UTC),
                is_binary=True,
            ),
        ]

    # Constructor tests
    def test_indexer_initialization(self, session: AsyncSession) -> None:
        """Test RepositoryIndexer initialization."""
        indexer = RepositoryIndexer(session=session)
        assert indexer.session == session
        assert isinstance(indexer.file_scanner, FileScanner)

    def test_indexer_with_custom_scanner(self, session: AsyncSession) -> None:
        """Test RepositoryIndexer with custom FileScanner."""
        custom_scanner = FileScanner(max_file_size_bytes=1000)
        indexer = RepositoryIndexer(session=session, file_scanner=custom_scanner)
        assert indexer.file_scanner == custom_scanner

    # _to_model tests
    def test_to_model_conversion(self) -> None:
        """Test ScannedFile to RepositoryFile conversion."""
        repo_id = uuid.uuid4()
        scanned = ScannedFile(
            relative_path="test.py",
            absolute_path="/path/test.py",
            file_name="test.py",
            extension=".py",
            language="Python",
            size_bytes=100,
            line_count=10,
            sha256_hash="hash123",
            last_modified=datetime.now(UTC),
            is_binary=False,
        )

        model = RepositoryIndexer._to_model(repo_id, scanned)

        assert isinstance(model, RepositoryFile)
        assert model.repository_id == repo_id
        assert model.relative_path == scanned.relative_path
        assert model.absolute_path == scanned.absolute_path
        assert model.file_name == scanned.file_name
        assert model.extension == scanned.extension
        assert model.language == scanned.language
        assert model.size_bytes == scanned.size_bytes
        assert model.line_count == scanned.line_count
        assert model.sha256_hash == scanned.sha256_hash
        assert model.last_modified == scanned.last_modified
        assert model.is_binary == scanned.is_binary

    def test_to_model_binary_file(self) -> None:
        """Test conversion of binary file with None line_count."""
        repo_id = uuid.uuid4()
        scanned = ScannedFile(
            relative_path="data.bin",
            absolute_path="/path/data.bin",
            file_name="data.bin",
            extension=".bin",
            language="Unknown",
            size_bytes=500,
            line_count=None,
            sha256_hash="binhash",
            last_modified=datetime.now(UTC),
            is_binary=True,
        )

        model = RepositoryIndexer._to_model(repo_id, scanned)

        assert model.is_binary is True
        assert model.line_count is None

    # _get_repository tests
    async def test_get_repository_success(
        self, indexer: RepositoryIndexer, repository: Repository
    ) -> None:
        """Test getting an existing repository."""
        result = await indexer._get_repository(repository.id)
        assert result.id == repository.id
        assert result.owner == repository.owner
        assert result.name == repository.name

    async def test_get_repository_not_found(self, indexer: RepositoryIndexer) -> None:
        """Test getting a non-existent repository raises error."""
        nonexistent_id = uuid.uuid4()
        with pytest.raises(AppError) as exc_info:
            await indexer._get_repository(nonexistent_id)

        assert exc_info.value.code == RESOURCE_NOT_FOUND
        assert "Repository was not found" in exc_info.value.message
        assert str(nonexistent_id) in str(exc_info.value.details)

    # build_statistics tests
    def test_build_statistics_from_scanned_files(
        self, mock_scanned_files: list[ScannedFile]
    ) -> None:
        """Test statistics generation from scanned files."""
        stats = RepositoryIndexer.build_statistics(mock_scanned_files)

        assert stats["total_files"] == 4
        assert stats["files_per_language"] == {"JavaScript": 1, "Python": 2, "Unknown": 1}
        assert stats["total_bytes"] == 1024 + 512 + 2048 + 4096  # 7680
        assert stats["binary_file_count"] == 1

        # Check largest files (top 5, sorted by size)
        assert len(stats["largest_files"]) == 4  # Only 4 files total
        assert stats["largest_files"][0]["relative_path"] == "data.bin"
        assert stats["largest_files"][0]["size_bytes"] == 4096

    def test_build_statistics_empty_list(self) -> None:
        """Test statistics with empty file list."""
        stats = RepositoryIndexer.build_statistics([])

        assert stats["total_files"] == 0
        assert stats["files_per_language"] == {}
        assert stats["total_bytes"] == 0
        assert stats["binary_file_count"] == 0
        assert stats["largest_files"] == []

    def test_build_statistics_largest_files_limit(self) -> None:
        """Test that largest_files respects LARGEST_FILE_LIMIT."""
        # Create more files than the limit
        files = []
        for i in range(10):
            files.append(
                ScannedFile(
                    relative_path=f"file{i}.py",
                    absolute_path=f"/path/file{i}.py",
                    file_name=f"file{i}.py",
                    extension=".py",
                    language="Python",
                    size_bytes=(i + 1) * 100,  # Different sizes
                    line_count=10,
                    sha256_hash=f"hash{i}",
                    last_modified=datetime.now(UTC),
                    is_binary=False,
                )
            )

        stats = RepositoryIndexer.build_statistics(files)

        assert stats["total_files"] == 10
        assert len(stats["largest_files"]) == LARGEST_FILE_LIMIT
        # Verify they are sorted by size (largest first)
        sizes = [f["size_bytes"] for f in stats["largest_files"]]
        assert sizes == sorted(sizes, reverse=True)

    def test_build_statistics_all_binary(self) -> None:
        """Test statistics when all files are binary."""
        binary_files = [
            ScannedFile(
                relative_path=f"data{i}.bin",
                absolute_path=f"/path/data{i}.bin",
                file_name=f"data{i}.bin",
                extension=".bin",
                language="Unknown",
                size_bytes=100,
                line_count=None,
                sha256_hash=f"hash{i}",
                last_modified=datetime.now(UTC),
                is_binary=True,
            )
            for i in range(3)
        ]

        stats = RepositoryIndexer.build_statistics(binary_files)

        assert stats["total_files"] == 3
        assert stats["binary_file_count"] == 3

    def test_build_statistics_from_models(self) -> None:
        """Test statistics generation from RepositoryFile models."""
        repo_id = uuid.uuid4()
        models = [
            RepositoryFile(
                repository_id=repo_id,
                relative_path="test1.py",
                absolute_path="/path/test1.py",
                file_name="test1.py",
                extension=".py",
                language="Python",
                size_bytes=200,
                line_count=10,
                sha256_hash="hash1",
                last_modified=datetime.now(UTC),
                is_binary=False,
            ),
            RepositoryFile(
                repository_id=repo_id,
                relative_path="test2.py",
                absolute_path="/path/test2.py",
                file_name="test2.py",
                extension=".py",
                language="Python",
                size_bytes=300,
                line_count=15,
                sha256_hash="hash2",
                last_modified=datetime.now(UTC),
                is_binary=False,
            ),
        ]

        stats = RepositoryIndexer.build_statistics_from_models(models)

        assert stats["total_files"] == 2
        assert stats["files_per_language"] == {"Python": 2}
        assert stats["total_bytes"] == 500
        assert stats["binary_file_count"] == 0

    # index_repository tests
    async def test_index_repository_creates_files(
        self, indexer: RepositoryIndexer, repository: Repository, session: AsyncSession
    ) -> None:
        """Test that index_repository creates file records."""
        # Create a real temporary directory with files
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            (tmp_path / "test.py").write_text("print('hello')\n")
            (tmp_path / "app.js").write_text("console.log('test');\n")

            # Update repository clone_path to temp directory
            repository.clone_path = str(tmp_path)
            await session.flush()

            # Index the repository
            stats = await indexer.index_repository(repository)

            # Verify statistics
            assert stats["total_files"] == 2
            assert "Python" in stats["files_per_language"]
            assert "JavaScript" in stats["files_per_language"]

            # Verify database records
            result = await session.execute(
                select(RepositoryFile).where(RepositoryFile.repository_id == repository.id)
            )
            files = list(result.scalars().all())
            assert len(files) == 2

            # Verify file metadata
            py_file = next((f for f in files if f.file_name == "test.py"), None)
            assert py_file is not None
            assert py_file.language == "Python"
            assert py_file.relative_path == "test.py"

    async def test_index_repository_deletes_old_files(
        self, indexer: RepositoryIndexer, repository: Repository, session: AsyncSession
    ) -> None:
        """Test that re-indexing deletes old file records."""
        # Create initial file records
        old_file = RepositoryFile(
            repository_id=repository.id,
            relative_path="old.py",
            absolute_path="/path/old.py",
            file_name="old.py",
            extension=".py",
            language="Python",
            size_bytes=100,
            line_count=5,
            sha256_hash="oldhash",
            last_modified=datetime.now(UTC),
            is_binary=False,
        )
        session.add(old_file)
        await session.flush()

        # Create temp directory with new files
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            (tmp_path / "new.py").write_text("print('new')\n")

            repository.clone_path = str(tmp_path)
            await session.flush()

            # Re-index
            await indexer.index_repository(repository)

            # Verify old file is deleted
            result = await session.execute(
                select(RepositoryFile).where(RepositoryFile.repository_id == repository.id)
            )
            files = list(result.scalars().all())

            assert len(files) == 1
            assert files[0].file_name == "new.py"
            assert not any(f.file_name == "old.py" for f in files)

    async def test_index_repository_empty_directory(
        self, indexer: RepositoryIndexer, repository: Repository, session: AsyncSession
    ) -> None:
        """Test indexing an empty directory."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            repository.clone_path = tmp_dir
            await session.flush()

            stats = await indexer.index_repository(repository)

            assert stats["total_files"] == 0
            assert stats["files_per_language"] == {}
            assert stats["total_bytes"] == 0

            # Verify no database records
            result = await session.execute(
                select(RepositoryFile).where(RepositoryFile.repository_id == repository.id)
            )
            files = list(result.scalars().all())
            assert len(files) == 0

    async def test_index_repository_nonexistent_path(
        self, indexer: RepositoryIndexer, repository: Repository
    ) -> None:
        """Test indexing a non-existent path."""
        repository.clone_path = "/nonexistent/path/to/repo"

        stats = await indexer.index_repository(repository)

        # Should return empty statistics without error
        assert stats["total_files"] == 0
        assert stats["files_per_language"] == {}

    # index_repository_by_id tests
    async def test_index_repository_by_id_success(
        self, indexer: RepositoryIndexer, repository: Repository, session: AsyncSession
    ) -> None:
        """Test indexing repository by ID."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            (tmp_path / "test.py").write_text("test\n")

            repository.clone_path = str(tmp_path)
            await session.flush()

            stats = await indexer.index_repository_by_id(repository.id)

            assert stats["total_files"] == 1

    async def test_index_repository_by_id_not_found(self, indexer: RepositoryIndexer) -> None:
        """Test indexing non-existent repository by ID."""
        nonexistent_id = uuid.uuid4()

        with pytest.raises(AppError) as exc_info:
            await indexer.index_repository_by_id(nonexistent_id)

        assert exc_info.value.code == RESOURCE_NOT_FOUND

    # list_files tests
    async def test_list_files_success(
        self, indexer: RepositoryIndexer, repository: Repository, session: AsyncSession
    ) -> None:
        """Test listing files for a repository."""
        # Create file records
        files_data = [
            ("z.py", "Python"),
            ("a.js", "JavaScript"),
            ("m.py", "Python"),
        ]

        for file_name, language in files_data:
            file_record = RepositoryFile(
                repository_id=repository.id,
                relative_path=file_name,
                absolute_path=f"/path/{file_name}",
                file_name=file_name,
                extension=Path(file_name).suffix,
                language=language,
                size_bytes=100,
                line_count=10,
                sha256_hash=f"hash_{file_name}",
                last_modified=datetime.now(UTC),
                is_binary=False,
            )
            session.add(file_record)

        await session.flush()

        # List files
        files = await indexer.list_files(repository.id)

        assert len(files) == 3
        # Verify they are sorted by relative_path
        file_names = [f.relative_path for f in files]
        assert file_names == ["a.js", "m.py", "z.py"]

    async def test_list_files_empty(
        self, indexer: RepositoryIndexer, repository: Repository
    ) -> None:
        """Test listing files for repository with no files."""
        files = await indexer.list_files(repository.id)
        assert files == []

    async def test_list_files_repository_not_found(self, indexer: RepositoryIndexer) -> None:
        """Test listing files for non-existent repository."""
        nonexistent_id = uuid.uuid4()

        with pytest.raises(AppError) as exc_info:
            await indexer.list_files(nonexistent_id)

        assert exc_info.value.code == RESOURCE_NOT_FOUND

    # get_file tests
    async def test_get_file_success(
        self, indexer: RepositoryIndexer, repository: Repository, session: AsyncSession
    ) -> None:
        """Test getting a specific file."""
        file_record = RepositoryFile(
            repository_id=repository.id,
            relative_path="test.py",
            absolute_path="/path/test.py",
            file_name="test.py",
            extension=".py",
            language="Python",
            size_bytes=100,
            line_count=10,
            sha256_hash="testhash",
            last_modified=datetime.now(UTC),
            is_binary=False,
        )
        session.add(file_record)
        await session.flush()
        await session.refresh(file_record)

        result = await indexer.get_file(repository.id, file_record.id)

        assert result.id == file_record.id
        assert result.file_name == "test.py"
        assert result.language == "Python"

    async def test_get_file_not_found(
        self, indexer: RepositoryIndexer, repository: Repository
    ) -> None:
        """Test getting a non-existent file."""
        nonexistent_file_id = uuid.uuid4()

        with pytest.raises(AppError) as exc_info:
            await indexer.get_file(repository.id, nonexistent_file_id)

        assert exc_info.value.code == RESOURCE_NOT_FOUND
        assert "Repository file was not found" in exc_info.value.message

    async def test_get_file_wrong_repository(
        self, indexer: RepositoryIndexer, repository: Repository, session: AsyncSession
    ) -> None:
        """Test getting a file with wrong repository ID."""
        # Create file for this repository
        file_record = RepositoryFile(
            repository_id=repository.id,
            relative_path="test.py",
            absolute_path="/path/test.py",
            file_name="test.py",
            extension=".py",
            language="Python",
            size_bytes=100,
            line_count=10,
            sha256_hash="hash",
            last_modified=datetime.now(UTC),
            is_binary=False,
        )
        session.add(file_record)
        await session.flush()
        await session.refresh(file_record)

        # Try to get with different repository ID
        wrong_repo_id = uuid.uuid4()

        with pytest.raises(AppError) as exc_info:
            await indexer.get_file(wrong_repo_id, file_record.id)

        # Should fail because repository doesn't exist
        assert exc_info.value.code == RESOURCE_NOT_FOUND

    async def test_get_file_repository_not_found(self, indexer: RepositoryIndexer) -> None:
        """Test getting file when repository doesn't exist."""
        with pytest.raises(AppError) as exc_info:
            await indexer.get_file(uuid.uuid4(), uuid.uuid4())

        assert exc_info.value.code == RESOURCE_NOT_FOUND
        assert "Repository was not found" in exc_info.value.message

    # get_statistics tests
    async def test_get_statistics_success(
        self, indexer: RepositoryIndexer, repository: Repository, session: AsyncSession
    ) -> None:
        """Test getting statistics for a repository."""
        # Create file records
        files = [
            RepositoryFile(
                repository_id=repository.id,
                relative_path=f"file{i}.py",
                absolute_path=f"/path/file{i}.py",
                file_name=f"file{i}.py",
                extension=".py",
                language="Python",
                size_bytes=100 * (i + 1),
                line_count=10,
                sha256_hash=f"hash{i}",
                last_modified=datetime.now(UTC),
                is_binary=False,
            )
            for i in range(3)
        ]
        session.add_all(files)
        await session.flush()

        stats = await indexer.get_statistics(repository.id)

        assert stats["total_files"] == 3
        assert stats["files_per_language"] == {"Python": 3}
        assert stats["total_bytes"] == 600  # 100 + 200 + 300
        assert stats["binary_file_count"] == 0

    async def test_get_statistics_empty_repository(
        self, indexer: RepositoryIndexer, repository: Repository
    ) -> None:
        """Test getting statistics for repository with no files."""
        stats = await indexer.get_statistics(repository.id)

        assert stats["total_files"] == 0
        assert stats["files_per_language"] == {}
        assert stats["total_bytes"] == 0

    async def test_get_statistics_repository_not_found(
        self, indexer: RepositoryIndexer
    ) -> None:
        """Test getting statistics for non-existent repository."""
        with pytest.raises(AppError) as exc_info:
            await indexer.get_statistics(uuid.uuid4())

        assert exc_info.value.code == RESOURCE_NOT_FOUND

    # Integration tests
    async def test_complete_indexing_workflow(
        self, indexer: RepositoryIndexer, repository: Repository, session: AsyncSession
    ) -> None:
        """Test complete indexing workflow."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)

            # Create test files
            (tmp_path / "main.py").write_text("print('main')\n" * 10)
            (tmp_path / "utils.py").write_text("def util():\n    pass\n")
            (tmp_path / "app.js").write_text("console.log('app');\n")

            subdir = tmp_path / "src"
            subdir.mkdir()
            (subdir / "helper.py").write_text("# helper\n")

            repository.clone_path = str(tmp_path)
            await session.flush()

            # Index repository
            stats = await indexer.index_repository(repository)

            # Verify statistics
            assert stats["total_files"] == 4
            assert stats["files_per_language"]["Python"] == 3
            assert stats["files_per_language"]["JavaScript"] == 1
            assert stats["total_bytes"] > 0

            # Verify files in database
            files = await indexer.list_files(repository.id)
            assert len(files) == 4

            # Verify we can get individual files
            py_file = next(f for f in files if f.file_name == "main.py")
            retrieved = await indexer.get_file(repository.id, py_file.id)
            assert retrieved.file_name == "main.py"

            # Verify statistics from database match
            db_stats = await indexer.get_statistics(repository.id)
            assert db_stats["total_files"] == stats["total_files"]
            assert db_stats["files_per_language"] == stats["files_per_language"]

    async def test_reindexing_updates_files(
        self, indexer: RepositoryIndexer, repository: Repository, session: AsyncSession
    ) -> None:
        """Test that re-indexing properly updates file list."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)

            # First indexing
            (tmp_path / "old.py").write_text("old")
            repository.clone_path = str(tmp_path)
            await session.flush()

            await indexer.index_repository(repository)
            files1 = await indexer.list_files(repository.id)
            assert len(files1) == 1
            assert files1[0].file_name == "old.py"

            # Add new file, remove old file
            (tmp_path / "old.py").unlink()
            (tmp_path / "new.py").write_text("new")

            # Re-index
            await indexer.index_repository(repository)
            files2 = await indexer.list_files(repository.id)

            assert len(files2) == 1
            assert files2[0].file_name == "new.py"
            assert files2[0].id != files1[0].id  # Different record
