"""Integration tests for Graph API endpoints."""

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
    """Create a test repository with file and symbol data."""
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


class TestGraphAPI:
    """Test suite for Graph API endpoints."""

    async def test_build_graph_success(
        self, async_client: AsyncClient, repository_with_data: Repository
    ) -> None:
        """Test building graph successfully."""
        response = await async_client.post(
            f"/api/v1/repositories/{repository_with_data.id}/graph"
        )

        assert response.status_code == 201
        data = response.json()

        assert data["repository_id"] == str(repository_with_data.id)
        assert data["nodes_persisted"] > 0
        assert data["edges_persisted"] > 0
        assert data["cleanup_performed"] is True
        assert "statistics" in data
        assert data["statistics"]["total_nodes"] > 0

    async def test_build_graph_repository_not_found(
        self, async_client: AsyncClient
    ) -> None:
        """Test building graph for non-existent repository."""
        fake_uuid = "00000000-0000-0000-0000-000000000000"
        response = await async_client.post(f"/api/v1/repositories/{fake_uuid}/graph")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    async def test_build_graph_no_data(
        self, async_client: AsyncClient, repository: Repository
    ) -> None:
        """Test building graph with no indexed data."""
        response = await async_client.post(f"/api/v1/repositories/{repository.id}/graph")

        assert response.status_code == 400
        assert "no nodes found" in response.json()["detail"].lower()

    async def test_get_graph_success(
        self, async_client: AsyncClient, repository_with_data: Repository
    ) -> None:
        """Test retrieving complete graph."""
        # Build graph first
        await async_client.post(f"/api/v1/repositories/{repository_with_data.id}/graph")

        # Get graph
        response = await async_client.get(
            f"/api/v1/repositories/{repository_with_data.id}/graph"
        )

        assert response.status_code == 200
        data = response.json()

        assert data["repository_id"] == str(repository_with_data.id)
        assert len(data["nodes"]) > 0
        assert len(data["edges"]) > 0
        assert "statistics" in data

        # Verify node structure
        node = data["nodes"][0]
        assert "id" in node
        assert "node_type" in node
        assert "display_name" in node
        assert "metadata" in node

        # Verify edge structure
        if len(data["edges"]) > 0:
            edge = data["edges"][0]
            assert "id" in edge
            assert "source_node_id" in edge
            assert "target_node_id" in edge
            assert "relationship_type" in edge

    async def test_get_graph_not_found(
        self, async_client: AsyncClient, repository_with_data: Repository
    ) -> None:
        """Test retrieving graph that doesn't exist."""
        response = await async_client.get(
            f"/api/v1/repositories/{repository_with_data.id}/graph"
        )

        assert response.status_code == 404
        assert "graph not found" in response.json()["detail"].lower()

    async def test_get_graph_nodes_all(
        self, async_client: AsyncClient, repository_with_data: Repository
    ) -> None:
        """Test retrieving all graph nodes."""
        # Build graph first
        await async_client.post(f"/api/v1/repositories/{repository_with_data.id}/graph")

        # Get nodes
        response = await async_client.get(
            f"/api/v1/repositories/{repository_with_data.id}/graph/nodes"
        )

        assert response.status_code == 200
        data = response.json()

        assert len(data) > 0
        assert any(node["node_type"] == "repository" for node in data)
        assert any(node["node_type"] == "file" for node in data)
        assert any(node["node_type"] == "symbol" for node in data)

    async def test_get_graph_nodes_filtered_by_type(
        self, async_client: AsyncClient, repository_with_data: Repository
    ) -> None:
        """Test retrieving graph nodes filtered by type."""
        # Build graph first
        await async_client.post(f"/api/v1/repositories/{repository_with_data.id}/graph")

        # Get only symbol nodes
        response = await async_client.get(
            f"/api/v1/repositories/{repository_with_data.id}/graph/nodes",
            params={"node_type": "symbol"},
        )

        assert response.status_code == 200
        data = response.json()

        assert len(data) > 0
        assert all(node["node_type"] == "symbol" for node in data)

    async def test_get_graph_nodes_filtered_by_language(
        self, async_client: AsyncClient, repository_with_data: Repository
    ) -> None:
        """Test retrieving graph nodes filtered by language."""
        # Build graph first
        await async_client.post(f"/api/v1/repositories/{repository_with_data.id}/graph")

        # Get only Python nodes
        response = await async_client.get(
            f"/api/v1/repositories/{repository_with_data.id}/graph/nodes",
            params={"language": "python"},
        )

        assert response.status_code == 200
        data = response.json()

        assert len(data) > 0
        # Note: repository node has no language, so check only file/symbol nodes
        language_nodes = [n for n in data if n["language"] is not None]
        assert all(node["language"] == "python" for node in language_nodes)

    async def test_get_graph_edges_all(
        self, async_client: AsyncClient, repository_with_data: Repository
    ) -> None:
        """Test retrieving all graph edges."""
        # Build graph first
        await async_client.post(f"/api/v1/repositories/{repository_with_data.id}/graph")

        # Get edges
        response = await async_client.get(
            f"/api/v1/repositories/{repository_with_data.id}/graph/edges"
        )

        assert response.status_code == 200
        data = response.json()

        assert len(data) > 0
        # Should have at least CONTAINS edges
        assert any(edge["relationship_type"] == "CONTAINS" for edge in data)

    async def test_get_graph_edges_filtered_by_type(
        self, async_client: AsyncClient, repository_with_data: Repository
    ) -> None:
        """Test retrieving graph edges filtered by relationship type."""
        # Build graph first
        await async_client.post(f"/api/v1/repositories/{repository_with_data.id}/graph")

        # Get only CONTAINS edges
        response = await async_client.get(
            f"/api/v1/repositories/{repository_with_data.id}/graph/edges",
            params={"relationship_type": "CONTAINS"},
        )

        assert response.status_code == 200
        data = response.json()

        assert len(data) > 0
        assert all(edge["relationship_type"] == "CONTAINS" for edge in data)

    async def test_get_single_node(
        self, async_client: AsyncClient, repository_with_data: Repository
    ) -> None:
        """Test retrieving a single node."""
        # Build graph first
        build_response = await async_client.post(
            f"/api/v1/repositories/{repository_with_data.id}/graph"
        )

        # Get all nodes to find a valid node ID
        nodes_response = await async_client.get(
            f"/api/v1/repositories/{repository_with_data.id}/graph/nodes"
        )
        nodes = nodes_response.json()
        node_id = nodes[0]["id"]

        # Get single node
        response = await async_client.get(
            f"/api/v1/repositories/{repository_with_data.id}/graph/node/{node_id}"
        )

        assert response.status_code == 200
        data = response.json()

        assert data["id"] == node_id
        assert "node_type" in data
        assert "display_name" in data

    async def test_get_single_node_not_found(
        self, async_client: AsyncClient, repository_with_data: Repository
    ) -> None:
        """Test retrieving non-existent node."""
        # Build graph first
        await async_client.post(f"/api/v1/repositories/{repository_with_data.id}/graph")

        # Try to get non-existent node
        fake_uuid = "00000000-0000-0000-0000-000000000000"
        response = await async_client.get(
            f"/api/v1/repositories/{repository_with_data.id}/graph/node/{fake_uuid}"
        )

        assert response.status_code == 404

    async def test_rebuild_graph(
        self, async_client: AsyncClient, repository_with_data: Repository
    ) -> None:
        """Test rebuilding graph replaces old data."""
        # Build graph first time
        response1 = await async_client.post(
            f"/api/v1/repositories/{repository_with_data.id}/graph"
        )
        assert response1.status_code == 201
        data1 = response1.json()
        nodes_persisted_1 = data1["nodes_persisted"]

        # Build graph second time (rebuild)
        response2 = await async_client.post(
            f"/api/v1/repositories/{repository_with_data.id}/graph"
        )
        assert response2.status_code == 201
        data2 = response2.json()

        # Should have deleted old nodes
        assert data2["nodes_deleted"] == nodes_persisted_1
        assert data2["cleanup_performed"] is True

        # Final node count should be same as first build
        assert data2["statistics"]["total_nodes"] == nodes_persisted_1

    async def test_graph_metadata_parsing(
        self, async_client: AsyncClient, repository_with_data: Repository
    ) -> None:
        """Test that node and edge metadata is properly parsed to JSON."""
        # Build graph
        await async_client.post(f"/api/v1/repositories/{repository_with_data.id}/graph")

        # Get graph
        response = await async_client.get(
            f"/api/v1/repositories/{repository_with_data.id}/graph"
        )

        assert response.status_code == 200
        data = response.json()

        # Check node metadata is dict
        for node in data["nodes"]:
            if node["metadata"] is not None:
                assert isinstance(node["metadata"], dict)

        # Check edge metadata is dict
        for edge in data["edges"]:
            if edge["metadata"] is not None:
                assert isinstance(edge["metadata"], dict)
