"""RepositoryRelationshipType enum."""

from enum import Enum


class RepositoryRelationshipType(str, Enum):
    """Enum for repository knowledge graph relationship types.

    Defines the types of relationships that can exist between nodes
    in the repository knowledge graph.
    """

    # Containment relationships
    CONTAINS = "CONTAINS"  # Repository → File, File → Symbol, Class → Method

    # Import/Export relationships
    IMPORTS = "IMPORTS"  # File → File, Symbol → Symbol
    EXPORTS = "EXPORTS"  # File → Symbol

    # Call relationships
    CALLS = "CALLS"  # Function → Function, Method → Method/Function

    # Inheritance relationships
    INHERITS = "INHERITS"  # Class → Class, Class → Interface
    IMPLEMENTS = "IMPLEMENTS"  # Class → Interface

    # Reference relationships
    REFERENCES = "REFERENCES"  # Symbol → Symbol (general reference)
    DEFINES = "DEFINES"  # Function → Variable, Class → Field

    # Dependency relationships
    DEPENDS_ON = "DEPENDS_ON"  # File → File, Symbol → Symbol

    # Module relationships
    BELONGS_TO = "BELONGS_TO"  # File → Module, Symbol → Module

    def __str__(self) -> str:
        """Return the string value of the enum."""
        return self.value
