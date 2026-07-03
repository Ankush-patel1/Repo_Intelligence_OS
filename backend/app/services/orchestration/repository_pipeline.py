"""Repository processing pipeline orchestrator.

Coordinates the complete repository analysis pipeline:
1. Import (handled externally)
2. Clone (handled externally)
3. Index (scan files)
4. Parse (extract symbols)
5. Build Knowledge Graph (create nodes and edges)
"""

from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.graph import EdgeExtractor, GraphPersister, NodeExtractor
from app.services.indexing import FileScanner, RepositoryIndexer


class RepositoryPipeline:
    """Orchestrates the complete repository analysis pipeline.

    Coordinates indexing, parsing, and graph building in a single workflow.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the pipeline with database session.

        Args:
            session: Database session for all operations
        """
        self.session = session
        self.indexer = RepositoryIndexer(session=session, file_scanner=FileScanner())
        self.node_extractor = NodeExtractor(session=session)
        self.edge_extractor = EdgeExtractor(session=session)
        self.graph_persister = GraphPersister(session=session)

    async def run_full_pipeline(
        self,
        repository_id: UUID,
        skip_indexing: bool = False,
        skip_graph: bool = False,
    ) -> dict[str, Any]:
        """Run the complete pipeline for a repository.

        Pipeline steps:
        1. Index repository (scan files and extract symbols)
        2. Build knowledge graph (create nodes and edges)

        Args:
            repository_id: UUID of the repository
            skip_indexing: Skip indexing step (use existing data)
            skip_graph: Skip graph building step

        Returns:
            Dictionary with statistics from all pipeline stages:
            {
                "repository_id": str,
                "indexing": {...},
                "graph": {...},
                "pipeline_complete": bool
            }
        """
        results: dict[str, Any] = {
            "repository_id": str(repository_id),
            "indexing": None,
            "graph": None,
            "pipeline_complete": False,
        }

        # Step 1: Index repository (if not skipped)
        if not skip_indexing:
            indexing_stats = await self.indexer.index_repository_by_id(repository_id)
            results["indexing"] = indexing_stats
            await self.session.flush()
        else:
            results["indexing"] = {"skipped": True}

        # Step 2: Build knowledge graph (if not skipped)
        if not skip_graph:
            graph_stats = await self.build_graph(repository_id)
            results["graph"] = graph_stats
            await self.session.flush()
        else:
            results["graph"] = {"skipped": True}

        # Mark pipeline as complete
        results["pipeline_complete"] = True

        return results

    async def run_index_and_graph(self, repository_id: UUID) -> dict[str, Any]:
        """Run indexing and graph building (most common workflow).

        Convenience method that runs the full pipeline without skipping any steps.

        Args:
            repository_id: UUID of the repository

        Returns:
            Dictionary with pipeline statistics
        """
        return await self.run_full_pipeline(
            repository_id,
            skip_indexing=False,
            skip_graph=False,
        )

    async def run_graph_only(self, repository_id: UUID) -> dict[str, Any]:
        """Run only graph building (assumes repository already indexed).

        Args:
            repository_id: UUID of the repository

        Returns:
            Dictionary with graph statistics
        """
        return await self.run_full_pipeline(
            repository_id,
            skip_indexing=True,
            skip_graph=False,
        )

    async def build_graph(self, repository_id: UUID) -> dict[str, Any]:
        """Build knowledge graph for a repository.

        Extracts nodes and edges from indexed data and persists to database.

        Args:
            repository_id: UUID of the repository

        Returns:
            Dictionary with graph building statistics:
            {
                "nodes_persisted": int,
                "edges_persisted": int,
                "nodes_deleted": int,
                "cleanup_performed": bool,
                "statistics": {...}
            }
        """
        # Extract and persist nodes first
        nodes = await self.node_extractor.extract_repository_nodes(repository_id)
        
        # Delete old graph
        nodes_deleted = await self.graph_persister.delete_repository_graph(repository_id)
        
        # Persist nodes to get IDs
        await self.graph_persister.persist_nodes(nodes)
        await self.session.flush()  # Flush to assign IDs to nodes

        # Now extract edges (nodes have IDs now)
        edges = await self.edge_extractor.extract_all_edges(repository_id, nodes)

        # Persist edges
        await self.graph_persister.persist_edges(edges)
        await self.session.flush()

        # Get final graph statistics
        graph_stats = await self.graph_persister.get_graph_statistics(repository_id)

        # Combine statistics
        return {
            "nodes_persisted": len(nodes),
            "edges_persisted": len(edges),
            "nodes_deleted": nodes_deleted,
            "edges_deleted": 0,  # Cascade deleted with nodes
            "cleanup_performed": True,
            "statistics": graph_stats,
        }

    async def rebuild_graph(self, repository_id: UUID) -> dict[str, Any]:
        """Rebuild knowledge graph without re-indexing.

        Useful when graph logic changes but indexed data is unchanged.

        Args:
            repository_id: UUID of the repository

        Returns:
            Dictionary with graph statistics
        """
        return await self.build_graph(repository_id)

    async def get_pipeline_status(self, repository_id: UUID) -> dict[str, Any]:
        """Get status of pipeline stages for a repository.

        Checks what pipeline stages have been completed.

        Args:
            repository_id: UUID of the repository

        Returns:
            Dictionary with pipeline status:
            {
                "repository_id": str,
                "indexed": bool,
                "graph_built": bool,
                "indexing_stats": {...},
                "graph_stats": {...}
            }
        """
        # Check if indexed (has files)
        indexing_stats = await self.indexer.get_statistics(repository_id)
        indexed = indexing_stats["total_files"] > 0

        # Check if graph exists
        graph_exists = await self.graph_persister.graph_exists(repository_id)
        graph_stats = None
        if graph_exists:
            graph_stats = await self.graph_persister.get_graph_statistics(repository_id)

        return {
            "repository_id": str(repository_id),
            "indexed": indexed,
            "graph_built": graph_exists,
            "indexing_stats": indexing_stats,
            "graph_stats": graph_stats,
        }
