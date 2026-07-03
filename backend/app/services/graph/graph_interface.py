"""Graph interface for repository knowledge graph operations.

Defines the abstract interface for graph analyzers that extract
relationships from repository data.
"""

from abc import ABC, abstractmethod
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession


class GraphInterface(ABC):
    """Abstract base class for graph analyzers.

    Graph analyzers implement specific relationship extraction logic
    (imports, calls, inheritance, etc.) and register with the GraphRegistry.
    Each analyzer is responsible for one type of relationship.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the graph analyzer.

        Args:
            session: Database session for queries and persistence
        """
        self.session = session

    @property
    @abstractmethod
    def relationship_type(self) -> str:
        """Return the relationship type this analyzer handles.

        Returns:
            Relationship type string (e.g., "IMPORTS", "CALLS", "INHERITS")
        """
        pass

    @property
    @abstractmethod
    def supported_languages(self) -> list[str]:
        """Return list of programming languages this analyzer supports.

        Returns:
            List of language names, or ["*"] for all languages
        """
        pass

    @abstractmethod
    async def analyze(self, repository_id: UUID) -> dict[str, Any]:
        """Analyze repository and extract relationships.

        This method should:
        1. Query necessary data (symbols, files, etc.)
        2. Extract relationships based on analyzer logic
        3. Create nodes and edges in the graph
        4. Return statistics about what was created

        Args:
            repository_id: UUID of the repository to analyze

        Returns:
            Dictionary with analysis statistics:
            {
                "relationship_type": str,
                "nodes_created": int,
                "edges_created": int,
                "files_analyzed": int,
                "symbols_analyzed": int,
                "errors": list[str],
            }
        """
        pass

    @abstractmethod
    async def can_analyze(self, repository_id: UUID) -> bool:
        """Check if this analyzer can process the repository.

        Determines if the repository has the necessary data (symbols, files)
        for this analyzer to run.

        Args:
            repository_id: UUID of the repository to check

        Returns:
            True if analyzer can run, False otherwise
        """
        pass

    async def cleanup(self, repository_id: UUID) -> int:
        """Clean up existing relationships before re-analyzing.

        Optional method for analyzers to remove stale relationships
        before creating new ones.

        Args:
            repository_id: UUID of the repository to clean

        Returns:
            Number of relationships removed
        """
        return 0

    def get_priority(self) -> int:
        """Get execution priority for this analyzer.

        Analyzers with lower priority numbers run first.
        Useful for ensuring dependency order (e.g., file nodes before imports).

        Returns:
            Priority number (default: 100)
        """
        return 100
