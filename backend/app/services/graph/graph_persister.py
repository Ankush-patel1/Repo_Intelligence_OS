"""Graph persistence service.

Handles storing RepositoryNode and RepositoryEdge objects to the database,
avoiding duplicates and updating existing graphs on re-analysis.
"""

from typing import Any
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.repository_edge import RepositoryEdge
from app.db.models.repository_node import RepositoryNode


class GraphPersister:
    """Persists graph nodes and edges to the database.

    Handles:
    - Storing nodes and edges
    - Avoiding duplicates
    - Cleaning up old graph data
    - Updating on re-analysis
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the graph persister.

        Args:
            session: Database session for persistence
        """
        self.session = session

    async def persist_graph(
        self,
        repository_id: UUID,
        nodes: list[RepositoryNode],
        edges: list[RepositoryEdge],
        cleanup: bool = True,
    ) -> dict[str, Any]:
        """Persist complete graph to database.

        Args:
            repository_id: UUID of the repository
            nodes: List of RepositoryNode objects to persist
            edges: List of RepositoryEdge objects to persist
            cleanup: Whether to delete existing graph first (default: True)

        Returns:
            Dictionary with persistence statistics:
            {
                "repository_id": str,
                "nodes_persisted": int,
                "edges_persisted": int,
                "nodes_deleted": int,
                "edges_deleted": int,
                "cleanup_performed": bool,
            }
        """
        nodes_deleted = 0
        edges_deleted = 0

        # Clean up existing graph if requested
        if cleanup:
            nodes_deleted = await self.delete_repository_graph(repository_id)
            # Edges are cascade deleted with nodes

        # Persist nodes first (edges reference nodes)
        await self.persist_nodes(nodes)
        
        # Flush nodes to assign IDs before creating edges
        await self.session.flush()

        # Now persist edges (nodes have IDs now)
        await self.persist_edges(edges)

        # Flush edges to database
        await self.session.flush()

        return {
            "repository_id": str(repository_id),
            "nodes_persisted": len(nodes),
            "edges_persisted": len(edges),
            "nodes_deleted": nodes_deleted,
            "edges_deleted": edges_deleted,
            "cleanup_performed": cleanup,
        }

    async def persist_nodes(self, nodes: list[RepositoryNode]) -> int:
        """Persist nodes to database.

        Args:
            nodes: List of RepositoryNode objects

        Returns:
            Number of nodes persisted
        """
        if not nodes:
            return 0

        # Add all nodes to session
        self.session.add_all(nodes)

        return len(nodes)

    async def persist_edges(self, edges: list[RepositoryEdge]) -> int:
        """Persist edges to database.

        Args:
            edges: List of RepositoryEdge objects

        Returns:
            Number of edges persisted
        """
        if not edges:
            return 0

        # Add all edges to session
        self.session.add_all(edges)

        return len(edges)

    async def delete_repository_graph(self, repository_id: UUID) -> int:
        """Delete all graph data for a repository.

        Deletes nodes (edges cascade delete automatically).

        Args:
            repository_id: UUID of the repository

        Returns:
            Number of nodes deleted (edges cascade)
        """
        # Count existing nodes
        count_result = await self.session.execute(
            select(RepositoryNode).where(RepositoryNode.repository_id == repository_id)
        )
        existing_nodes = list(count_result.scalars().all())
        node_count = len(existing_nodes)

        # Delete all nodes for repository (edges cascade)
        await self.session.execute(
            delete(RepositoryNode).where(RepositoryNode.repository_id == repository_id)
        )

        return node_count

    async def update_graph(
        self,
        repository_id: UUID,
        nodes: list[RepositoryNode],
        edges: list[RepositoryEdge],
    ) -> dict[str, Any]:
        """Update graph by replacing old data with new.

        Convenience method that always performs cleanup.

        Args:
            repository_id: UUID of the repository
            nodes: New list of nodes
            edges: New list of edges

        Returns:
            Persistence statistics dictionary
        """
        return await self.persist_graph(
            repository_id, nodes, edges, cleanup=True
        )

    async def graph_exists(self, repository_id: UUID) -> bool:
        """Check if graph data exists for a repository.

        Args:
            repository_id: UUID of the repository

        Returns:
            True if graph nodes exist, False otherwise
        """
        result = await self.session.execute(
            select(RepositoryNode)
            .where(RepositoryNode.repository_id == repository_id)
            .limit(1)
        )
        return result.scalar_one_or_none() is not None

    async def get_graph_statistics(self, repository_id: UUID) -> dict[str, Any]:
        """Get statistics about persisted graph.

        Args:
            repository_id: UUID of the repository

        Returns:
            Dictionary with graph statistics
        """
        # Count nodes
        node_result = await self.session.execute(
            select(RepositoryNode).where(
                RepositoryNode.repository_id == repository_id
            )
        )
        nodes = list(node_result.scalars().all())
        total_nodes = len(nodes)

        # Count nodes by type
        nodes_by_type: dict[str, int] = {}
        for node in nodes:
            node_type = node.node_type
            nodes_by_type[node_type] = nodes_by_type.get(node_type, 0) + 1

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
            "repository_id": str(repository_id),
            "total_nodes": total_nodes,
            "nodes_by_type": nodes_by_type,
            "total_edges": total_edges,
            "edges_by_type": edges_by_type,
            "graph_exists": total_nodes > 0,
        }

    async def persist_incremental(
        self,
        repository_id: UUID,
        new_nodes: list[RepositoryNode],
        new_edges: list[RepositoryEdge],
        node_keys_to_delete: list[tuple[str, str]] | None = None,
    ) -> dict[str, Any]:
        """Persist graph incrementally without full cleanup.

        Useful for updating specific parts of the graph without
        rebuilding everything.

        Args:
            repository_id: UUID of the repository
            new_nodes: New nodes to add
            new_edges: New edges to add
            node_keys_to_delete: Optional list of (node_type, display_name) to delete

        Returns:
            Persistence statistics dictionary
        """
        nodes_deleted = 0

        # Delete specific nodes if requested
        if node_keys_to_delete:
            for node_type, display_name in node_keys_to_delete:
                result = await self.session.execute(
                    delete(RepositoryNode).where(
                        RepositoryNode.repository_id == repository_id,
                        RepositoryNode.node_type == node_type,
                        RepositoryNode.display_name == display_name,
                    )
                )
                nodes_deleted += result.rowcount or 0

        # Add new nodes and edges
        nodes_added = await self.persist_nodes(new_nodes)
        edges_added = await self.persist_edges(new_edges)

        await self.session.flush()

        return {
            "repository_id": str(repository_id),
            "nodes_persisted": nodes_added,
            "edges_persisted": edges_added,
            "nodes_deleted": nodes_deleted,
            "cleanup_performed": False,
            "incremental": True,
        }

    async def delete_nodes_by_file(
        self, repository_id: UUID, file_ids: list[UUID]
    ) -> int:
        """Delete all nodes associated with specific files.

        Useful for updating graphs when files are modified.

        Args:
            repository_id: UUID of the repository
            file_ids: List of file IDs to delete nodes for

        Returns:
            Number of nodes deleted
        """
        if not file_ids:
            return 0

        result = await self.session.execute(
            delete(RepositoryNode).where(
                RepositoryNode.repository_id == repository_id,
                RepositoryNode.repository_file_id.in_(file_ids),
            )
        )

        return result.rowcount or 0

    async def delete_edges_by_relationship_type(
        self, repository_id: UUID, relationship_type: str
    ) -> int:
        """Delete all edges of a specific relationship type.

        Useful for rebuilding specific relationship types without
        affecting others.

        Args:
            repository_id: UUID of the repository
            relationship_type: Type of relationship to delete

        Returns:
            Number of edges deleted
        """
        # Find all edges for this repository with the relationship type
        subquery = (
            select(RepositoryNode.id)
            .where(RepositoryNode.repository_id == repository_id)
        )

        result = await self.session.execute(
            delete(RepositoryEdge).where(
                RepositoryEdge.source_node_id.in_(subquery),
                RepositoryEdge.relationship_type == relationship_type,
            )
        )

        return result.rowcount or 0

    async def commit(self) -> None:
        """Commit the current transaction.

        Explicitly commits changes to the database.
        """
        await self.session.commit()

    async def rollback(self) -> None:
        """Rollback the current transaction.

        Reverts all changes since last commit.
        """
        await self.session.rollback()
