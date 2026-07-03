"""RepositorySymbol database model."""

import uuid
from datetime import datetime

from sqlalchemy import UUID, Column, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import relationship

from app.db.base import Base


class RepositorySymbol(Base):
    """RepositorySymbol model for storing parsed symbol information.

    Stores metadata about symbols (functions, classes, variables, etc.) found
    during source code parsing. Contains location information and signatures
    but no source code content.
    """

    __tablename__ = "repository_symbols"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Foreign key to RepositoryFile
    repository_file_id = Column(
        UUID(as_uuid=True),
        ForeignKey("repository_files.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Reference to the file containing this symbol",
    )

    # Symbol identification
    symbol_name = Column(
        String(512),
        nullable=False,
        index=True,
        comment="Name of the symbol (function name, class name, variable name, etc.)",
    )
    symbol_type = Column(
        String(64),
        nullable=False,
        index=True,
        comment="Type of symbol: function, class, method, variable, import, etc.",
    )
    parent_symbol = Column(
        UUID(as_uuid=True),
        ForeignKey("repository_symbols.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        comment="Parent symbol (e.g., class containing a method)",
    )

    # Location information
    start_line = Column(
        Integer,
        nullable=False,
        comment="Starting line number (1-indexed)",
    )
    end_line = Column(
        Integer,
        nullable=False,
        comment="Ending line number (1-indexed)",
    )
    start_column = Column(
        Integer,
        nullable=True,
        comment="Starting column number (0-indexed)",
    )
    end_column = Column(
        Integer,
        nullable=True,
        comment="Ending column number (0-indexed)",
    )

    # Language and signature
    language = Column(
        String(32),
        nullable=False,
        index=True,
        comment="Programming language of the symbol",
    )
    signature = Column(
        Text,
        nullable=True,
        comment="Signature of the symbol (function signature, type signature, etc.)",
    )

    # Metadata
    symbol_metadata = Column(
        "metadata",
        Text,
        nullable=True,
        comment="JSON metadata about the symbol (access modifiers, type hints, etc.)",
    )
    created_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        comment="Timestamp when the symbol was recorded",
    )

    # Relationships
    repository_file = relationship(
        "RepositoryFile",
        back_populates="symbols",
        lazy="selectin",
    )
    parent = relationship(
        "RepositorySymbol",
        remote_side=[id],
        backref="children",
        foreign_keys=[parent_symbol],
        lazy="selectin",
    )

    # Indexes
    __table_args__ = (
        Index(
            "ix_repository_symbols_repository_file_id_symbol_type",
            "repository_file_id",
            "symbol_type",
        ),
        Index(
            "ix_repository_symbols_language_symbol_type",
            "language",
            "symbol_type",
        ),
        Index(
            "ix_repository_symbols_location",
            "repository_file_id",
            "start_line",
            "end_line",
        ),
        Index(
            "ix_repository_symbols_created_at",
            "created_at",
        ),
    )

    def __repr__(self) -> str:
        """String representation of the RepositorySymbol."""
        return f"<RepositorySymbol {self.symbol_name} ({self.symbol_type}) in {self.language}>"
