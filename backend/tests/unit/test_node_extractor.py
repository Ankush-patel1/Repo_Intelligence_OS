"""Unit tests for NodeExtractor service."""

import json
from datetime import datetime
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.db.models.repository import Repository
from app.db.models.repository_file import RepositoryFile
from app.db.models.repository_symbol import RepositorySymbol
from app.services.graph.node_extractor import NodeExtractor


@pytest.fixture(scope="function")
async def async_session():
    """Create an async database session for testing."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session_maker = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session_maker() as session:
        yield session

    await engine.dispose()


@pytest_asyncio.fixture
async def repository(async_session: AsyncSession) -> Repository:
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
async def repository_file(async_session: AsyncSession, repository: Repository) -> RepositoryFile:
    """Create a test repository file."""
    repo_file = RepositoryFile(
        repository_id=repository.id,
        relative_path="src/main.py",
        absolute_path="/tmp/testrepo/src/main.py",
        file_name="main.py",
        extension=".py",
        language="python",
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
async def repository_symbol(
    async_session: AsyncSession, repository_file: RepositoryFile
) -> RepositorySymbol:
    """Create a test repository symbol."""
    symbol = RepositorySymbol(
        repository_file_id=repository_file.id,
        symbol_name="test_function",
        symbol_type="function",
        parent_symbol=None,
        start_line=10,
        end_line=20,
        start_column=0,
        end_column=10,
        language="python",
        signature="def test_function():",
        symbol_metadata='{"parameters": [], "return_type": "None"}',
    )
    async_session.add(symbol)
    await async_session.flush()
    return symbol


class TestNodeExtractor:
    """Test suite for NodeExtractor."""

    async def test_extract_repository_node(
        self, async_session: AsyncSession, repository: Repository
    ) -> None:
        """Test extracting repository node."""
        extractor = NodeExtractor(session=async_session)
        node = await extractor.extract_repository_node(repository.id)

        assert node is not None
        assert node.repository_id == repository.id
        assert node.repository_file_id is None
        assert node.symbol_id is None
        assert node.node_type == "repository"
        assert node.display_name == repository.full_name
        assert node.language is None

        # Check metadata
        metadata = json.loads(node.node_metadata)
        assert metadata["full_name"] == repository.full_name
        assert metadata["owner"] == repository.owner
        assert metadata["name"] == repository.name

    async def test_extract_repository_node_not_found(
        self, async_session: AsyncSession
    ) -> None:
        """Test extracting non-existent repository node."""
        extractor = NodeExtractor(session=async_session)
        node = await extractor.extract_repository_node(uuid4())

        assert node is None

    async def test_extract_file_nodes(
        self, async_session: AsyncSession, repository: Repository, repository_file: RepositoryFile
    ) -> None:
        """Test extracting file nodes."""
        extractor = NodeExtractor(session=async_session)
        nodes = await extractor.extract_file_nodes(repository.id)

        assert len(nodes) == 1
        node = nodes[0]

        assert node.repository_id == repository.id
        assert node.repository_file_id == repository_file.id
        assert node.symbol_id is None
        assert node.node_type == "file"
        assert node.display_name == repository_file.relative_path
        assert node.language == repository_file.language

        # Check metadata
        metadata = json.loads(node.node_metadata)
        assert metadata["relative_path"] == repository_file.relative_path
        assert metadata["extension"] == repository_file.extension
        assert metadata["size_bytes"] == repository_file.size_bytes

    async def test_extract_symbol_nodes(
        self,
        async_session: AsyncSession,
        repository: Repository,
        repository_file: RepositoryFile,
        repository_symbol: RepositorySymbol,
    ) -> None:
        """Test extracting symbol nodes."""
        extractor = NodeExtractor(session=async_session)
        nodes = await extractor.extract_symbol_nodes(repository.id)

        assert len(nodes) == 1
        node = nodes[0]

        assert node.repository_id == repository.id
        assert node.repository_file_id == repository_symbol.repository_file_id
        assert node.symbol_id == repository_symbol.id
        assert node.node_type == "symbol"
        assert node.display_name == repository_symbol.symbol_name
        assert node.language == repository_symbol.language

        # Check metadata
        metadata = json.loads(node.node_metadata)
        assert metadata["symbol_type"] == repository_symbol.symbol_type
        assert metadata["signature"] == repository_symbol.signature
        assert metadata["start_line"] == repository_symbol.start_line

    async def test_extract_repository_nodes(
        self,
        async_session: AsyncSession,
        repository: Repository,
        repository_file: RepositoryFile,
        repository_symbol: RepositorySymbol,
    ) -> None:
        """Test extracting all nodes for a repository."""
        extractor = NodeExtractor(session=async_session)
        nodes = await extractor.extract_repository_nodes(repository.id)

        # Should have 1 repository + 1 file + 1 symbol = 3 nodes
        assert len(nodes) == 3

        # Check node types
        node_types = {node.node_type for node in nodes}
        assert node_types == {"repository", "file", "symbol"}

        # Verify repository node
        repo_nodes = [n for n in nodes if n.node_type == "repository"]
        assert len(repo_nodes) == 1
        assert repo_nodes[0].repository_id == repository.id

        # Verify file node
        file_nodes = [n for n in nodes if n.node_type == "file"]
        assert len(file_nodes) == 1
        assert file_nodes[0].repository_file_id == repository_file.id

        # Verify symbol node
        symbol_nodes = [n for n in nodes if n.node_type == "symbol"]
        assert len(symbol_nodes) == 1
        assert symbol_nodes[0].symbol_id == repository_symbol.id

    async def test_extract_file_node(
        self, async_session: AsyncSession, repository_file: RepositoryFile
    ) -> None:
        """Test extracting single file node."""
        extractor = NodeExtractor(session=async_session)
        node = await extractor.extract_file_node(repository_file.id)

        assert node is not None
        assert node.repository_file_id == repository_file.id
        assert node.node_type == "file"
        assert node.display_name == repository_file.relative_path

    async def test_extract_symbol_node(
        self, async_session: AsyncSession, repository_symbol: RepositorySymbol
    ) -> None:
        """Test extracting single symbol node."""
        extractor = NodeExtractor(session=async_session)
        node = await extractor.extract_symbol_node(repository_symbol.id)

        assert node is not None
        assert node.symbol_id == repository_symbol.id
        assert node.node_type == "symbol"
        assert node.display_name == repository_symbol.symbol_name

    async def test_extract_nodes_by_type_repository(
        self, async_session: AsyncSession, repository: Repository, repository_file: RepositoryFile
    ) -> None:
        """Test extracting nodes by type - repository."""
        extractor = NodeExtractor(session=async_session)
        nodes = await extractor.extract_nodes_by_type(repository.id, "repository")

        assert len(nodes) == 1
        assert nodes[0].node_type == "repository"

    async def test_extract_nodes_by_type_file(
        self, async_session: AsyncSession, repository: Repository, repository_file: RepositoryFile
    ) -> None:
        """Test extracting nodes by type - file."""
        extractor = NodeExtractor(session=async_session)
        nodes = await extractor.extract_nodes_by_type(repository.id, "file")

        assert len(nodes) == 1
        assert nodes[0].node_type == "file"

    async def test_extract_nodes_by_type_symbol(
        self,
        async_session: AsyncSession,
        repository: Repository,
        repository_file: RepositoryFile,
        repository_symbol: RepositorySymbol,
    ) -> None:
        """Test extracting nodes by type - symbol."""
        extractor = NodeExtractor(session=async_session)
        nodes = await extractor.extract_nodes_by_type(repository.id, "symbol")

        assert len(nodes) == 1
        assert nodes[0].node_type == "symbol"

    async def test_extract_nodes_by_type_invalid(
        self, async_session: AsyncSession, repository: Repository
    ) -> None:
        """Test extracting nodes with invalid type."""
        extractor = NodeExtractor(session=async_session)

        with pytest.raises(ValueError, match="Invalid node_type"):
            await extractor.extract_nodes_by_type(repository.id, "invalid_type")

    async def test_get_node_statistics(
        self,
        async_session: AsyncSession,
        repository: Repository,
        repository_file: RepositoryFile,
        repository_symbol: RepositorySymbol,
    ) -> None:
        """Test getting node statistics."""
        extractor = NodeExtractor(session=async_session)
        stats = await extractor.get_node_statistics(repository.id)

        assert stats["repository_nodes"] == 1
        assert stats["file_nodes"] == 1
        assert stats["symbol_nodes"] == 1
        assert stats["total_nodes"] == 3
        assert "python" in stats["files_by_language"]
        assert "python" in stats["symbols_by_language"]
        assert "function" in stats["symbols_by_type"]

    async def test_extract_multiple_files(
        self, async_session: AsyncSession, repository: Repository
    ) -> None:
        """Test extracting nodes from multiple files."""
        # Create multiple files
        files = []
        for i in range(3):
            repo_file = RepositoryFile(
                repository_id=repository.id,
                relative_path=f"src/file{i}.py",
                absolute_path=f"/tmp/testrepo/src/file{i}.py",
                file_name=f"file{i}.py",
                extension=".py",
                language="python",
                size_bytes=1024,
                line_count=50,
                sha256_hash=f"hash{i}",
                last_modified=datetime.utcnow(),
                is_binary=False,
            )
            async_session.add(repo_file)
            files.append(repo_file)
        await async_session.flush()

        extractor = NodeExtractor(session=async_session)
        nodes = await extractor.extract_file_nodes(repository.id)

        assert len(nodes) == 3
        assert all(n.node_type == "file" for n in nodes)

    async def test_extract_parent_child_symbols(
        self, async_session: AsyncSession, repository: Repository, repository_file: RepositoryFile
    ) -> None:
        """Test extracting parent-child symbol hierarchy."""
        # Create parent class
        parent_symbol = RepositorySymbol(
            repository_file_id=repository_file.id,
            symbol_name="TestClass",
            symbol_type="class",
            parent_symbol=None,
            start_line=10,
            end_line=30,
            language="python",
            signature="class TestClass:",
        )
        async_session.add(parent_symbol)
        await async_session.flush()

        # Create child method
        child_symbol = RepositorySymbol(
            repository_file_id=repository_file.id,
            symbol_name="test_method",
            symbol_type="method",
            parent_symbol=parent_symbol.id,
            start_line=15,
            end_line=20,
            language="python",
            signature="def test_method(self):",
        )
        async_session.add(child_symbol)
        await async_session.flush()

        extractor = NodeExtractor(session=async_session)
        nodes = await extractor.extract_symbol_nodes(repository.id)

        assert len(nodes) == 2

        # Verify parent node
        parent_node = next(n for n in nodes if n.symbol_id == parent_symbol.id)
        parent_metadata = json.loads(parent_node.node_metadata)
        assert parent_metadata["parent_symbol_id"] is None

        # Verify child node
        child_node = next(n for n in nodes if n.symbol_id == child_symbol.id)
        child_metadata = json.loads(child_node.node_metadata)
        assert child_metadata["parent_symbol_id"] == str(parent_symbol.id)
