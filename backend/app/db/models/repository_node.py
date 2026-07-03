"""RepositoryNode database model."""

import uuid
from datetime import datetime

from sqlalchemy import UUID, Column, DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.orm import relationship

from app.db.base import Base


class RepositoryNode(Base):
    """RepositoryNode model for knowledge graph nodes.

    Represents nodes in the repository knowledge graph. A node can represent:
    - Repository (root node)
    - File/Module
    - Symbol (function, class, method, etc.)

    Nodes are linked together via RepositoryEdge to form the complete graph.
    """

    __tablename__ = "repository_nodes"

    # Primary key
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
        comment="Unique identifier for the node",
    )

    # Foreign keys (nullable to support different node types)
    repository_id = Column(
        UUID(as_uuid=True),
        ForeignKey("repositories.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Reference to the repository this node belongs to",
    )
    repository_file_id = Column(
        UUID(as_uuid=True),
        ForeignKey("repository_files.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        comment="Reference to file (if node represents a file or symbol in a file)",
    )
    symbol_id = Column(
        UUID(as_uuid=True),
        ForeignKey("repository_symbols.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        comment="Reference to symbol (if node represents a code symbol)",
    )

    # Node identification
    node_type = Column(
        String(64),
        nullable=False,
        index=True,
        comment="Type of node: repository, file, module, symbol",
    )
    display_name = Column(
        String(512),
        nullable=False,
        index=True,
        comment="Human-readable name for the node",
    )
    language = Column(
        String(32),
        nullable=True,
        index=True,
        comment="Programming language (for file and symbol nodes)",
    )

    # Node metadata
    node_metadata = Column(
        "metadata",
        Text,
        nullable=True,
        comment="JSON metadata for the node (type-specific properties)",
    )

    # Timestamps
    created_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        server_default=func.now(),
        comment="Timestamp when the node was created",
    )

    # Relationships
    repository = relationship(
        "Repository",
        foreign_keys=[repository_id],
        lazy="selectin",
    )
    repository_file = relationship(
        "RepositoryFile",
        foreign_keys=[repository_file_id],
        lazy="selectin",
    )
    symbol = relationship(
        "RepositorySymbol",
        foreign_keys=[symbol_id],
        lazy="selectin",
    )

    # Indexes
    __table_args__ = (
        Index(
            "ix_repository_nodes_repository_id_node_type",
            "repository_id",
            "node_type",
        ),
        Index(
            "ix_repository_nodes_repository_id_language",
            "repository_id",
            "language",
        ),
        Index(
            "ix_repository_nodes_symbol_id_node_type",
            "symbol_id",
            "node_type",
        ),
    )

    def __repr__(self) -> str:
        """String representation of the RepositoryNode."""
        return f"<RepositoryNode {self.node_type}: {self.display_name}>"
