"""Graph query service.

Provides high-level query interface for the repository knowledge graph.
Handles common graph traversal and analysis operations.
"""

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.repository_edge import RepositoryEdge
from app.db.models.repository_node import RepositoryNode


class GraphService:
    """Service for querying the repository knowledge graph.

    Provides methods for:
    - Querying nodes and edges
    - Graph traversal operations
    - Relationship analysis
    - Graph statistics
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the graph service.

        Args:
            session: Database session for queries
        """
        self.session = session

    async def get_node(self, node_id: UUID) -> RepositoryNode | None:
        """Get a graph node by ID.

        Args:
            node_id: UUID of the node

        Returns:
            RepositoryNode instance or None if not found
        """
        result = await self.session.execute(
            select(RepositoryNode).where(RepositoryNode.id == node_id)
        )
        return result.scalar_one_or_none()

    async def get_nodes_by_repository(
        self,
        repository_id: UUID,
        node_type: str | None = None,
        language: str | None = None,
    ) -> list[RepositoryNode]:
        """Get all nodes for a repository.

        Args:
            repository_id: UUID of the repository
            node_type: Optional filter by node type
            language: Optional filter by language

        Returns:
            List of RepositoryNode instances
        """
        query = select(RepositoryNode).where(
            RepositoryNode.repository_id == repository_id
        )

        if node_type:
            query = query.where(RepositoryNode.node_type == node_type)

        if language:
            query = query.where(RepositoryNode.language == language)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_outgoing_edges(
        self, node_id: UUID, relationship_type: str | None = None
    ) -> list[RepositoryEdge]:
        """Get all outgoing edges from a node.

        Args:
            node_id: UUID of the source node
            relationship_type: Optional filter by relationship type

        Returns:
            List of RepositoryEdge instances
        """
        query = select(RepositoryEdge).where(RepositoryEdge.source_node_id == node_id)

        if relationship_type:
            query = query.where(RepositoryEdge.relationship_type == relationship_type)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_incoming_edges(
        self, node_id: UUID, relationship_type: str | None = None
    ) -> list[RepositoryEdge]:
        """Get all incoming edges to a node.

        Args:
            node_id: UUID of the target node
            relationship_type: Optional filter by relationship type

        Returns:
            List of RepositoryEdge instances
        """
        query = select(RepositoryEdge).where(RepositoryEdge.target_node_id == node_id)

        if relationship_type:
            query = query.where(RepositoryEdge.relationship_type == relationship_type)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_neighbors(
        self,
        node_id: UUID,
        relationship_type: str | None = None,
        direction: str = "both",
    ) -> list[RepositoryNode]:
        """Get all neighboring nodes.

        Args:
            node_id: UUID of the node
            relationship_type: Optional filter by relationship type
            direction: "outgoing", "incoming", or "both"

        Returns:
            List of RepositoryNode instances
        """
        nodes: list[RepositoryNode] = []

        if direction in ("outgoing", "both"):
            edges = await self.get_outgoing_edges(node_id, relationship_type)
            for edge in edges:
                if edge.target_node:
                    nodes.append(edge.target_node)

        if direction in ("incoming", "both"):
            edges = await self.get_incoming_edges(node_id, relationship_type)
            for edge in edges:
                if edge.source_node:
                    nodes.append(edge.source_node)

        return nodes

    async def get_graph_statistics(self, repository_id: UUID) -> dict[str, Any]:
        """Get statistics about the repository graph.

        Args:
            repository_id: UUID of the repository

        Returns:
            Dictionary with graph statistics:
            {
                "total_nodes": int,
                "nodes_by_type": dict[str, int],
                "total_edges": int,
                "edges_by_type": dict[str, int],
                "nodes_by_language": dict[str, int],
            }
        """
        # Count total nodes
        nodes = await self.get_nodes_by_repository(repository_id)
        total_nodes = len(nodes)

        # Count nodes by type
        nodes_by_type: dict[str, int] = {}
        nodes_by_language: dict[str, int] = {}

        for node in nodes:
            # Count by type
            node_type = node.node_type
            nodes_by_type[node_type] = nodes_by_type.get(node_type, 0) + 1

            # Count by language (if available)
            if node.language:
                language = node.language
                nodes_by_language[language] = nodes_by_language.get(language, 0) + 1

        # Count edges
        edge_result = await self.session.execute(
            select(RepositoryEdge)
            .join(RepositoryNode, RepositoryEdge.source_node_id == RepositoryNode.id)
            .where(RepositoryNode.repository_id == repository_id)
        )
        edges = list(edge_result.scalars().all())
        total_edges = len(edges)

        # Count edges by type
        edges_by_type: dict[str, int] = {}
        for edge in edges:
            rel_type = edge.relationship_type
            edges_by_type[rel_type] = edges_by_type.get(rel_type, 0) + 1

        return {
            "total_nodes": total_nodes,
            "nodes_by_type": nodes_by_type,
            "total_edges": total_edges,
            "edges_by_type": edges_by_type,
            "nodes_by_language": nodes_by_language,
        }

    async def find_path(
        self,
        source_id: UUID,
        target_id: UUID,
        max_depth: int = 5,
        relationship_type: str | None = None,
    ) -> list[UUID] | None:
        """Find a path between two nodes using breadth-first search.

        Args:
            source_id: UUID of the source node
            target_id: UUID of the target node
            max_depth: Maximum path length to search
            relationship_type: Optional filter by relationship type

        Returns:
            List of node UUIDs forming the path, or None if no path found
        """
        # Simple BFS implementation
        from collections import deque

        if source_id == target_id:
            return [source_id]

        visited = {source_id}
        queue = deque([(source_id, [source_id])])

        while queue and len(queue[0][1]) <= max_depth:
            current_id, path = queue.popleft()

            # Get outgoing edges
            edges = await self.get_outgoing_edges(current_id, relationship_type)

            for edge in edges:
                next_id = edge.target_node_id

                if next_id == target_id:
                    return path + [next_id]

                if next_id not in visited:
                    visited.add(next_id)
                    queue.append((next_id, path + [next_id]))

        return None

    async def has_relationship(
        self,
        source_id: UUID,
        target_id: UUID,
        relationship_type: str | None = None,
    ) -> bool:
        """Check if a relationship exists between two nodes.

        Args:
            source_id: UUID of the source node
            target_id: UUID of the target node
            relationship_type: Optional specific relationship type to check

        Returns:
            True if relationship exists, False otherwise
        """
        query = select(RepositoryEdge).where(
            RepositoryEdge.source_node_id == source_id,
            RepositoryEdge.target_node_id == target_id,
        )

        if relationship_type:
            query = query.where(RepositoryEdge.relationship_type == relationship_type)

        result = await self.session.execute(query)
        return result.scalar_one_or_none() is not None
