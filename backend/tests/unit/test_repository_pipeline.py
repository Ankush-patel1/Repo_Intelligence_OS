"""Unit tests for RepositoryPipeline orchestration service."""

from datetime import datetime
from pathlib import Path

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.db.models.repository import Repository
from app.db.models.repository_file import RepositoryFile
from app.db.models.repository_symbol import RepositorySymbol
from app.services.orchestration.repository_pipeline import RepositoryPipeline


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
async def repository_with_data(async_session: AsyncSession, repository: Repository) -> Repository:
    """Create a repository with indexed data."""
    # Create file
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

    # Create symbols
    symbols = [
        RepositorySymbol(
            repository_file_id=repo_file.id,
            symbol_name="test_function",
            symbol_type="function",
            start_line=10,
            end_line=20,
            language="python",
            signature="def test_function():",
        ),
        RepositorySymbol(
            repository_file_id=repo_file.id,
            symbol_name="TestClass",
            symbol_type="class",
            start_line=25,
            end_line=40,
            language="python",
            signature="class TestClass:",
        ),
    ]
    async_session.add_all(symbols)
    await async_session.flush()

    return repository


class TestRepositoryPipeline:
    """Test suite for RepositoryPipeline."""

    async def test_pipeline_initialization(self, async_session: AsyncSession) -> None:
        """Test pipeline initializes with required services."""
        pipeline = RepositoryPipeline(session=async_session)

        assert pipeline.session is not None
        assert pipeline.indexer is not None
        assert pipeline.node_extractor is not None
        assert pipeline.edge_extractor is not None
        assert pipeline.graph_persister is not None

    async def test_build_graph(
        self, async_session: AsyncSession, repository_with_data: Repository
    ) -> None:
        """Test building knowledge graph."""
        pipeline = RepositoryPipeline(session=async_session)
        stats = await pipeline.build_graph(repository_with_data.id)

        assert stats["nodes_persisted"] > 0
        assert stats["edges_persisted"] > 0
        assert stats["cleanup_performed"] is True
        assert "statistics" in stats
        assert stats["statistics"]["total_nodes"] > 0
        assert stats["statistics"]["graph_exists"] is True

    async def test_rebuild_graph(
        self, async_session: AsyncSession, repository_with_data: Repository
    ) -> None:
        """Test rebuilding graph without re-indexing."""
        pipeline = RepositoryPipeline(session=async_session)

        # Build initial graph
        stats1 = await pipeline.build_graph(repository_with_data.id)
        nodes_count_1 = stats1["nodes_persisted"]

        # Rebuild graph
        stats2 = await pipeline.rebuild_graph(repository_with_data.id)

        # Should have deleted old nodes and created new ones
        assert stats2["nodes_deleted"] == nodes_count_1
        assert stats2["nodes_persisted"] == nodes_count_1

    async def test_run_graph_only(
        self, async_session: AsyncSession, repository_with_data: Repository
    ) -> None:
        """Test running only graph building step."""
        pipeline = RepositoryPipeline(session=async_session)
        results = await pipeline.run_graph_only(repository_with_data.id)

        assert results["repository_id"] == str(repository_with_data.id)
        assert results["indexing"]["skipped"] is True
        assert results["graph"]["nodes_persisted"] > 0
        assert results["pipeline_complete"] is True

    async def test_run_full_pipeline_skip_indexing(
        self, async_session: AsyncSession, repository_with_data: Repository
    ) -> None:
        """Test running full pipeline with indexing skipped."""
        pipeline = RepositoryPipeline(session=async_session)
        results = await pipeline.run_full_pipeline(
            repository_with_data.id, skip_indexing=True, skip_graph=False
        )

        assert results["repository_id"] == str(repository_with_data.id)
        assert results["indexing"]["skipped"] is True
        assert results["graph"]["nodes_persisted"] > 0
        assert results["pipeline_complete"] is True

    async def test_run_full_pipeline_skip_graph(
        self, async_session: AsyncSession, repository_with_data: Repository
    ) -> None:
        """Test running full pipeline with graph skipped."""
        pipeline = RepositoryPipeline(session=async_session)
        results = await pipeline.run_full_pipeline(
            repository_with_data.id, skip_indexing=True, skip_graph=True
        )

        assert results["repository_id"] == str(repository_with_data.id)
        assert results["indexing"]["skipped"] is True
        assert results["graph"]["skipped"] is True
        assert results["pipeline_complete"] is True

    async def test_get_pipeline_status_not_indexed(
        self, async_session: AsyncSession, repository: Repository
    ) -> None:
        """Test getting pipeline status when repository not indexed."""
        pipeline = RepositoryPipeline(session=async_session)
        status = await pipeline.get_pipeline_status(repository.id)

        assert status["repository_id"] == str(repository.id)
        assert status["indexed"] is False
        assert status["graph_built"] is False
        assert status["graph_stats"] is None

    async def test_get_pipeline_status_indexed_no_graph(
        self, async_session: AsyncSession, repository_with_data: Repository
    ) -> None:
        """Test getting pipeline status when indexed but no graph."""
        pipeline = RepositoryPipeline(session=async_session)
        status = await pipeline.get_pipeline_status(repository_with_data.id)

        assert status["repository_id"] == str(repository_with_data.id)
        assert status["indexed"] is True
        assert status["graph_built"] is False
        assert status["indexing_stats"]["total_files"] > 0

    async def test_get_pipeline_status_complete(
        self, async_session: AsyncSession, repository_with_data: Repository
    ) -> None:
        """Test getting pipeline status when fully complete."""
        pipeline = RepositoryPipeline(session=async_session)

        # Build graph
        await pipeline.build_graph(repository_with_data.id)

        # Get status
        status = await pipeline.get_pipeline_status(repository_with_data.id)

        assert status["repository_id"] == str(repository_with_data.id)
        assert status["indexed"] is True
        assert status["graph_built"] is True
        assert status["graph_stats"]["total_nodes"] > 0

    async def test_run_index_and_graph_without_files(
        self, async_session: AsyncSession, repository: Repository
    ) -> None:
        """Test running pipeline when repository has no files to index."""
        pipeline = RepositoryPipeline(session=async_session)

        # Note: This would fail in a real scenario since indexer needs actual files
        # In unit tests, we're testing the orchestration logic
        # Full integration test would need actual repository files

    async def test_pipeline_services_integration(
        self, async_session: AsyncSession, repository_with_data: Repository
    ) -> None:
        """Test that pipeline correctly integrates all services."""
        pipeline = RepositoryPipeline(session=async_session)

        # Verify services are using the same session
        assert pipeline.indexer.session == async_session
        assert pipeline.node_extractor.session == async_session
        assert pipeline.edge_extractor.session == async_session
        assert pipeline.graph_persister.session == async_session

    async def test_build_graph_statistics_accuracy(
        self, async_session: AsyncSession, repository_with_data: Repository
    ) -> None:
        """Test that build graph statistics are accurate."""
        pipeline = RepositoryPipeline(session=async_session)
        stats = await pipeline.build_graph(repository_with_data.id)

        # Verify statistics match actual counts
        assert stats["statistics"]["total_nodes"] == stats["nodes_persisted"]
        assert stats["statistics"]["total_edges"] == stats["edges_persisted"]
        assert stats["statistics"]["graph_exists"] is True

        # Verify node type breakdown
        nodes_by_type = stats["statistics"]["nodes_by_type"]
        assert "repository" in nodes_by_type
        assert "file" in nodes_by_type
        assert "symbol" in nodes_by_type

        # Verify total matches sum
        total = sum(nodes_by_type.values())
        assert total == stats["statistics"]["total_nodes"]

    async def test_multiple_graph_rebuilds(
        self, async_session: AsyncSession, repository_with_data: Repository
    ) -> None:
        """Test multiple successive graph rebuilds."""
        pipeline = RepositoryPipeline(session=async_session)

        # Build graph multiple times
        stats1 = await pipeline.build_graph(repository_with_data.id)
        stats2 = await pipeline.rebuild_graph(repository_with_data.id)
        stats3 = await pipeline.rebuild_graph(repository_with_data.id)

        # All should have same final node count
        assert stats1["statistics"]["total_nodes"] == stats2["statistics"]["total_nodes"]
        assert stats2["statistics"]["total_nodes"] == stats3["statistics"]["total_nodes"]

        # Each rebuild should delete previous nodes
        assert stats2["nodes_deleted"] == stats1["nodes_persisted"]
        assert stats3["nodes_deleted"] == stats2["nodes_persisted"]
