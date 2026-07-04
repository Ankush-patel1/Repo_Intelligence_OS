"""Repository processing pipeline orchestrator.

Coordinates the complete repository analysis pipeline:
1. Import (handled externally)
2. Clone (handled externally)
3. Index (scan files)
4. Parse (extract symbols)
5. Build Knowledge Graph (create nodes and edges)
6. Generate Semantic Chunks (create semantic code chunks)
"""

from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.chunking import ClassChunker, ChunkPersister, FunctionChunker
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
        self.class_chunker = ClassChunker(session=session)
        self.function_chunker = FunctionChunker(session=session)
        self.chunk_persister = ChunkPersister(session=session)

    async def run_full_pipeline(
        self,
        repository_id: UUID,
        skip_indexing: bool = False,
        skip_graph: bool = False,
        skip_chunking: bool = False,
    ) -> dict[str, Any]:
        """Run the complete pipeline for a repository.

        Pipeline steps:
        1. Index repository (scan files and extract symbols)
        2. Build knowledge graph (create nodes and edges)
        3. Generate semantic chunks (create code chunks)

        Args:
            repository_id: UUID of the repository
            skip_indexing: Skip indexing step (use existing data)
            skip_graph: Skip graph building step
            skip_chunking: Skip semantic chunking step

        Returns:
            Dictionary with statistics from all pipeline stages:
            {
                "repository_id": str,
                "indexing": {...},
                "graph": {...},
                "chunking": {...},
                "pipeline_complete": bool
            }
        """
        results: dict[str, Any] = {
            "repository_id": str(repository_id),
            "indexing": None,
            "graph": None,
            "chunking": None,
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

        # Step 3: Generate semantic chunks (if not skipped)
        if not skip_chunking:
            chunking_stats = await self.generate_chunks(repository_id)
            results["chunking"] = chunking_stats
            await self.session.flush()
        else:
            results["chunking"] = {"skipped": True}

        # Mark pipeline as complete
        results["pipeline_complete"] = True

        return results

    async def run_index_and_graph(self, repository_id: UUID) -> dict[str, Any]:
        """Run indexing and graph building (legacy workflow without chunking).

        Convenience method that runs indexing and graph building only.
        Use run_full_pipeline for complete analysis including chunking.

        Args:
            repository_id: UUID of the repository

        Returns:
            Dictionary with pipeline statistics
        """
        return await self.run_full_pipeline(
            repository_id,
            skip_indexing=False,
            skip_graph=False,
            skip_chunking=True,
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
            skip_chunking=True,
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
                "chunks_generated": bool,
                "indexing_stats": {...},
                "graph_stats": {...},
                "chunking_stats": {...}
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

        # Check if chunks exist
        chunking_stats = await self.chunk_persister.get_chunk_statistics(repository_id)
        chunks_generated = chunking_stats["total_chunks"] > 0

        return {
            "repository_id": str(repository_id),
            "indexed": indexed,
            "graph_built": graph_exists,
            "chunks_generated": chunks_generated,
            "indexing_stats": indexing_stats,
            "graph_stats": graph_stats,
            "chunking_stats": chunking_stats,
        }

    async def generate_chunks(
        self,
        repository_id: UUID,
        include_classes: bool = True,
        include_functions: bool = True,
        include_methods: bool = True,
    ) -> dict[str, Any]:
        """Generate semantic chunks for a repository.

        Creates semantic code chunks from parsed symbols and graph data.
        Uses ClassChunker and FunctionChunker to generate chunks, then
        persists them with deduplication.

        Args:
            repository_id: UUID of the repository
            include_classes: Whether to chunk classes (default: True)
            include_functions: Whether to chunk functions (default: True)
            include_methods: Whether to chunk methods (default: True)

        Returns:
            Dictionary with chunking statistics:
            {
                "total_chunks": int,
                "created": int,
                "updated": int,
                "deleted": int,
                "unchanged": int,
                "by_type": {...}
            }
        """
        all_chunks = []

        # Generate class chunks
        if include_classes:
            try:
                class_chunks = await self.class_chunker.chunk_all_classes(repository_id)
                all_chunks.extend(class_chunks)
            except Exception as e:
                # Log but continue with other chunk types
                print(f"Error generating class chunks: {e}")

        # Generate function/method chunks
        if include_functions or include_methods:
            try:
                function_chunks = await self.function_chunker.chunk_all_functions(
                    repository_id, include_methods=include_methods
                )
                all_chunks.extend(function_chunks)
            except Exception as e:
                # Log but continue
                print(f"Error generating function chunks: {e}")

        # Persist chunks with update strategy (handles create/update/delete)
        stats = await self.chunk_persister.update_repository_chunks(
            repository_id, all_chunks
        )

        # Get chunk type breakdown
        chunking_stats = await self.chunk_persister.get_chunk_statistics(repository_id)

        return {
            "total_chunks": chunking_stats["total_chunks"],
            "created": stats["created"],
            "updated": stats["updated"],
            "deleted": stats["deleted"],
            "unchanged": stats["unchanged"],
            "by_type": chunking_stats.get("by_type", {}),
        }

    async def regenerate_chunks(self, repository_id: UUID) -> dict[str, Any]:
        """Regenerate chunks without re-running other pipeline stages.

        Useful when:
        - Chunking logic has been updated
        - Chunks need to be regenerated from existing graph data
        - You want to rebuild chunks without re-parsing

        Args:
            repository_id: UUID of the repository

        Returns:
            Dictionary with chunking statistics
        """
        return await self.generate_chunks(repository_id)
