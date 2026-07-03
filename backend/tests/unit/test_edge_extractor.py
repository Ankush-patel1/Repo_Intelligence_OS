"""Unit tests for EdgeExtractor service."""

import json
from datetime import datetime
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.db.models.repository import Repository
from app.db.models.repository_file import RepositoryFile
from app.db.models.repository_node import RepositoryNode
from app.db.models.repository_symbol import RepositorySymbol
from app.services.graph.edge_extractor import EdgeExtractor
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


class TestEdgeExtractor:
    """Test suite for EdgeExtractor."""

    async def test_extract_contains_edges_repo_to_file(
        self, async_session: AsyncSession, repository: Repository, repository_file: RepositoryFile
    ) -> None:
        """Test extracting CONTAINS edges from repository to file."""
        # Extract nodes first
        node_extractor = NodeExtractor(session=async_session)
        nodes = await node_extractor.extract_repository_nodes(repository.id)

        # Extract edges
        edge_extractor = EdgeExtractor(session=async_session)
        edges = await edge_extractor.extract_contains_edges(nodes)

        # Should have repository -> file edge
        repo_file_edges = [e for e in edges if e.relationship_type == "CONTAINS"]
        assert len(repo_file_edges) >= 1

        # Verify edge structure
        edge = repo_file_edges[0]
        metadata = json.loads(edge.edge_metadata)
        assert metadata["container_type"] in ["repository", "file"]
        assert metadata["contained_type"] in ["file", "symbol"]

    async def test_extract_contains_edges_file_to_symbol(
        self, async_session: AsyncSession, repository: Repository, repository_file: RepositoryFile
    ) -> None:
        """Test extracting CONTAINS edges from file to symbol."""
        # Create symbol
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

        # Extract nodes
        node_extractor = NodeExtractor(session=async_session)
        nodes = await node_extractor.extract_repository_nodes(repository.id)

        # Extract edges
        edge_extractor = EdgeExtractor(session=async_session)
        edges = await edge_extractor.extract_contains_edges(nodes)

        # Should have file -> symbol edge
        file_symbol_edges = [
            e
            for e in edges
            if json.loads(e.edge_metadata).get("contained_type") == "symbol"
        ]
        assert len(file_symbol_edges) >= 1

    async def test_extract_contains_edges_parent_child_symbols(
        self, async_session: AsyncSession, repository: Repository, repository_file: RepositoryFile
    ) -> None:
        """Test extracting CONTAINS edges for parent-child symbol hierarchy."""
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

        # Extract nodes
        node_extractor = NodeExtractor(session=async_session)
        nodes = await node_extractor.extract_repository_nodes(repository.id)

        # Extract edges
        edge_extractor = EdgeExtractor(session=async_session)
        edges = await edge_extractor.extract_contains_edges(nodes)

        # Find parent-child edge
        parent_child_edges = [
            e
            for e in edges
            if json.loads(e.edge_metadata).get("parent_child") is True
        ]
        assert len(parent_child_edges) >= 1

        edge = parent_child_edges[0]
        metadata = json.loads(edge.edge_metadata)
        assert metadata["parent_child"] is True

    async def test_extract_imports_edges(
        self, async_session: AsyncSession, repository: Repository, repository_file: RepositoryFile
    ) -> None:
        """Test extracting IMPORTS edges."""
        # Create import symbol
        import_symbol = RepositorySymbol(
            repository_file_id=repository_file.id,
            symbol_name="os",
            symbol_type="import",
            parent_symbol=None,
            start_line=1,
            end_line=1,
            language="python",
            signature="import os",
        )
        async_session.add(import_symbol)
        await async_session.flush()

        # Extract nodes
        node_extractor = NodeExtractor(session=async_session)
        nodes = await node_extractor.extract_repository_nodes(repository.id)
        node_by_symbol = {n.symbol_id: n for n in nodes if n.symbol_id}

        # Extract edges
        edge_extractor = EdgeExtractor(session=async_session)
        edges = await edge_extractor.extract_imports_edges(repository.id, nodes, node_by_symbol)

        assert len(edges) >= 1
        edge = edges[0]
        assert edge.relationship_type == "IMPORTS"

        metadata = json.loads(edge.edge_metadata)
        assert "import_statement" in metadata
        assert metadata["import_type"] == "import"

    async def test_extract_inherits_edges(
        self, async_session: AsyncSession, repository: Repository, repository_file: RepositoryFile
    ) -> None:
        """Test extracting INHERITS edges."""
        # Create class with inheritance
        class_symbol = RepositorySymbol(
            repository_file_id=repository_file.id,
            symbol_name="ChildClass",
            symbol_type="class",
            parent_symbol=None,
            start_line=10,
            end_line=20,
            language="python",
            signature="class ChildClass(BaseClass):",
            symbol_metadata='{"base_classes": ["BaseClass"]}',
        )
        async_session.add(class_symbol)
        await async_session.flush()

        # Extract nodes
        node_extractor = NodeExtractor(session=async_session)
        nodes = await node_extractor.extract_repository_nodes(repository.id)
        node_by_symbol = {n.symbol_id: n for n in nodes if n.symbol_id}

        # Extract edges
        edge_extractor = EdgeExtractor(session=async_session)
        edges = await edge_extractor.extract_inherits_edges(repository.id, nodes, node_by_symbol)

        assert len(edges) >= 1
        edge = edges[0]
        assert edge.relationship_type == "INHERITS"

        metadata = json.loads(edge.edge_metadata)
        assert metadata["base_class"] == "BaseClass"
        assert metadata["derived_class"] == "ChildClass"

    async def test_extract_implements_edges(
        self, async_session: AsyncSession, repository: Repository, repository_file: RepositoryFile
    ) -> None:
        """Test extracting IMPLEMENTS edges."""
        # Create class with interface implementation
        class_symbol = RepositorySymbol(
            repository_file_id=repository_file.id,
            symbol_name="MyClass",
            symbol_type="class",
            parent_symbol=None,
            start_line=10,
            end_line=20,
            language="typescript",
            signature="class MyClass implements IMyInterface",
            symbol_metadata='{"interfaces": ["IMyInterface"]}',
        )
        async_session.add(class_symbol)
        await async_session.flush()

        # Extract nodes
        node_extractor = NodeExtractor(session=async_session)
        nodes = await node_extractor.extract_repository_nodes(repository.id)
        node_by_symbol = {n.symbol_id: n for n in nodes if n.symbol_id}

        # Extract edges
        edge_extractor = EdgeExtractor(session=async_session)
        edges = await edge_extractor.extract_implements_edges(repository.id, nodes, node_by_symbol)

        assert len(edges) >= 1
        edge = edges[0]
        assert edge.relationship_type == "IMPLEMENTS"

        metadata = json.loads(edge.edge_metadata)
        assert metadata["interface"] == "IMyInterface"
        assert metadata["implementing_class"] == "MyClass"

    async def test_extract_declares_edges_function_parameters(
        self, async_session: AsyncSession, repository: Repository, repository_file: RepositoryFile
    ) -> None:
        """Test extracting DECLARES edges for function parameters."""
        # Create function with parameters
        function_symbol = RepositorySymbol(
            repository_file_id=repository_file.id,
            symbol_name="test_function",
            symbol_type="function",
            parent_symbol=None,
            start_line=10,
            end_line=15,
            language="python",
            signature="def test_function(x, y):",
            symbol_metadata='{"parameters": ["x", "y"]}',
        )
        async_session.add(function_symbol)
        await async_session.flush()

        # Extract nodes
        node_extractor = NodeExtractor(session=async_session)
        nodes = await node_extractor.extract_repository_nodes(repository.id)
        node_by_symbol = {n.symbol_id: n for n in nodes if n.symbol_id}

        # Extract edges
        edge_extractor = EdgeExtractor(session=async_session)
        edges = await edge_extractor.extract_declares_edges(nodes, node_by_symbol)

        # Should have 2 declares edges (one per parameter)
        declares_edges = [e for e in edges if e.relationship_type == "DECLARES"]
        assert len(declares_edges) == 2

        # Verify metadata
        for edge in declares_edges:
            metadata = json.loads(edge.edge_metadata)
            assert metadata["declaration_type"] == "parameter"
            assert metadata["parameter_name"] in ["x", "y"]

    async def test_extract_declares_edges_class_fields(
        self, async_session: AsyncSession, repository: Repository, repository_file: RepositoryFile
    ) -> None:
        """Test extracting DECLARES edges for class fields."""
        # Create class with fields
        class_symbol = RepositorySymbol(
            repository_file_id=repository_file.id,
            symbol_name="TestClass",
            symbol_type="class",
            parent_symbol=None,
            start_line=10,
            end_line=20,
            language="python",
            signature="class TestClass:",
            symbol_metadata='{"fields": ["field1", "field2"]}',
        )
        async_session.add(class_symbol)
        await async_session.flush()

        # Extract nodes
        node_extractor = NodeExtractor(session=async_session)
        nodes = await node_extractor.extract_repository_nodes(repository.id)
        node_by_symbol = {n.symbol_id: n for n in nodes if n.symbol_id}

        # Extract edges
        edge_extractor = EdgeExtractor(session=async_session)
        edges = await edge_extractor.extract_declares_edges(nodes, node_by_symbol)

        # Should have 2 declares edges (one per field)
        declares_edges = [e for e in edges if e.relationship_type == "DECLARES"]
        assert len(declares_edges) == 2

        # Verify metadata
        for edge in declares_edges:
            metadata = json.loads(edge.edge_metadata)
            assert metadata["declaration_type"] == "field"
            assert metadata["field_name"] in ["field1", "field2"]

    async def test_extract_references_edges_decorators(
        self, async_session: AsyncSession, repository: Repository, repository_file: RepositoryFile
    ) -> None:
        """Test extracting REFERENCES edges for decorators."""
        # Create function with decorators
        function_symbol = RepositorySymbol(
            repository_file_id=repository_file.id,
            symbol_name="test_function",
            symbol_type="function",
            parent_symbol=None,
            start_line=10,
            end_line=15,
            language="python",
            signature="def test_function():",
            symbol_metadata='{"decorators": ["@property", "@staticmethod"]}',
        )
        async_session.add(function_symbol)
        await async_session.flush()

        # Extract nodes
        node_extractor = NodeExtractor(session=async_session)
        nodes = await node_extractor.extract_repository_nodes(repository.id)
        node_by_symbol = {n.symbol_id: n for n in nodes if n.symbol_id}

        # Extract edges
        edge_extractor = EdgeExtractor(session=async_session)
        edges = await edge_extractor.extract_references_edges(nodes, node_by_symbol)

        # Should have 2 references edges (one per decorator)
        references_edges = [e for e in edges if e.relationship_type == "REFERENCES"]
        assert len(references_edges) == 2

        # Verify metadata
        for edge in references_edges:
            metadata = json.loads(edge.edge_metadata)
            assert metadata["reference_type"] == "decorator"
            assert metadata["decorator_name"] in ["@property", "@staticmethod"]

    async def test_extract_all_edges(
        self, async_session: AsyncSession, repository: Repository, repository_file: RepositoryFile
    ) -> None:
        """Test extracting all edge types."""
        # Create various symbols
        symbols = [
            RepositorySymbol(
                repository_file_id=repository_file.id,
                symbol_name="os",
                symbol_type="import",
                start_line=1,
                end_line=1,
                language="python",
                signature="import os",
            ),
            RepositorySymbol(
                repository_file_id=repository_file.id,
                symbol_name="TestClass",
                symbol_type="class",
                start_line=10,
                end_line=30,
                language="python",
                signature="class TestClass:",
                symbol_metadata='{"base_classes": ["BaseClass"]}',
            ),
        ]
        async_session.add_all(symbols)
        await async_session.flush()

        # Add method to class
        method = RepositorySymbol(
            repository_file_id=repository_file.id,
            symbol_name="test_method",
            symbol_type="method",
            parent_symbol=symbols[1].id,
            start_line=15,
            end_line=20,
            language="python",
            signature="def test_method(self):",
        )
        async_session.add(method)
        await async_session.flush()

        # Extract nodes
        node_extractor = NodeExtractor(session=async_session)
        nodes = await node_extractor.extract_repository_nodes(repository.id)

        # Extract all edges
        edge_extractor = EdgeExtractor(session=async_session)
        edges = await edge_extractor.extract_all_edges(repository.id, nodes)

        assert len(edges) > 0

        # Verify we have different relationship types
        relationship_types = {e.relationship_type for e in edges}
        assert "CONTAINS" in relationship_types
        # May have IMPORTS, INHERITS depending on symbols created

    async def test_get_edge_statistics(
        self, async_session: AsyncSession, repository: Repository, repository_file: RepositoryFile
    ) -> None:
        """Test getting edge statistics."""
        # Create symbols
        symbol = RepositorySymbol(
            repository_file_id=repository_file.id,
            symbol_name="test_function",
            symbol_type="function",
            start_line=10,
            end_line=15,
            language="python",
            signature="def test_function():",
        )
        async_session.add(symbol)
        await async_session.flush()

        # Extract nodes and edges
        node_extractor = NodeExtractor(session=async_session)
        nodes = await node_extractor.extract_repository_nodes(repository.id)

        edge_extractor = EdgeExtractor(session=async_session)
        edges = await edge_extractor.extract_all_edges(repository.id, nodes)

        # Get statistics
        stats = await edge_extractor.get_edge_statistics(edges)

        assert "total_edges" in stats
        assert "edges_by_type" in stats
        assert "unique_relationship_types" in stats
        assert stats["total_edges"] == len(edges)
        assert stats["total_edges"] > 0

    async def test_extract_calls_edges_placeholder(
        self, async_session: AsyncSession, repository: Repository, repository_file: RepositoryFile
    ) -> None:
        """Test extracting CALLS edges (placeholder implementation)."""
        # Extract nodes
        node_extractor = NodeExtractor(session=async_session)
        nodes = await node_extractor.extract_repository_nodes(repository.id)
        node_by_symbol = {n.symbol_id: n for n in nodes if n.symbol_id}

        # Extract calls edges
        edge_extractor = EdgeExtractor(session=async_session)
        edges = await edge_extractor.extract_calls_edges(repository.id, nodes, node_by_symbol)

        # Current implementation returns empty list (placeholder)
        assert isinstance(edges, list)
        # Note: When call analysis is implemented, this test should verify CALLS edges
