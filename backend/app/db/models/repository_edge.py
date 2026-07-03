"""RepositoryEdge database model."""

import uuid
from datetime import datetime

from sqlalchemy import UUID, Column, DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.orm import relationship

from app.db.base import Base


class RepositoryEdge(Base):
    """RepositoryEdge model for knowledge graph edges.

    Represents directed edges (relationships) between nodes in the repository
    knowledge graph. Each edge connects a source node to a target node with
    a specific relationship type.

    Examples:
    - File IMPORTS File
    - Function CALLS Function
    - Class INHERITS Class
    - Symbol REFERENCES Symbol
    """

    __tablename__ = "repository_edges"

    # Primary key
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
        comment="Unique identifier for the edge",
    )

    # Foreign keys (source and target nodes)
    source_node_id = Column(
        UUID(as_uuid=True),
        ForeignKey("repository_nodes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Reference to the source node of this relationship",
    )
    target_node_id = Column(
        UUID(as_uuid=True),
        ForeignKey("repository_nodes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Reference to the target node of this relationship",
    )

    # Relationship type
    relationship_type = Column(
        String(64),
        nullable=False,
        index=True,
        comment="Type of relationship (IMPORTS, CALLS, INHERITS, REFERENCES, etc.)",
    )

    # Edge metadata
    edge_metadata = Column(
        "metadata",
        Text,
        nullable=True,
        comment="JSON metadata for the edge (relationship-specific properties)",
    )

    # Timestamps
    created_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        server_default=func.now(),
        comment="Timestamp when the edge was created",
    )

    # Relationships
    source_node = relationship(
        "RepositoryNode",
        foreign_keys=[source_node_id],
        lazy="selectin",
    )
    target_node = relationship(
        "RepositoryNode",
        foreign_keys=[target_node_id],
        lazy="selectin",
    )

    # Indexes
    __table_args__ = (
        Index(
            "ix_repository_edges_source_node_id_relationship_type",
            "source_node_id",
            "relationship_type",
        ),
        Index(
            "ix_repository_edges_target_node_id_relationship_type",
            "target_node_id",
            "relationship_type",
        ),
        Index(
            "ix_repository_edges_source_target",
            "source_node_id",
            "target_node_id",
        ),
        Index(
            "ix_repository_edges_relationship_type_created_at",
            "relationship_type",
            "created_at",
        ),
    )

    def __repr__(self) -> str:
        """String representation of the RepositoryEdge."""
        return f"<RepositoryEdge {self.relationship_type}: {self.source_node_id} → {self.target_node_id}>"
