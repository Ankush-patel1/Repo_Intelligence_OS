"""Integration tests for RepositorySymbol persistence."""

import uuid
from datetime import datetime
from pathlib import Path

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.db.models.repository import Repository
from app.db.models.repository_file import RepositoryFile
from app.db.models.repository_symbol import RepositorySymbol
from app.services.indexing.symbol_extractor import SymbolExtractor


@pytest.fixture(scope="function")
async def async_session():
    """Create an async database session for testing."""
    # Use in-memory SQLite for testing
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
    )

    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Create session
    async_session_maker = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session_maker() as session:
        yield session

    await engine.dispose()


@pytest.fixture
def sample_python_file() -> Path:
    """Get path to sample Python file."""
    return Path("tests/fixtures/samples/sample.py")


@pytest.fixture
def sample_js_file() -> Path:
    """Get path to sample JavaScript file."""
    return Path("tests/fixtures/samples/sample.js")


@pytest.fixture
def sample_ts_file() -> Path:
    """Get path to sample TypeScript file."""
    return Path("tests/fixtures/samples/sample.ts")


class TestSymbolPersistence:
    """Test suite for RepositorySymbol persistence."""

    @pytest_asyncio.fixture
    async def repository(self, async_session: AsyncSession) -> Repository:
        """Create a test repository."""
        repo = Repository(
            owner="testuser",
            name="testrepo",
            full_name="testuser/testrepo",
            branch="main",
            clone_path="/tmp/testrepo",
            private=False,
            default_branch="main",
        )
        async_session.add(repo)
        await async_session.flush()
        return repo

    @pytest_asyncio.fixture
    async def repository_file_python(
        self, async_session: AsyncSession, repository: Repository, sample_python_file: Path
    ) -> RepositoryFile:
        """Create a test Python repository file."""
        repo_file = RepositoryFile(
            repository_id=repository.id,
            relative_path="sample.py",
            absolute_path=str(sample_python_file.absolute()),
            file_name="sample.py",
            extension=".py",
            language="Python",
            size_bytes=1024,
            line_count=50,
            sha256_hash="abc123",
            last_modified=datetime.utcnow(),
            is_binary=False,
        )
        async_session.add(repo_file)
        await async_session.flush()
        return repo_file

    @pytest_asyncio.fixture
    async def repository_file_js(
        self, async_session: AsyncSession, repository: Repository, sample_js_file: Path
    ) -> RepositoryFile:
        """Create a test JavaScript repository file."""
        repo_file = RepositoryFile(
            repository_id=repository.id,
            relative_path="sample.js",
            absolute_path=str(sample_js_file.absolute()),
            file_name="sample.js",
            extension=".js",
            language="JavaScript",
            size_bytes=1024,
            line_count=50,
            sha256_hash="def456",
            last_modified=datetime.utcnow(),
            is_binary=False,
        )
        async_session.add(repo_file)
        await async_session.flush()
        return repo_file

    async def test_create_symbol(self, async_session: AsyncSession, repository_file_python: RepositoryFile) -> None:
        """Test creating a single RepositorySymbol."""
        symbol = RepositorySymbol(
            repository_file_id=repository_file_python.id,
            symbol_name="test_function",
            symbol_type="function",
            parent_symbol=None,
            start_line=1,
            end_line=5,
            start_column=0,
            end_column=10,
            language="Python",
            signature="def test_function():",
            symbol_metadata=None,
            created_at=datetime.utcnow(),
        )

        async_session.add(symbol)
        await async_session.flush()

        assert symbol.id is not None
        assert symbol.symbol_name == "test_function"

    async def test_query_symbols_by_file(
        self, async_session: AsyncSession, repository_file_python: RepositoryFile
    ) -> None:
        """Test querying symbols by file."""
        # Create multiple symbols
        symbols = [
            RepositorySymbol(
                repository_file_id=repository_file_python.id,
                symbol_name=f"func_{i}",
                symbol_type="function",
                parent_symbol=None,
                start_line=i * 10,
                end_line=i * 10 + 5,
                language="Python",
                signature=f"def func_{i}():",
                created_at=datetime.utcnow(),
            )
            for i in range(3)
        ]

        async_session.add_all(symbols)
        await async_session.flush()

        # Query symbols
        result = await async_session.execute(
            select(RepositorySymbol).where(
                RepositorySymbol.repository_file_id == repository_file_python.id
            )
        )
        queried_symbols = result.scalars().all()

        assert len(queried_symbols) == 3
        assert all(s.repository_file_id == repository_file_python.id for s in queried_symbols)

    async def test_parent_child_relationship(
        self, async_session: AsyncSession, repository_file_python: RepositoryFile
    ) -> None:
        """Test parent-child relationship between class and method."""
        # Create parent class
        class_symbol = RepositorySymbol(
            repository_file_id=repository_file_python.id,
            symbol_name="TestClass",
            symbol_type="class",
            parent_symbol=None,
            start_line=10,
            end_line=30,
            language="Python",
            signature="class TestClass:",
            created_at=datetime.utcnow(),
        )
        async_session.add(class_symbol)
        await async_session.flush()

        # Create child method
        method_symbol = RepositorySymbol(
            repository_file_id=repository_file_python.id,
            symbol_name="test_method",
            symbol_type="method",
            parent_symbol=class_symbol.id,
            start_line=15,
            end_line=20,
            language="Python",
            signature="def test_method(self):",
            created_at=datetime.utcnow(),
        )
        async_session.add(method_symbol)
        await async_session.flush()

        # Verify relationship
        assert method_symbol.parent_symbol == class_symbol.id

        # Query using relationship
        result = await async_session.execute(
            select(RepositorySymbol).where(RepositorySymbol.parent_symbol == class_symbol.id)
        )
        children = result.scalars().all()

        assert len(children) == 1
        assert children[0].symbol_name == "test_method"

    async def test_symbol_extractor_integration_python(
        self, async_session: AsyncSession, repository_file_python: RepositoryFile
    ) -> None:
        """Test SymbolExtractor with Python file."""
        extractor = SymbolExtractor(async_session)
        result = await extractor.extract_and_store_symbols(repository_file_python)

        assert result["success"] is True
        assert result["language"] == "Python"
        assert result["symbols_extracted"] > 0

        # Verify symbols were stored
        db_result = await async_session.execute(
            select(RepositorySymbol).where(
                RepositorySymbol.repository_file_id == repository_file_python.id
            )
        )
        symbols = db_result.scalars().all()

        assert len(symbols) == result["symbols_extracted"]
        assert any(s.symbol_type == "import" for s in symbols)
        assert any(s.symbol_type == "function" for s in symbols)
        assert any(s.symbol_type == "class" for s in symbols)
        assert any(s.symbol_type == "method" for s in symbols)

    async def test_symbol_extractor_integration_javascript(
        self, async_session: AsyncSession, repository_file_js: RepositoryFile
    ) -> None:
        """Test SymbolExtractor with JavaScript file."""
        extractor = SymbolExtractor(async_session)
        result = await extractor.extract_and_store_symbols(repository_file_js)

        assert result["success"] is True
        assert result["language"] == "JavaScript"
        assert result["symbols_extracted"] > 0

        # Verify symbols were stored
        db_result = await async_session.execute(
            select(RepositorySymbol).where(
                RepositorySymbol.repository_file_id == repository_file_js.id
            )
        )
        symbols = db_result.scalars().all()

        assert len(symbols) > 0
        assert any(s.symbol_type == "import" for s in symbols)
        assert any(s.symbol_type == "function" for s in symbols)
        assert any(s.symbol_type == "class" for s in symbols)

    async def test_symbol_extractor_class_method_hierarchy(
        self, async_session: AsyncSession, repository_file_python: RepositoryFile
    ) -> None:
        """Test that class-method hierarchy is preserved."""
        extractor = SymbolExtractor(async_session)
        await extractor.extract_and_store_symbols(repository_file_python)

        # Get class symbols
        class_result = await async_session.execute(
            select(RepositorySymbol).where(
                RepositorySymbol.repository_file_id == repository_file_python.id,
                RepositorySymbol.symbol_type == "class",
            )
        )
        classes = class_result.scalars().all()

        assert len(classes) > 0

        # Get methods for the first class
        sample_class = classes[0]
        method_result = await async_session.execute(
            select(RepositorySymbol).where(
                RepositorySymbol.parent_symbol == sample_class.id,
                RepositorySymbol.symbol_type == "method",
            )
        )
        methods = method_result.scalars().all()

        assert len(methods) > 0
        assert all(m.parent_symbol == sample_class.id for m in methods)

    async def test_symbol_extractor_skip_binary_file(
        self, async_session: AsyncSession, repository_file_python: RepositoryFile
    ) -> None:
        """Test that binary files are skipped."""
        # Mark file as binary
        repository_file_python.is_binary = True
        await async_session.flush()

        extractor = SymbolExtractor(async_session)
        result = await extractor.extract_and_store_symbols(repository_file_python)

        assert result["success"] is False
        assert result["reason"] == "binary_file"
        assert result["symbols_extracted"] == 0

    async def test_symbol_extractor_unsupported_language(
        self, async_session: AsyncSession, repository_file_python: RepositoryFile
    ) -> None:
        """Test that unsupported languages are handled correctly."""
        # Change to unsupported language that has no real parser
        repository_file_python.language = "Fortran"
        repository_file_python.extension = ".f90"
        repository_file_python.absolute_path = "/nonexistent/file.f90"
        await async_session.flush()

        extractor = SymbolExtractor(async_session)
        result = await extractor.extract_and_store_symbols(repository_file_python)

        # Should either skip as unsupported or fail gracefully
        assert result["success"] is False or result["symbols_extracted"] == 0

    async def test_cascade_delete_symbols_with_file(
        self, async_session: AsyncSession, repository_file_python: RepositoryFile
    ) -> None:
        """Test that symbols are deleted when file is deleted."""
        # Create symbols
        extractor = SymbolExtractor(async_session)
        await extractor.extract_and_store_symbols(repository_file_python)

        # Verify symbols exist
        result = await async_session.execute(
            select(RepositorySymbol).where(
                RepositorySymbol.repository_file_id == repository_file_python.id
            )
        )
        symbols_before = result.scalars().all()
        assert len(symbols_before) > 0

        # Delete file
        await async_session.delete(repository_file_python)
        await async_session.flush()

        # Verify symbols are deleted (cascade)
        result = await async_session.execute(
            select(RepositorySymbol).where(
                RepositorySymbol.repository_file_id == repository_file_python.id
            )
        )
        symbols_after = result.scalars().all()
        assert len(symbols_after) == 0

    async def test_query_symbols_by_type(
        self, async_session: AsyncSession, repository_file_python: RepositoryFile
    ) -> None:
        """Test querying symbols by type."""
        extractor = SymbolExtractor(async_session)
        await extractor.extract_and_store_symbols(repository_file_python)

        # Query only functions
        result = await async_session.execute(
            select(RepositorySymbol).where(
                RepositorySymbol.repository_file_id == repository_file_python.id,
                RepositorySymbol.symbol_type == "function",
            )
        )
        functions = result.scalars().all()

        assert len(functions) > 0
        assert all(s.symbol_type == "function" for s in functions)

    async def test_query_symbols_by_language(
        self, async_session: AsyncSession, repository_file_python: RepositoryFile
    ) -> None:
        """Test querying symbols by language."""
        extractor = SymbolExtractor(async_session)
        await extractor.extract_and_store_symbols(repository_file_python)

        # Query by language
        result = await async_session.execute(
            select(RepositorySymbol).where(RepositorySymbol.language == "Python")
        )
        python_symbols = result.scalars().all()

        assert len(python_symbols) > 0
        assert all(s.language == "Python" for s in python_symbols)
