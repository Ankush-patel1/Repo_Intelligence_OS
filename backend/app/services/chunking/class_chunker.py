"""Class-based semantic chunking implementation.

Creates semantic chunks from class symbols, including:
- Class definition
- Methods
- Import statements
- Called symbols
- Graph relationships
"""

import hashlib
import json
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models.repository_edge import RepositoryEdge
from app.db.models.repository_file import RepositoryFile
from app.db.models.repository_node import RepositoryNode
from app.db.models.repository_symbol import RepositorySymbol
from app.schemas.chunk import ChunkContext, ChunkMetadata, ChunkResult


class ClassChunker:
    """Creates semantic chunks from class symbols.

    Processes class symbols and generates comprehensive chunks containing:
    - The class definition and all methods
    - Import statements needed by the class
    - Relationships to other symbols (calls, inheritance)
    - Graph node and edge information
    """

    def __init__(self, session: AsyncSession):
        """Initialize class chunker.

        Args:
            session: Database session for querying models
        """
        self.session = session

    async def chunk_class(
        self,
        class_symbol_id: UUID,
    ) -> ChunkResult:
        """Create a semantic chunk from a class symbol.

        Args:
            class_symbol_id: UUID of the class symbol to chunk

        Returns:
            ChunkResult containing the complete class chunk

        Raises:
            ValueError: If symbol not found or not a class
        """
        # Fetch the class symbol with relationships
        class_symbol = await self._fetch_class_symbol(class_symbol_id)

        if not class_symbol:
            raise ValueError(f"Class symbol {class_symbol_id} not found")

        if class_symbol.symbol_type not in ("class", "interface"):
            raise ValueError(
                f"Symbol {class_symbol_id} is not a class (type: {class_symbol.symbol_type})"
            )

        # Fetch related data
        file = class_symbol.repository_file
        file_content = await self._read_file_content(file.absolute_path)
        method_symbols = await self._fetch_method_symbols(class_symbol_id)
        graph_node = await self._fetch_graph_node(class_symbol_id)
        imports = await self._extract_imports(file.id)
        relationships = await self._fetch_relationships(graph_node.id) if graph_node else []

        # Extract class content
        content = self._extract_class_content(
            file_content, class_symbol, method_symbols
        )

        # Build context
        context = await self._build_class_context(
            imports, class_symbol, method_symbols, relationships
        )

        # Build metadata
        metadata = await self._build_class_metadata(
            class_symbol, method_symbols, graph_node, relationships
        )

        # Calculate metrics
        token_count = self._estimate_token_count(content)
        content_hash = self._calculate_content_hash(content)

        # Create chunk result
        chunk = ChunkResult(
            repository_id=file.repository_id,
            repository_file_id=file.id,
            symbol_id=class_symbol.id,
            chunk_type="class",
            chunk_name=class_symbol.symbol_name,
            language=class_symbol.language,
            content=content,
            token_count=token_count,
            content_hash=content_hash,
            metadata=metadata,
            context=context,
        )

        return chunk

    async def chunk_all_classes(
        self,
        repository_id: UUID,
    ) -> list[ChunkResult]:
        """Create chunks for all classes in a repository.

        Args:
            repository_id: UUID of the repository

        Returns:
            List of ChunkResult objects for all classes
        """
        # Fetch all class symbols in repository
        stmt = (
            select(RepositorySymbol)
            .join(RepositoryFile)
            .where(RepositoryFile.repository_id == repository_id)
            .where(RepositorySymbol.symbol_type.in_(["class", "interface"]))
            .options(selectinload(RepositorySymbol.repository_file))
        )

        result = await self.session.execute(stmt)
        class_symbols = result.scalars().all()

        # Chunk each class
        chunks = []
        for class_symbol in class_symbols:
            try:
                chunk = await self.chunk_class(class_symbol.id)
                chunks.append(chunk)
            except Exception as e:
                # Log error but continue processing other classes
                print(f"Error chunking class {class_symbol.symbol_name}: {e}")
                continue

        return chunks

    async def _fetch_class_symbol(
        self, class_symbol_id: UUID
    ) -> RepositorySymbol | None:
        """Fetch class symbol with relationships.

        Args:
            class_symbol_id: UUID of the class symbol

        Returns:
            RepositorySymbol or None if not found
        """
        stmt = (
            select(RepositorySymbol)
            .where(RepositorySymbol.id == class_symbol_id)
            .options(
                selectinload(RepositorySymbol.repository_file),
                selectinload(RepositorySymbol.parent),
            )
        )

        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def _fetch_method_symbols(
        self, class_symbol_id: UUID
    ) -> list[RepositorySymbol]:
        """Fetch all method symbols for a class.

        Args:
            class_symbol_id: UUID of the class symbol

        Returns:
            List of method RepositorySymbol objects
        """
        stmt = (
            select(RepositorySymbol)
            .where(RepositorySymbol.parent_symbol == class_symbol_id)
            .where(RepositorySymbol.symbol_type == "method")
            .order_by(RepositorySymbol.start_line)
        )

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def _fetch_graph_node(
        self, symbol_id: UUID
    ) -> RepositoryNode | None:
        """Fetch graph node for a symbol.

        Args:
            symbol_id: UUID of the symbol

        Returns:
            RepositoryNode or None if not found
        """
        stmt = select(RepositoryNode).where(RepositoryNode.symbol_id == symbol_id)

        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def _fetch_relationships(
        self, node_id: UUID
    ) -> list[tuple[RepositoryEdge, RepositoryNode]]:
        """Fetch outgoing edges and target nodes for a node.

        Args:
            node_id: UUID of the source node

        Returns:
            List of (edge, target_node) tuples
        """
        stmt = (
            select(RepositoryEdge, RepositoryNode)
            .where(RepositoryEdge.source_node_id == node_id)
            .join(
                RepositoryNode,
                RepositoryEdge.target_node_id == RepositoryNode.id,
            )
            .options(
                selectinload(RepositoryNode.symbol),
            )
        )

        result = await self.session.execute(stmt)
        return list(result.all())

    async def _extract_imports(self, file_id: UUID) -> list[str]:
        """Extract import statements from a file.

        Args:
            file_id: UUID of the file

        Returns:
            List of import statement strings
        """
        stmt = (
            select(RepositorySymbol)
            .where(RepositorySymbol.repository_file_id == file_id)
            .where(RepositorySymbol.symbol_type == "import")
            .order_by(RepositorySymbol.start_line)
        )

        result = await self.session.execute(stmt)
        import_symbols = result.scalars().all()

        imports = []
        for import_symbol in import_symbols:
            # Use signature if available, otherwise use symbol name
            import_stmt = import_symbol.signature or import_symbol.symbol_name
            imports.append(import_stmt)

        return imports

    async def _read_file_content(self, file_path: str) -> str:
        """Read file content from disk.

        Args:
            file_path: Absolute path to the file

        Returns:
            File content as string
        """
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            raise ValueError(f"Failed to read file {file_path}: {e}")

    def _extract_class_content(
        self,
        file_content: str,
        class_symbol: RepositorySymbol,
        method_symbols: list[RepositorySymbol],
    ) -> str:
        """Extract class content including all methods.

        Args:
            file_content: Complete file content
            class_symbol: The class symbol
            method_symbols: List of method symbols

        Returns:
            Extracted class content
        """
        lines = file_content.splitlines()

        # Validate line numbers
        if class_symbol.start_line < 1 or class_symbol.end_line > len(lines):
            raise ValueError(
                f"Invalid line range: {class_symbol.start_line}-{class_symbol.end_line} "
                f"(file has {len(lines)} lines)"
            )

        # Extract lines (convert from 1-indexed to 0-indexed)
        start_idx = class_symbol.start_line - 1
        end_idx = class_symbol.end_line  # end_line is inclusive, so no -1 needed

        class_lines = lines[start_idx:end_idx]
        return "\n".join(class_lines)

    async def _build_class_context(
        self,
        imports: list[str],
        class_symbol: RepositorySymbol,
        method_symbols: list[RepositorySymbol],
        relationships: list[tuple[RepositoryEdge, RepositoryNode]],
    ) -> ChunkContext:
        """Build context for a class chunk.

        Args:
            imports: List of import statements
            class_symbol: The class symbol
            method_symbols: List of method symbols
            relationships: List of (edge, target_node) tuples

        Returns:
            ChunkContext object
        """
        # Parse class metadata
        class_metadata = self._parse_metadata(class_symbol.symbol_metadata)

        # Extract docstring from metadata
        docstring = class_metadata.get("docstring")

        # Extract decorators from metadata
        decorators = class_metadata.get("decorators", [])

        # Get parent class definition if exists
        parent_definition = None
        if class_symbol.parent:
            parent_definition = class_symbol.parent.signature

        # Extract dependencies from relationships
        dependencies = []
        for edge, target_node in relationships:
            if edge.relationship_type in ("IMPORTS", "INHERITS", "IMPLEMENTS", "REFERENCES"):
                if target_node.symbol_id:
                    dependencies.append(target_node.symbol_id)

        # Related chunks would be method chunks (future implementation)
        related_chunks = []

        return ChunkContext(
            imports=imports,
            parent_definition=parent_definition,
            dependencies=dependencies,
            related_chunks=related_chunks,
            docstring=docstring,
            decorators=decorators,
        )

    async def _build_class_metadata(
        self,
        class_symbol: RepositorySymbol,
        method_symbols: list[RepositorySymbol],
        graph_node: RepositoryNode | None,
        relationships: list[tuple[RepositoryEdge, RepositoryNode]],
    ) -> ChunkMetadata:
        """Build metadata for a class chunk.

        Args:
            class_symbol: The class symbol
            method_symbols: List of method symbols
            graph_node: The graph node for this class
            relationships: List of (edge, target_node) tuples

        Returns:
            ChunkMetadata object
        """
        # Parse class metadata
        class_metadata = self._parse_metadata(class_symbol.symbol_metadata)

        # Extract inheritance information
        inherits_from = []
        implements = []
        calls = []
        called_by = []

        for edge, target_node in relationships:
            if edge.relationship_type == "INHERITS":
                inherits_from.append(target_node.display_name)
            elif edge.relationship_type == "IMPLEMENTS":
                implements.append(target_node.display_name)
            elif edge.relationship_type == "CALLS":
                if target_node.symbol_id:
                    calls.append(target_node.symbol_id)

        # Note: called_by would require fetching incoming edges
        # which we're not doing for performance reasons

        # Extract access modifier
        access_modifier = class_metadata.get("access_modifier")

        # Check if abstract
        is_abstract = class_metadata.get("is_abstract", False)

        return ChunkMetadata(
            symbol_type="class",
            signature=class_symbol.signature,
            start_line=class_symbol.start_line,
            end_line=class_symbol.end_line,
            start_column=class_symbol.start_column,
            end_column=class_symbol.end_column,
            parent_symbol_id=class_symbol.parent_symbol,
            node_id=graph_node.id if graph_node else None,
            calls=calls,
            called_by=called_by,
            inherits_from=inherits_from,
            implements=implements,
            method_count=len(method_symbols),
            is_abstract=is_abstract,
            access_modifier=access_modifier,
        )

    def _parse_metadata(self, metadata_json: str | None) -> dict[str, Any]:
        """Parse JSON metadata string.

        Args:
            metadata_json: JSON string or None

        Returns:
            Parsed metadata dictionary
        """
        if not metadata_json:
            return {}

        try:
            return json.loads(metadata_json)
        except json.JSONDecodeError:
            return {}

    def _estimate_token_count(self, content: str) -> int:
        """Estimate token count for content.

        Uses a simple heuristic: ~4 characters per token on average.

        Args:
            content: Text to count tokens for

        Returns:
            Estimated token count
        """
        # Simple estimation: avg 4 chars per token
        return len(content) // 4

    def _calculate_content_hash(self, content: str) -> str:
        """Calculate SHA256 hash of content.

        Args:
            content: Content to hash

        Returns:
            Hexadecimal hash string (64 characters)
        """
        return hashlib.sha256(content.encode("utf-8")).hexdigest()


