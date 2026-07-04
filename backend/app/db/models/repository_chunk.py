"""RepositoryChunk database model."""

import uuid
from datetime import datetime

from sqlalchemy import UUID, BigInteger, Column, DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.orm import relationship

from app.db.base import Base


class RepositoryChunk(Base):
    """RepositoryChunk model for semantic chunks of repository content.

    Stores intelligently chunked code segments optimized for RAG/LLM processing.
    Chunks are created from parsed symbols with semantic boundaries and context.
    """

    __tablename__ = "repository_chunks"

    # Primary key
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
        comment="Unique identifier for the chunk",
    )

    # Foreign keys
    repository_id = Column(
        UUID(as_uuid=True),
        ForeignKey("repositories.id", ondelete="CASCADE"),
        nullable=False,
        comment="Reference to the repository this chunk belongs to",
    )
    repository_file_id = Column(
        UUID(as_uuid=True),
        ForeignKey("repository_files.id", ondelete="CASCADE"),
        nullable=True,
        comment="Reference to the file this chunk is from (if applicable)",
    )
    symbol_id = Column(
        UUID(as_uuid=True),
        ForeignKey("repository_symbols.id", ondelete="CASCADE"),
        nullable=True,
        comment="Reference to the symbol this chunk represents (if applicable)",
    )

    # Chunk identification
    chunk_type = Column(
        String(64),
        nullable=False,
        comment="Type of chunk: function, method, class, imports, interface, test, documentation, configuration",
    )
    chunk_name = Column(
        String(512),
        nullable=False,
        comment="Human-readable name for the chunk (function name, class name, etc.)",
    )

    # Language
    language = Column(
        String(32),
        nullable=False,
        comment="Programming language of the chunk",
    )

    # Content
    content = Column(
        Text,
        nullable=False,
        comment="The actual chunk content (code with context)",
    )

    # Metadata
    chunk_metadata = Column(
        "metadata",
        Text,
        nullable=True,
        comment="JSON metadata for the chunk (type-specific properties, context info, relationships)",
    )

    # Size metrics
    token_count = Column(
        BigInteger,
        nullable=False,
        comment="Approximate token count for the chunk (for LLM processing)",
    )

    # Deduplication
    content_hash = Column(
        String(64),
        nullable=False,
        comment="SHA256 hash of content for deduplication",
    )

    # Timestamps
    created_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        server_default=func.now(),
        comment="Timestamp when the chunk was created",
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
            "ix_repository_chunks_repository_id_chunk_type",
            "repository_id",
            "chunk_type",
        ),
        Index(
            "ix_repository_chunks_repository_id_language",
            "repository_id",
            "language",
        ),
        Index(
            "ix_repository_chunks_file_id_chunk_type",
            "repository_file_id",
            "chunk_type",
        ),
        Index(
            "ix_repository_chunks_symbol_id",
            "symbol_id",
        ),
        Index(
            "ix_repository_chunks_content_hash",
            "content_hash",
        ),
        Index(
            "ix_repository_chunks_token_count",
            "token_count",
        ),
        Index(
            "ix_repository_chunks_language_chunk_type",
            "language",
            "chunk_type",
        ),
        Index(
            "ix_repository_chunks_created_at",
            "created_at",
        ),
    )

    def __repr__(self) -> str:
        """String representation of the RepositoryChunk."""
        return f"<RepositoryChunk {self.chunk_type}: {self.chunk_name} ({self.language})>"

