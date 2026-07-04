"""Pydantic schemas for repository chunks.

These schemas define the data structures for chunking operations,
providing validation, serialization, and type safety.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class ChunkContext(BaseModel):
    """Context information for a chunk.

    Represents the surrounding context needed to understand a chunk,
    including imports, parent definitions, and related code.
    """

    imports: list[str] = Field(
        default_factory=list,
        description="Import statements needed by this chunk",
    )
    parent_definition: str | None = Field(
        default=None,
        description="Parent class/module definition if chunk is a method/nested element",
    )
    dependencies: list[UUID] = Field(
        default_factory=list,
        description="UUIDs of symbols this chunk depends on",
    )
    related_chunks: list[UUID] = Field(
        default_factory=list,
        description="UUIDs of related chunks for context expansion",
    )
    docstring: str | None = Field(
        default=None,
        description="Docstring or documentation for the chunk",
    )
    decorators: list[str] = Field(
        default_factory=list,
        description="Decorators applied to the symbol (Python, Java annotations, etc.)",
    )
    context_before: str | None = Field(
        default=None,
        description="Code context appearing before the chunk",
    )
    context_after: str | None = Field(
        default=None,
        description="Code context appearing after the chunk",
    )

    class Config:
        """Pydantic configuration."""

        json_schema_extra = {
            "example": {
                "imports": ["from typing import List", "import json"],
                "parent_definition": "class MyClass:",
                "dependencies": ["550e8400-e29b-41d4-a716-446655440000"],
                "related_chunks": ["660e8400-e29b-41d4-a716-446655440000"],
                "docstring": "Calculate the total of all items.",
                "decorators": ["@staticmethod", "@lru_cache"],
                "context_before": "# Helper functions",
                "context_after": "# End of helper section",
            }
        }


class ChunkMetadata(BaseModel):
    """Metadata for a chunk.

    Type-specific metadata that varies based on chunk_type.
    Provides rich information about the chunk's structure and relationships.
    """

    # Symbol information (for function, method, class chunks)
    symbol_type: str | None = Field(
        default=None,
        description="Type of symbol: function, method, class, interface, etc.",
    )
    signature: str | None = Field(
        default=None,
        description="Function/method signature or class definition",
    )
    parameters: list[str] = Field(
        default_factory=list,
        description="Function/method parameters",
    )
    return_type: str | None = Field(
        default=None,
        description="Return type annotation if available",
    )

    # Location information
    start_line: int | None = Field(
        default=None,
        ge=1,
        description="Starting line number in the source file",
    )
    end_line: int | None = Field(
        default=None,
        ge=1,
        description="Ending line number in the source file",
    )
    start_column: int | None = Field(
        default=None,
        ge=0,
        description="Starting column number in the source file",
    )
    end_column: int | None = Field(
        default=None,
        ge=0,
        description="Ending column number in the source file",
    )

    # Relationships (graph linkage)
    parent_symbol_id: UUID | None = Field(
        default=None,
        description="UUID of parent symbol (e.g., class for a method)",
    )
    node_id: UUID | None = Field(
        default=None,
        description="UUID of corresponding knowledge graph node",
    )
    calls: list[UUID] = Field(
        default_factory=list,
        description="UUIDs of symbols this chunk calls/references",
    )
    called_by: list[UUID] = Field(
        default_factory=list,
        description="UUIDs of symbols that call this chunk",
    )

    # Class-specific metadata
    inherits_from: list[str] = Field(
        default_factory=list,
        description="Base classes this class inherits from",
    )
    implements: list[str] = Field(
        default_factory=list,
        description="Interfaces this class implements",
    )
    method_count: int | None = Field(
        default=None,
        ge=0,
        description="Number of methods in a class",
    )
    is_abstract: bool = Field(
        default=False,
        description="Whether the class/method is abstract",
    )

    # Test-specific metadata
    test_framework: str | None = Field(
        default=None,
        description="Testing framework (pytest, jest, junit, etc.)",
    )
    tests_symbol_id: UUID | None = Field(
        default=None,
        description="UUID of symbol being tested",
    )
    assertion_count: int | None = Field(
        default=None,
        ge=0,
        description="Number of assertions in test",
    )

    # Access and modifiers
    access_modifier: str | None = Field(
        default=None,
        description="Access modifier: public, private, protected",
    )
    is_static: bool = Field(
        default=False,
        description="Whether the symbol is static",
    )
    is_async: bool = Field(
        default=False,
        description="Whether the function/method is async",
    )

    # Additional metadata
    complexity_score: float | None = Field(
        default=None,
        ge=0.0,
        description="Cyclomatic complexity or similar metric",
    )
    has_examples: bool = Field(
        default=False,
        description="Whether documentation contains code examples",
    )
    tags: list[str] = Field(
        default_factory=list,
        description="Custom tags for categorization",
    )
    custom: dict[str, Any] = Field(
        default_factory=dict,
        description="Language-specific or custom metadata",
    )

    @field_validator("end_line")
    @classmethod
    def end_line_after_start(cls, v: int | None, info) -> int | None:
        """Validate that end_line is after start_line."""
        if v is not None and info.data.get("start_line") is not None:
            if v < info.data["start_line"]:
                raise ValueError("end_line must be >= start_line")
        return v

    class Config:
        """Pydantic configuration."""

        json_schema_extra = {
            "example": {
                "symbol_type": "method",
                "signature": "def calculate_total(self, items: List[float]) -> float:",
                "parameters": ["self", "items"],
                "return_type": "float",
                "start_line": 42,
                "end_line": 58,
                "parent_symbol_id": "550e8400-e29b-41d4-a716-446655440000",
                "node_id": "660e8400-e29b-41d4-a716-446655440000",
                "calls": ["770e8400-e29b-41d4-a716-446655440000"],
                "access_modifier": "public",
                "is_async": False,
                "complexity_score": 3.5,
                "tags": ["business-logic", "calculations"],
            }
        }


class ChunkResult(BaseModel):
    """Result of a chunking operation.

    Represents a generated chunk with all its properties and metadata.
    Used for returning chunk data from services and APIs.
    """

    # Core identification
    id: UUID | None = Field(
        default=None,
        description="Unique identifier (populated after persistence)",
    )
    repository_id: UUID = Field(
        description="UUID of the repository this chunk belongs to",
    )
    repository_file_id: UUID | None = Field(
        default=None,
        description="UUID of the file this chunk is from",
    )
    symbol_id: UUID | None = Field(
        default=None,
        description="UUID of the symbol this chunk represents",
    )

    # Chunk properties
    chunk_type: str = Field(
        description="Type of chunk: function, method, class, imports, interface, test, documentation, configuration",
    )
    chunk_name: str = Field(
        min_length=1,
        max_length=512,
        description="Human-readable name for the chunk",
    )
    language: str = Field(
        min_length=1,
        max_length=32,
        description="Programming language of the chunk",
    )

    # Content
    content: str = Field(
        min_length=1,
        description="The actual chunk content (code with context)",
    )

    # Metrics
    token_count: int = Field(
        ge=0,
        description="Approximate token count for LLM processing",
    )
    content_hash: str = Field(
        min_length=64,
        max_length=64,
        description="SHA256 hash of content for deduplication",
    )

    # Rich metadata
    metadata: ChunkMetadata = Field(
        description="Detailed metadata about the chunk",
    )
    context: ChunkContext | None = Field(
        default=None,
        description="Context information for the chunk",
    )

    # Timestamps
    created_at: datetime | None = Field(
        default=None,
        description="When the chunk was created",
    )

    @field_validator("chunk_type")
    @classmethod
    def validate_chunk_type(cls, v: str) -> str:
        """Validate chunk_type is one of the allowed values."""
        allowed_types = {
            "function",
            "method",
            "class",
            "imports",
            "interface",
            "test",
            "documentation",
            "configuration",
        }
        if v not in allowed_types:
            raise ValueError(f"chunk_type must be one of {allowed_types}, got '{v}'")
        return v

    @field_validator("content_hash")
    @classmethod
    def validate_hash_format(cls, v: str) -> str:
        """Validate content_hash is a valid SHA256 hex string."""
        if not all(c in "0123456789abcdef" for c in v.lower()):
            raise ValueError("content_hash must be a valid hexadecimal string")
        return v.lower()

    class Config:
        """Pydantic configuration."""

        from_attributes = True  # Allow creation from ORM models
        json_schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "repository_id": "660e8400-e29b-41d4-a716-446655440000",
                "repository_file_id": "770e8400-e29b-41d4-a716-446655440000",
                "symbol_id": "880e8400-e29b-41d4-a716-446655440000",
                "chunk_type": "function",
                "chunk_name": "calculate_total",
                "language": "python",
                "content": "def calculate_total(items: List[float]) -> float:\n    \"\"\"Calculate sum of items.\"\"\"\n    return sum(items)",
                "token_count": 42,
                "content_hash": "a" * 64,
                "metadata": {
                    "symbol_type": "function",
                    "signature": "def calculate_total(items: List[float]) -> float:",
                    "parameters": ["items"],
                    "return_type": "float",
                    "start_line": 10,
                    "end_line": 13,
                },
                "context": {
                    "imports": ["from typing import List"],
                    "docstring": "Calculate sum of items.",
                },
                "created_at": "2026-07-04T00:56:00Z",
            }
        }


class ChunkRelationship(BaseModel):
    """Relationship between two chunks.

    Represents semantic or structural connections between chunks,
    enabling context expansion and related code discovery.
    """

    # Identification
    id: UUID | None = Field(
        default=None,
        description="Unique identifier (populated after persistence)",
    )
    source_chunk_id: UUID = Field(
        description="UUID of the source chunk",
    )
    target_chunk_id: UUID = Field(
        description="UUID of the target chunk",
    )

    # Relationship type
    relationship_type: str = Field(
        description="Type of relationship between chunks",
    )
    relationship_strength: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Strength of the relationship (0.0-1.0) for ranking",
    )

    # Relationship metadata
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata about the relationship",
    )

    # Timestamps
    created_at: datetime | None = Field(
        default=None,
        description="When the relationship was created",
    )

    @field_validator("relationship_type")
    @classmethod
    def validate_relationship_type(cls, v: str) -> str:
        """Validate relationship_type is one of the allowed values."""
        allowed_types = {
            "calls",
            "called_by",
            "imports",
            "imported_by",
            "inherits",
            "inherited_by",
            "implements",
            "implemented_by",
            "tests",
            "tested_by",
            "documents",
            "documented_by",
            "references",
            "referenced_by",
            "contains",
            "contained_by",
            "similar_to",
            "depends_on",
            "depended_by",
        }
        if v not in allowed_types:
            raise ValueError(f"relationship_type must be one of {allowed_types}, got '{v}'")
        return v

    @field_validator("source_chunk_id", "target_chunk_id")
    @classmethod
    def validate_different_chunks(cls, v: UUID, info) -> UUID:
        """Validate that source and target are different chunks."""
        if info.field_name == "target_chunk_id":
            source = info.data.get("source_chunk_id")
            if source and v == source:
                raise ValueError("source_chunk_id and target_chunk_id must be different")
        return v

    class Config:
        """Pydantic configuration."""

        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "990e8400-e29b-41d4-a716-446655440000",
                "source_chunk_id": "550e8400-e29b-41d4-a716-446655440000",
                "target_chunk_id": "660e8400-e29b-41d4-a716-446655440000",
                "relationship_type": "calls",
                "relationship_strength": 0.95,
                "metadata": {
                    "call_count": 5,
                    "is_direct": True,
                    "call_type": "method_call",
                },
                "created_at": "2026-07-04T00:56:00Z",
            }
        }


# Type aliases for convenience
ChunkMetadataDict = dict[str, Any]
ChunkContextDict = dict[str, Any]

