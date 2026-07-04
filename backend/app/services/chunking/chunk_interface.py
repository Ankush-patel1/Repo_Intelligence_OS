"""Abstract interfaces for chunking system.

Defines the core contracts that all chunking components must follow.
These interfaces enable flexible strategy implementation and testing.
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any
from uuid import UUID

from app.schemas.chunk import ChunkContext, ChunkMetadata, ChunkResult


class ChunkStrategyType(Enum):
    """Available chunking strategies."""

    SYMBOL_LEVEL = "symbol-level"  # Individual functions, methods, classes
    LOGICAL_UNIT = "logical-unit"  # Related symbol groups, test suites
    FILE_LEVEL = "file-level"  # Complete files or file sections
    MODULE_LEVEL = "module-level"  # Package/module aggregations
    AUTO = "auto"  # Automatically determine best strategy


class ChunkInterface(ABC):
    """Interface for chunk generation components.

    All chunk generators must implement this interface to ensure
    consistent behavior across different chunking strategies.
    """

    @abstractmethod
    async def generate_chunks(
        self,
        content: str,
        file_id: UUID,
        repository_id: UUID,
        metadata: dict[str, Any],
    ) -> list[ChunkResult]:
        """Generate chunks from content.

        Args:
            content: Source code or text to chunk
            file_id: UUID of the source file
            repository_id: UUID of the repository
            metadata: Additional metadata about the source

        Returns:
            List of generated chunks with metadata
        """
        pass

    @abstractmethod
    async def validate_chunk(self, chunk: ChunkResult) -> bool:
        """Validate a chunk meets quality criteria.

        Args:
            chunk: The chunk to validate

        Returns:
            True if chunk is valid, False otherwise
        """
        pass

    @abstractmethod
    def estimate_token_count(self, content: str) -> int:
        """Estimate token count for content.

        Args:
            content: Text to count tokens for

        Returns:
            Estimated token count
        """
        pass


class ChunkStrategy(ABC):
    """Abstract base class for chunking strategies.

    Each strategy implements a different approach to dividing
    code into semantically meaningful chunks.
    """

    strategy_type: ChunkStrategyType

    @abstractmethod
    async def should_apply(
        self,
        file_metadata: dict[str, Any],
        symbol_count: int,
        file_size: int,
    ) -> bool:
        """Determine if this strategy should be applied.

        Args:
            file_metadata: Metadata about the file
            symbol_count: Number of symbols in the file
            file_size: Size of the file in bytes

        Returns:
            True if this strategy is appropriate, False otherwise
        """
        pass

    @abstractmethod
    async def calculate_boundaries(
        self,
        symbols: list[dict[str, Any]],
        file_content: str,
    ) -> list[tuple[int, int, dict[str, Any]]]:
        """Calculate chunk boundaries.

        Args:
            symbols: List of parsed symbols from the file
            file_content: Complete file content

        Returns:
            List of (start_line, end_line, metadata) tuples
        """
        pass

    @abstractmethod
    async def build_context(
        self,
        symbol: dict[str, Any],
        file_content: str,
        all_symbols: list[dict[str, Any]],
    ) -> ChunkContext:
        """Build context for a chunk.

        Args:
            symbol: The symbol being chunked
            file_content: Complete file content
            all_symbols: All symbols in the file for relationship detection

        Returns:
            Context object with imports, dependencies, etc.
        """
        pass

    @abstractmethod
    async def extract_metadata(
        self,
        symbol: dict[str, Any],
        chunk_content: str,
    ) -> ChunkMetadata:
        """Extract metadata from a chunk.

        Args:
            symbol: The symbol data from parser
            chunk_content: The chunk content

        Returns:
            Metadata object with detailed chunk information
        """
        pass

    @abstractmethod
    def get_priority(self) -> int:
        """Get strategy priority for auto-selection.

        Returns:
            Priority value (higher = more preferred)
        """
        pass


class ContextProvider(ABC):
    """Interface for providing context information to chunks."""

    @abstractmethod
    async def get_imports(self, file_id: UUID) -> list[str]:
        """Get import statements for a file.

        Args:
            file_id: UUID of the file

        Returns:
            List of import statement strings
        """
        pass

    @abstractmethod
    async def get_parent_context(
        self, symbol_id: UUID
    ) -> tuple[str | None, UUID | None]:
        """Get parent context for a symbol.

        Args:
            symbol_id: UUID of the symbol

        Returns:
            Tuple of (parent_definition, parent_symbol_id)
        """
        pass

    @abstractmethod
    async def get_dependencies(self, symbol_id: UUID) -> list[UUID]:
        """Get symbols this symbol depends on.

        Args:
            symbol_id: UUID of the symbol

        Returns:
            List of dependency symbol UUIDs
        """
        pass

    @abstractmethod
    async def get_related_chunks(
        self, chunk_id: UUID, relationship_type: str | None = None
    ) -> list[UUID]:
        """Get related chunks.

        Args:
            chunk_id: UUID of the chunk
            relationship_type: Optional filter by relationship type

        Returns:
            List of related chunk UUIDs
        """
        pass


class ChunkValidator(ABC):
    """Interface for chunk validation."""

    @abstractmethod
    async def validate_size(
        self, chunk: ChunkResult, min_tokens: int, max_tokens: int
    ) -> bool:
        """Validate chunk size is within bounds.

        Args:
            chunk: The chunk to validate
            min_tokens: Minimum acceptable token count
            max_tokens: Maximum acceptable token count

        Returns:
            True if size is valid
        """
        pass

    @abstractmethod
    async def validate_content(self, chunk: ChunkResult) -> bool:
        """Validate chunk content is complete and syntactically valid.

        Args:
            chunk: The chunk to validate

        Returns:
            True if content is valid
        """
        pass

    @abstractmethod
    async def validate_metadata(self, chunk: ChunkResult) -> bool:
        """Validate chunk metadata is complete.

        Args:
            chunk: The chunk to validate

        Returns:
            True if metadata is valid
        """
        pass

    @abstractmethod
    async def validate_relationships(self, chunk: ChunkResult) -> list[str]:
        """Validate chunk relationships exist.

        Args:
            chunk: The chunk to validate

        Returns:
            List of validation warnings (empty if all valid)
        """
        pass


