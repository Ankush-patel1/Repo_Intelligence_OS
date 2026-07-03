"""Unit tests for GraphPersister service."""

import json
from datetime import datetime

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.db.models.repository import Repository
from app.db.models.repository_edge import RepositoryEdge
from app.db.models.repository_file import RepositoryFile
from app.db.models.repository_node import RepositoryNode
from app.db.models.repository_symbol import RepositorySymbol
from app.services.graph import EdgeExtractor, GraphPersister, NodeExtractor


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
        language="python",
        signature="def test_function():",
    )
    async_session.add(symbol)
    await async_session.flush()
    return symbol


class TestGraphPersister:
    """Test suite for GraphPersister."""

    async def test_persist_nodes(
        self,
        async_session: AsyncSession,
        repository: Repository,
        repository_file: RepositoryFile,
        repository_symbol: RepositorySymbol,
    ) -> None:
        """Test persisting nodes to database."""
        # Extract nodes
        node_extractor = NodeExtractor(session=async_session)
        nodes = await node_extractor.extract_repository_nodes(repository.id)

        # Persist nodes
        persister = GraphPersister(session=async_session)
        count = await persister.persist_nodes(nodes)

        assert count == len(nodes)

        # Verify nodes in database
        result = await async_session.execute(
            select(RepositoryNode).where(RepositoryNode.repository_id == repository.id)
        )
        db_nodes = list(result.scalars().all())

        assert len(db_nodes) == count
        assert any(n.node_type == "repository" for n in db_nodes)
        assert any(n.node_type == "file" for n in db_nodes)
        assert any(n.node_type == "symbol" for n in db_nodes)

    async def test_persist_edges(
        self,
        async_session: AsyncSession,
        repository: Repository,
        repository_file: RepositoryFile,
        repository_symbol: RepositorySymbol,
    ) -> None:
        """Test persisting edges to database."""
        # Extract and persist nodes first
        node_extractor = NodeExtractor(session=async_session)
        nodes = await node_extractor.extract_repository_nodes(repository.id)

        persister = GraphPersister(session=async_session)
        await persister.persist_nodes(nodes)
        await async_session.flush()

        # Extract edges
        edge_extractor = EdgeExtractor(session=async_session)
        edges = await edge_extractor.extract_all_edges(repository.id, nodes)

        # Persist edges
        count = await persister.persist_edges(edges)

        assert count == len(edges)

        # Verify edges in database
        result = await async_session.execute(select(RepositoryEdge))
        db_edges = list(result.scalars().all())

        assert len(db_edges) == count

    async def test_persist_graph(
        self,
        async_session: AsyncSession,
        repository: Repository,
        repository_file: RepositoryFile,
        repository_symbol: RepositorySymbol,
    ) -> None:
        """Test persisting complete graph."""
        # Extract nodes
        node_extractor = NodeExtractor(session=async_session)
        nodes = await node_extractor.extract_repository_nodes(repository.id)

        # Persist nodes first
        persister = GraphPersister(session=async_session)
        await persister.persist_nodes(nodes)
        await async_session.flush()  # Nodes now have IDs

        # Now extract edges (nodes have IDs)
        edge_extractor = EdgeExtractor(session=async_session)
        edges = await edge_extractor.extract_all_edges(repository.id, nodes)

        # Persist edges
        await persister.persist_edges(edges)
        await async_session.flush()

        # Get stats for verification
        stats = await persister.get_graph_statistics(repository.id)

        assert stats["repository_id"] == str(repository.id)
        assert stats["total_nodes"] == len(nodes)
        assert stats["total_edges"] == len(edges)

        # Verify in database
        node_result = await async_session.execute(
            select(RepositoryNode).where(RepositoryNode.repository_id == repository.id)
        )
        db_nodes = list(node_result.scalars().all())
        assert len(db_nodes) == len(nodes)

    async def test_persist_graph_cleanup(
        self,
        async_session: AsyncSession,
        repository: Repository,
        repository_file: RepositoryFile,
        repository_symbol: RepositorySymbol,
    ) -> None:
        """Test graph cleanup during persistence."""
        # Extract and persist initial graph
        node_extractor = NodeExtractor(session=async_session)
        nodes = await node_extractor.extract_repository_nodes(repository.id)

        persister = GraphPersister(session=async_session)
        await persister.persist_nodes(nodes)
        await async_session.flush()  # Nodes now have IDs

        edge_extractor = EdgeExtractor(session=async_session)
        edges = await edge_extractor.extract_all_edges(repository.id, nodes)

        await persister.persist_edges(edges)
        await async_session.flush()

        # Get initial count
        result = await async_session.execute(
            select(RepositoryNode).where(RepositoryNode.repository_id == repository.id)
        )
        initial_count = len(list(result.scalars().all()))

        # Delete old graph
        deleted_count = await persister.delete_repository_graph(repository.id)
        await async_session.flush()

        assert deleted_count == initial_count

        # Re-extract nodes (previous ones are now deleted)
        new_nodes = await node_extractor.extract_repository_nodes(repository.id)

        # Persist again
        await persister.persist_nodes(new_nodes)
        await async_session.flush()  # Nodes now have IDs

        # Re-extract edges with new node IDs
        new_edges = await edge_extractor.extract_all_edges(repository.id, new_nodes)
        await persister.persist_edges(new_edges)
        await async_session.flush()

        # Verify count remains the same
        result = await async_session.execute(
            select(RepositoryNode).where(RepositoryNode.repository_id == repository.id)
        )
        final_count = len(list(result.scalars().all()))
        assert final_count == initial_count

    async def test_delete_repository_graph(
        self,
        async_session: AsyncSession,
        repository: Repository,
        repository_file: RepositoryFile,
        repository_symbol: RepositorySymbol,
    ) -> None:
        """Test deleting repository graph."""
        # Create and persist graph
        node_extractor = NodeExtractor(session=async_session)
        nodes = await node_extractor.extract_repository_nodes(repository.id)

        persister = GraphPersister(session=async_session)
        await persister.persist_nodes(nodes)
        await async_session.flush()  # Nodes now have IDs

        edge_extractor = EdgeExtractor(session=async_session)
        edges = await edge_extractor.extract_all_edges(repository.id, nodes)

        await persister.persist_edges(edges)
        await async_session.flush()

        # Verify graph exists
        result = await async_session.execute(
            select(RepositoryNode).where(RepositoryNode.repository_id == repository.id)
        )
        assert len(list(result.scalars().all())) > 0

        # Delete graph
        deleted_count = await persister.delete_repository_graph(repository.id)
        await async_session.flush()

        assert deleted_count > 0

        # Verify graph deleted
        result = await async_session.execute(
            select(RepositoryNode).where(RepositoryNode.repository_id == repository.id)
        )
        assert len(list(result.scalars().all())) == 0

        # Note: Cascade delete of edges may not work in SQLite without explicit configuration
        # In production PostgreSQL, edges would cascade delete automatically

    async def test_update_graph(
        self,
        async_session: AsyncSession,
        repository: Repository,
        repository_file: RepositoryFile,
        repository_symbol: RepositorySymbol,
    ) -> None:
        """Test updating graph."""
        # Create initial graph
        node_extractor = NodeExtractor(session=async_session)
        nodes = await node_extractor.extract_repository_nodes(repository.id)

        persister = GraphPersister(session=async_session)
        await persister.persist_nodes(nodes)
        await async_session.flush()  # Nodes now have IDs

        edge_extractor = EdgeExtractor(session=async_session)
        edges = await edge_extractor.extract_all_edges(repository.id, nodes)

        await persister.persist_edges(edges)
        await async_session.flush()

        # Update graph (delete and re-persist)
        await persister.delete_repository_graph(repository.id)
        await async_session.flush()

        # Re-extract nodes (previous ones are now deleted)
        new_nodes = await node_extractor.extract_repository_nodes(repository.id)

        await persister.persist_nodes(new_nodes)
        await async_session.flush()  # Nodes now have IDs

        # Re-extract edges with new node IDs
        new_edges = await edge_extractor.extract_all_edges(repository.id, new_nodes)
        await persister.persist_edges(new_edges)
        await async_session.flush()

        # Verify persistence
        stats = await persister.get_graph_statistics(repository.id)
        assert stats["total_nodes"] == len(new_nodes)
        assert stats["total_edges"] == len(new_edges)

    async def test_graph_exists(
        self,
        async_session: AsyncSession,
        repository: Repository,
        repository_file: RepositoryFile,
        repository_symbol: RepositorySymbol,
    ) -> None:
        """Test checking if graph exists."""
        persister = GraphPersister(session=async_session)

        # Should not exist initially
        exists = await persister.graph_exists(repository.id)
        assert exists is False

        # Create graph
        node_extractor = NodeExtractor(session=async_session)
        nodes = await node_extractor.extract_repository_nodes(repository.id)

        await persister.persist_nodes(nodes)
        await async_session.flush()  # Nodes now have IDs

        edge_extractor = EdgeExtractor(session=async_session)
        edges = await edge_extractor.extract_all_edges(repository.id, nodes)

        await persister.persist_edges(edges)
        await async_session.flush()

        # Should exist now
        exists = await persister.graph_exists(repository.id)
        assert exists is True

    async def test_get_graph_statistics(
        self,
        async_session: AsyncSession,
        repository: Repository,
        repository_file: RepositoryFile,
        repository_symbol: RepositorySymbol,
    ) -> None:
        """Test getting graph statistics."""
        # Create graph
        node_extractor = NodeExtractor(session=async_session)
        nodes = await node_extractor.extract_repository_nodes(repository.id)

        persister = GraphPersister(session=async_session)
        await persister.persist_nodes(nodes)
        await async_session.flush()  # Nodes now have IDs

        edge_extractor = EdgeExtractor(session=async_session)
        edges = await edge_extractor.extract_all_edges(repository.id, nodes)

        await persister.persist_edges(edges)
        await async_session.flush()

        # Get statistics
        stats = await persister.get_graph_statistics(repository.id)

        assert stats["repository_id"] == str(repository.id)
        assert stats["total_nodes"] == len(nodes)
        assert stats["total_edges"] == len(edges)
        assert "nodes_by_type" in stats
        assert "edges_by_type" in stats
        assert stats["graph_exists"] is True

    async def test_persist_incremental(
        self,
        async_session: AsyncSession,
        repository: Repository,
        repository_file: RepositoryFile,
        repository_symbol: RepositorySymbol,
    ) -> None:
        """Test incremental graph persistence."""
        # Create initial graph
        node_extractor = NodeExtractor(session=async_session)
        initial_nodes = await node_extractor.extract_repository_nodes(repository.id)

        persister = GraphPersister(session=async_session)
        await persister.persist_nodes(initial_nodes)
        await async_session.flush()  # Nodes now have IDs

        edge_extractor = EdgeExtractor(session=async_session)
        initial_edges = await edge_extractor.extract_all_edges(repository.id, initial_nodes)

        await persister.persist_edges(initial_edges)
        await async_session.flush()

        # Create new file and symbol
        new_file = RepositoryFile(
            repository_id=repository.id,
            relative_path="src/new.py",
            absolute_path="/tmp/testrepo/src/new.py",
            file_name="new.py",
            extension=".py",
            language="python",
            size_bytes=512,
            line_count=25,
            sha256_hash="newfile123",
            last_modified=datetime.utcnow(),
            is_binary=False,
        )
        async_session.add(new_file)
        await async_session.flush()

        # Extract only new nodes
        new_nodes = await node_extractor.extract_file_nodes(repository.id)
        new_file_node = [n for n in new_nodes if n.repository_file_id == new_file.id]

        # Persist incrementally
        stats = await persister.persist_incremental(
            repository.id, new_file_node, [], node_keys_to_delete=None
        )

        assert stats["incremental"] is True
        assert stats["nodes_persisted"] > 0

    async def test_delete_nodes_by_file(
        self,
        async_session: AsyncSession,
        repository: Repository,
        repository_file: RepositoryFile,
        repository_symbol: RepositorySymbol,
    ) -> None:
        """Test deleting nodes by file."""
        # Create graph
        node_extractor = NodeExtractor(session=async_session)
        nodes = await node_extractor.extract_repository_nodes(repository.id)

        persister = GraphPersister(session=async_session)
        await persister.persist_nodes(nodes)
        await async_session.flush()  # Nodes now have IDs

        edge_extractor = EdgeExtractor(session=async_session)
        edges = await edge_extractor.extract_all_edges(repository.id, nodes)

        await persister.persist_edges(edges)
        await async_session.flush()

        # Delete nodes by file
        deleted_count = await persister.delete_nodes_by_file(repository.id, [repository_file.id])
        await async_session.flush()

        assert deleted_count > 0

        # Verify file and symbol nodes deleted, repository node remains
        result = await async_session.execute(
            select(RepositoryNode).where(
                RepositoryNode.repository_id == repository.id,
                RepositoryNode.node_type == "repository",
            )
        )
        repo_nodes = list(result.scalars().all())
        assert len(repo_nodes) == 1  # Repository node should still exist

    async def test_delete_edges_by_relationship_type(
        self,
        async_session: AsyncSession,
        repository: Repository,
        repository_file: RepositoryFile,
        repository_symbol: RepositorySymbol,
    ) -> None:
        """Test deleting edges by relationship type."""
        # Create graph
        node_extractor = NodeExtractor(session=async_session)
        nodes = await node_extractor.extract_repository_nodes(repository.id)

        persister = GraphPersister(session=async_session)
        await persister.persist_nodes(nodes)
        await async_session.flush()  # Nodes now have IDs

        edge_extractor = EdgeExtractor(session=async_session)
        edges = await edge_extractor.extract_all_edges(repository.id, nodes)

        await persister.persist_edges(edges)
        await async_session.flush()

        # Get initial edge count
        result = await async_session.execute(select(RepositoryEdge))
        initial_count = len(list(result.scalars().all()))

        # Delete CONTAINS edges
        deleted_count = await persister.delete_edges_by_relationship_type(
            repository.id, "CONTAINS"
        )
        await async_session.flush()

        assert deleted_count > 0

        # Verify edges deleted
        result = await async_session.execute(select(RepositoryEdge))
        final_count = len(list(result.scalars().all()))
        assert final_count < initial_count

    async def test_commit_and_rollback(
        self,
        async_session: AsyncSession,
        repository: Repository,
        repository_file: RepositoryFile,
    ) -> None:
        """Test explicit commit and rollback."""
        node_extractor = NodeExtractor(session=async_session)
        nodes = await node_extractor.extract_repository_nodes(repository.id)

        persister = GraphPersister(session=async_session)
        await persister.persist_nodes(nodes)

        # Test rollback
        await persister.rollback()

        # Nodes should not be persisted
        result = await async_session.execute(
            select(RepositoryNode).where(RepositoryNode.repository_id == repository.id)
        )
        assert len(list(result.scalars().all())) == 0

        # Persist again and commit
        await persister.persist_nodes(nodes)
        await persister.commit()

        # Nodes should be persisted
        result = await async_session.execute(
            select(RepositoryNode).where(RepositoryNode.repository_id == repository.id)
        )
        assert len(list(result.scalars().all())) > 0
