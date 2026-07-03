"""Graph builder orchestrator.

Coordinates the execution of multiple graph analyzers to build
the complete repository knowledge graph.
"""

from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.graph.graph_registry import get_registry


class GraphBuilder:
    """Orchestrates graph building across multiple analyzers.

    The GraphBuilder is responsible for:
    1. Coordinating analyzer execution in the correct order
    2. Aggregating results from multiple analyzers
    3. Handling errors and partial failures
    4. Providing progress tracking
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the graph builder.

        Args:
            session: Database session for graph operations
        """
        self.session = session
        self.registry = get_registry()

    async def build_graph(
        self,
        repository_id: UUID,
        relationship_types: list[str] | None = None,
        cleanup: bool = True,
    ) -> dict[str, Any]:
        """Build knowledge graph for a repository.

        Executes all registered analyzers (or specified subset) to build
        the complete graph structure. Analyzers run in priority order.

        Args:
            repository_id: UUID of repository to analyze
            relationship_types: Optional list of specific relationship types to build.
                              If None, builds all registered analyzers.
            cleanup: Whether to clean up existing relationships before building

        Returns:
            Dictionary with build statistics:
            {
                "repository_id": str,
                "total_nodes_created": int,
                "total_edges_created": int,
                "analyzers_run": int,
                "analyzers_skipped": int,
                "analyzers_failed": int,
                "results": [
                    {
                        "relationship_type": str,
                        "status": "success" | "skipped" | "failed",
                        "nodes_created": int,
                        "edges_created": int,
                        "error": str | None,
                    },
                    ...
                ],
                "duration_seconds": float,
            }
        """
        import time

        start_time = time.time()

        # Determine which analyzers to run
        if relationship_types:
            analyzers = [
                self.registry.get_analyzer(rel_type, self.session)
                for rel_type in relationship_types
                if self.registry.has_analyzer(rel_type)
            ]
            # Sort by priority
            analyzers = sorted(analyzers, key=lambda a: a.get_priority())
        else:
            analyzers = self.registry.get_all_analyzers(self.session)

        # Initialize statistics
        total_nodes = 0
        total_edges = 0
        analyzers_run = 0
        analyzers_skipped = 0
        analyzers_failed = 0
        results = []

        # Execute each analyzer
        for analyzer in analyzers:
            result = {
                "relationship_type": analyzer.relationship_type,
                "status": "pending",
                "nodes_created": 0,
                "edges_created": 0,
                "error": None,
            }

            try:
                # Check if analyzer can run
                if not await analyzer.can_analyze(repository_id):
                    result["status"] = "skipped"
                    analyzers_skipped += 1
                    results.append(result)
                    continue

                # Clean up existing relationships if requested
                if cleanup:
                    await analyzer.cleanup(repository_id)

                # Run the analyzer
                analysis_result = await analyzer.analyze(repository_id)

                # Update statistics
                result["status"] = "success"
                result["nodes_created"] = analysis_result.get("nodes_created", 0)
                result["edges_created"] = analysis_result.get("edges_created", 0)
                result.update(analysis_result)  # Include any additional fields

                total_nodes += result["nodes_created"]
                total_edges += result["edges_created"]
                analyzers_run += 1

            except Exception as e:
                result["status"] = "failed"
                result["error"] = str(e)
                analyzers_failed += 1

            results.append(result)

        end_time = time.time()

        return {
            "repository_id": str(repository_id),
            "total_nodes_created": total_nodes,
            "total_edges_created": total_edges,
            "analyzers_run": analyzers_run,
            "analyzers_skipped": analyzers_skipped,
            "analyzers_failed": analyzers_failed,
            "results": results,
            "duration_seconds": round(end_time - start_time, 2),
        }

    async def rebuild_graph(self, repository_id: UUID) -> dict[str, Any]:
        """Rebuild graph from scratch.

        Convenience method that ensures cleanup before building.

        Args:
            repository_id: UUID of repository to rebuild

        Returns:
            Build statistics dictionary
        """
        return await self.build_graph(repository_id, cleanup=True)

    async def update_graph(
        self, repository_id: UUID, relationship_types: list[str]
    ) -> dict[str, Any]:
        """Update specific relationship types in the graph.

        Useful for incremental updates after code changes.

        Args:
            repository_id: UUID of repository to update
            relationship_types: List of relationship types to update

        Returns:
            Build statistics dictionary
        """
        return await self.build_graph(
            repository_id, relationship_types=relationship_types, cleanup=True
        )

    def get_available_analyzers(self) -> list[str]:
        """Get list of available analyzer relationship types.

        Returns:
            List of relationship type strings
        """
        return self.registry.get_supported_relationship_types()

    def get_analyzer_count(self) -> int:
        """Get count of registered analyzers.

        Returns:
            Number of available analyzers
        """
        return self.registry.get_analyzer_count()
