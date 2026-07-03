"""Graph analyzer registry.

Central registry for all graph analyzers. Manages analyzer lifecycle,
execution order, and provides discovery mechanisms.
"""

from typing import Type

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.graph.graph_interface import GraphInterface


class GraphRegistry:
    """Registry for graph analyzers.

    Maintains a collection of registered graph analyzers and provides
    methods to discover, instantiate, and execute them in the correct order.
    """

    def __init__(self) -> None:
        """Initialize the registry with an empty analyzer collection."""
        self._analyzers: dict[str, Type[GraphInterface]] = {}

    def register(self, analyzer_class: Type[GraphInterface]) -> None:
        """Register a graph analyzer class.

        Args:
            analyzer_class: Class that implements GraphInterface

        Raises:
            ValueError: If analyzer with same relationship_type already registered
        """
        # Create a temporary instance to get the relationship type
        # We can't instantiate without a session, so we need a way to get the type
        # For now, we'll use the class name as a fallback
        relationship_type = getattr(
            analyzer_class, "_relationship_type", analyzer_class.__name__
        )

        if relationship_type in self._analyzers:
            existing = self._analyzers[relationship_type]
            raise ValueError(
                f"Analyzer for '{relationship_type}' already registered: {existing.__name__}"
            )

        self._analyzers[relationship_type] = analyzer_class

    def unregister(self, relationship_type: str) -> None:
        """Unregister an analyzer by relationship type.

        Args:
            relationship_type: Type of relationship to unregister

        Raises:
            KeyError: If analyzer not found
        """
        if relationship_type not in self._analyzers:
            raise KeyError(f"No analyzer registered for '{relationship_type}'")

        del self._analyzers[relationship_type]

    def get_analyzer(
        self, relationship_type: str, session: AsyncSession
    ) -> GraphInterface:
        """Get an analyzer instance by relationship type.

        Args:
            relationship_type: Type of relationship analyzer handles
            session: Database session to pass to analyzer

        Returns:
            Instantiated analyzer

        Raises:
            KeyError: If analyzer not found
        """
        if relationship_type not in self._analyzers:
            raise KeyError(f"No analyzer registered for '{relationship_type}'")

        analyzer_class = self._analyzers[relationship_type]
        return analyzer_class(session)

    def get_all_analyzers(self, session: AsyncSession) -> list[GraphInterface]:
        """Get instances of all registered analyzers.

        Args:
            session: Database session to pass to analyzers

        Returns:
            List of analyzer instances, sorted by priority
        """
        analyzers = [
            analyzer_class(session) for analyzer_class in self._analyzers.values()
        ]

        # Sort by priority (lower numbers first)
        return sorted(analyzers, key=lambda a: a.get_priority())

    def get_supported_relationship_types(self) -> list[str]:
        """Get list of all supported relationship types.

        Returns:
            List of relationship type strings
        """
        return list(self._analyzers.keys())

    def has_analyzer(self, relationship_type: str) -> bool:
        """Check if an analyzer is registered for a relationship type.

        Args:
            relationship_type: Type to check

        Returns:
            True if analyzer exists, False otherwise
        """
        return relationship_type in self._analyzers

    def clear(self) -> None:
        """Clear all registered analyzers.

        Useful for testing or dynamic reconfiguration.
        """
        self._analyzers.clear()

    def get_analyzer_count(self) -> int:
        """Get count of registered analyzers.

        Returns:
            Number of registered analyzers
        """
        return len(self._analyzers)


# Global registry instance
_global_registry = GraphRegistry()


def get_registry() -> GraphRegistry:
    """Get the global graph analyzer registry.

    Returns:
        Global GraphRegistry instance
    """
    return _global_registry


def register_analyzer(analyzer_class: Type[GraphInterface]) -> None:
    """Register an analyzer in the global registry.

    Convenience function for registering analyzers.

    Args:
        analyzer_class: Analyzer class to register
    """
    _global_registry.register(analyzer_class)
