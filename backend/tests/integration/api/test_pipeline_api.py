"""Integration tests for Pipeline API endpoints."""

from datetime import datetime

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.db.models.repository import Repository
from app.db.models.repository_file import RepositoryFile
from app.db.models.repository_symbol import RepositorySymbol


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
    await async_session.commit()
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
    await async_session.commit()

    return repository


class TestPipelineAPI:
    """Test suite for Pipeline API endpoints."""

    async def test_analyze_repository_success(
        self, async_client: AsyncClient, repository_with_data: Repository
    ) -> None:
        """Test complete analysis pipeline."""
        response = await async_client.post(
            f"/api/v1/repositories/{repository_with_data.id}/analyze"
        )

        assert response.status_code == 202
        data = response.json()

        assert data["repository_id"] == str(repository_with_data.id)
        assert data["pipeline_complete"] is True

        # Check indexing results
        assert data["indexing"] is not None
        if not data["indexing"].get("skipped"):
            assert "total_files" in data["indexing"]

        # Check graph results
        assert data["graph"] is not None
        assert data["graph"]["nodes_persisted"] > 0
        assert data["graph"]["edges_persisted"] > 0
        assert data["graph"]["statistics"]["total_nodes"] > 0

    async def test_analyze_repository_not_found(
        self, async_client: AsyncClient
    ) -> None:
        """Test analyze with non-existent repository."""
        fake_uuid = "00000000-0000-0000-0000-000000000000"
        response = await async_client.post(f"/api/v1/repositories/{fake_uuid}/analyze")

        assert response.status_code == 404

    async def test_rebuild_graph_success(
        self, async_client: AsyncClient, repository_with_data: Repository
    ) -> None:
        """Test rebuilding graph."""
        # Build initial graph
        await async_client.post(f"/api/v1/repositories/{repository_with_data.id}/analyze")

        # Rebuild graph
        response = await async_client.post(
            f"/api/v1/repositories/{repository_with_data.id}/rebuild-graph"
        )

        assert response.status_code == 202
        data = response.json()

        assert data["nodes_persisted"] > 0
        assert data["edges_persisted"] > 0
        assert data["cleanup_performed"] is True
        assert "statistics" in data

    async def test_rebuild_graph_not_found(
        self, async_client: AsyncClient
    ) -> None:
        """Test rebuild graph with non-existent repository."""
        fake_uuid = "00000000-0000-0000-0000-000000000000"
        response = await async_client.post(f"/api/v1/repositories/{fake_uuid}/rebuild-graph")

        assert response.status_code == 404

    async def test_get_pipeline_status_not_indexed(
        self, async_client: AsyncClient, repository: Repository
    ) -> None:
        """Test pipeline status when repository not indexed."""
        response = await async_client.get(
            f"/api/v1/repositories/{repository.id}/pipeline-status"
        )

        assert response.status_code == 200
        data = response.json()

        assert data["repository_id"] == str(repository.id)
        assert data["indexed"] is False
        assert data["graph_built"] is False
        assert data["graph_stats"] is None

    async def test_get_pipeline_status_indexed_no_graph(
        self, async_client: AsyncClient, repository_with_data: Repository
    ) -> None:
        """Test pipeline status when indexed but no graph."""
        response = await async_client.get(
            f"/api/v1/repositories/{repository_with_data.id}/pipeline-status"
        )

        assert response.status_code == 200
        data = response.json()

        assert data["repository_id"] == str(repository_with_data.id)
        assert data["indexed"] is True
        assert data["graph_built"] is False
        assert data["indexing_stats"]["total_files"] > 0

    async def test_get_pipeline_status_complete(
        self, async_client: AsyncClient, repository_with_data: Repository
    ) -> None:
        """Test pipeline status when fully complete."""
        # Run full analysis
        await async_client.post(f"/api/v1/repositories/{repository_with_data.id}/analyze")

        # Get status
        response = await async_client.get(
            f"/api/v1/repositories/{repository_with_data.id}/pipeline-status"
        )

        assert response.status_code == 200
        data = response.json()

        assert data["repository_id"] == str(repository_with_data.id)
        assert data["indexed"] is True
        assert data["graph_built"] is True
        assert data["indexing_stats"]["total_files"] > 0
        assert data["graph_stats"]["total_nodes"] > 0

    async def test_get_pipeline_status_not_found(
        self, async_client: AsyncClient
    ) -> None:
        """Test pipeline status with non-existent repository."""
        fake_uuid = "00000000-0000-0000-0000-000000000000"
        response = await async_client.get(f"/api/v1/repositories/{fake_uuid}/pipeline-status")

        assert response.status_code == 404

    async def test_analyze_then_rebuild(
        self, async_client: AsyncClient, repository_with_data: Repository
    ) -> None:
        """Test analyze followed by rebuild."""
        # Run analysis
        analyze_response = await async_client.post(
            f"/api/v1/repositories/{repository_with_data.id}/analyze"
        )
        assert analyze_response.status_code == 202
        analyze_data = analyze_response.json()
        initial_nodes = analyze_data["graph"]["nodes_persisted"]

        # Rebuild graph
        rebuild_response = await async_client.post(
            f"/api/v1/repositories/{repository_with_data.id}/rebuild-graph"
        )
        assert rebuild_response.status_code == 202
        rebuild_data = rebuild_response.json()

        # Should have deleted and recreated same number of nodes
        assert rebuild_data["nodes_deleted"] == initial_nodes
        assert rebuild_data["nodes_persisted"] == initial_nodes

    async def test_multiple_analyzes_idempotent(
        self, async_client: AsyncClient, repository_with_data: Repository
    ) -> None:
        """Test multiple analyze calls are idempotent."""
        # First analysis
        response1 = await async_client.post(
            f"/api/v1/repositories/{repository_with_data.id}/analyze"
        )
        data1 = response1.json()
        nodes1 = data1["graph"]["statistics"]["total_nodes"]

        # Second analysis
        response2 = await async_client.post(
            f"/api/v1/repositories/{repository_with_data.id}/analyze"
        )
        data2 = response2.json()
        nodes2 = data2["graph"]["statistics"]["total_nodes"]

        # Should have same number of nodes
        assert nodes1 == nodes2

    async def test_pipeline_integration_workflow(
        self, async_client: AsyncClient, repository_with_data: Repository
    ) -> None:
        """Test complete pipeline workflow integration."""
        repo_id = repository_with_data.id

        # Step 1: Check initial status
        status_response = await async_client.get(
            f"/api/v1/repositories/{repo_id}/pipeline-status"
        )
        assert status_response.status_code == 200
        assert status_response.json()["graph_built"] is False

        # Step 2: Run analysis
        analyze_response = await async_client.post(f"/api/v1/repositories/{repo_id}/analyze")
        assert analyze_response.status_code == 202
        assert analyze_response.json()["pipeline_complete"] is True

        # Step 3: Verify status updated
        status_response = await async_client.get(
            f"/api/v1/repositories/{repo_id}/pipeline-status"
        )
        assert status_response.status_code == 200
        status_data = status_response.json()
        assert status_data["indexed"] is True
        assert status_data["graph_built"] is True

        # Step 4: Query graph
        graph_response = await async_client.get(f"/api/v1/repositories/{repo_id}/graph")
        assert graph_response.status_code == 200
        graph_data = graph_response.json()
        assert len(graph_data["nodes"]) > 0
        assert len(graph_data["edges"]) > 0

        # Step 5: Rebuild graph
        rebuild_response = await async_client.post(
            f"/api/v1/repositories/{repo_id}/rebuild-graph"
        )
        assert rebuild_response.status_code == 202

        # Step 6: Verify graph still accessible
        graph_response2 = await async_client.get(f"/api/v1/repositories/{repo_id}/graph")
        assert graph_response2.status_code == 200

    async def test_analyze_response_structure(
        self, async_client: AsyncClient, repository_with_data: Repository
    ) -> None:
        """Test analyze response has correct structure."""
        response = await async_client.post(
            f"/api/v1/repositories/{repository_with_data.id}/analyze"
        )

        assert response.status_code == 202
        data = response.json()

        # Verify top-level fields
        assert "repository_id" in data
        assert "indexing" in data
        assert "graph" in data
        assert "pipeline_complete" in data

        # Verify graph structure
        graph = data["graph"]
        assert "nodes_persisted" in graph
        assert "edges_persisted" in graph
        assert "nodes_deleted" in graph
        assert "edges_deleted" in graph
        assert "cleanup_performed" in graph
        assert "statistics" in graph

        # Verify statistics structure
        stats = graph["statistics"]
        assert "repository_id" in stats
        assert "total_nodes" in stats
        assert "nodes_by_type" in stats
        assert "total_edges" in stats
        assert "edges_by_type" in stats
        assert "graph_exists" in stats
