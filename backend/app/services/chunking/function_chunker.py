"""Function-based semantic chunking implementation.

Creates semantic chunks from function symbols, including:
- Function definition and body
- Import statements
- Called functions
- Parent class (for methods)
- Referenced symbols
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


class FunctionChunker:
    """Creates semantic chunks from function symbols.

    Processes function and method symbols and generates comprehensive chunks containing:
    - The function definition and body
    - Import statements needed by the function
    - Functions called by this function
    - Parent class (for methods)
    - Referenced symbols
    - Graph node and edge information
    """

    def __init__(self, session: AsyncSession):
        """Initialize function chunker.

        Args:
            session: Database session for querying models
        """
        self.session = session

    async def chunk_function(
        self,
        function_symbol_id: UUID,
    ) -> ChunkResult:
        """Create a semantic chunk from a function symbol.

        Args:
            function_symbol_id: UUID of the function symbol to chunk

        Returns:
            ChunkResult containing the complete function chunk

        Raises:
            ValueError: If symbol not found or not a function/method
        """
        # Fetch the function symbol with relationships
        function_symbol = await self._fetch_function_symbol(function_symbol_id)

        if not function_symbol:
            raise ValueError(f"Function symbol {function_symbol_id} not found")

        if function_symbol.symbol_type not in ("function", "method"):
            raise ValueError(
                f"Symbol {function_symbol_id} is not a function/method (type: {function_symbol.symbol_type})"
            )

        # Fetch related data
        file = function_symbol.repository_file
        file_content = await self._read_file_content(file.absolute_path)
        graph_node = await self._fetch_graph_node(function_symbol_id)
        imports = await self._extract_imports(file.id)
        relationships = await self._fetch_relationships(graph_node.id) if graph_node else []
        parent_class = function_symbol.parent if function_symbol.parent else None

        # Extract function content
        content = self._extract_function_content(file_content, function_symbol)

        # Build context
        context = await self._build_function_context(
            imports, function_symbol, parent_class, relationships
        )

        # Build metadata
        metadata = await self._build_function_metadata(
            function_symbol, parent_class, graph_node, relationships
        )

        # Calculate metrics
        token_count = self._estimate_token_count(content)
        content_hash = self._calculate_content_hash(content)

        # Determine chunk type (method vs function)
        chunk_type = "method" if function_symbol.symbol_type == "method" else "function"

        # Create chunk result
        chunk = ChunkResult(
            repository_id=file.repository_id,
            repository_file_id=file.id,
            symbol_id=function_symbol.id,
            chunk_type=chunk_type,
            chunk_name=function_symbol.symbol_name,
            language=function_symbol.language,
            content=content,
            token_count=token_count,
            content_hash=content_hash,
            metadata=metadata,
            context=context,
        )

        return chunk

    async def chunk_all_functions(
        self,
        repository_id: UUID,
        include_methods: bool = True,
    ) -> list[ChunkResult]:
        """Create chunks for all functions in a repository.

        Args:
            repository_id: UUID of the repository
            include_methods: Whether to include methods (default: True)

        Returns:
            List of ChunkResult objects for all functions
        """
        # Determine symbol types to fetch
        symbol_types = ["function"]
        if include_methods:
            symbol_types.append("method")

        # Fetch all function/method symbols in repository
        stmt = (
            select(RepositorySymbol)
            .join(RepositoryFile)
            .where(RepositoryFile.repository_id == repository_id)
            .where(RepositorySymbol.symbol_type.in_(symbol_types))
            .options(selectinload(RepositorySymbol.repository_file))
            .options(selectinload(RepositorySymbol.parent))
        )

        result = await self.session.execute(stmt)
        function_symbols = result.scalars().all()

        # Chunk each function
        chunks = []
        for function_symbol in function_symbols:
            try:
                chunk = await self.chunk_function(function_symbol.id)
                chunks.append(chunk)
            except Exception as e:
                # Log error but continue processing other functions
                print(f"Error chunking function {function_symbol.symbol_name}: {e}")
                continue

        return chunks

    async def chunk_file_functions(
        self,
        file_id: UUID,
        include_methods: bool = True,
    ) -> list[ChunkResult]:
        """Create chunks for all functions in a specific file.

        Args:
            file_id: UUID of the file
            include_methods: Whether to include methods (default: True)

        Returns:
            List of ChunkResult objects for functions in the file
        """
        # Determine symbol types to fetch
        symbol_types = ["function"]
        if include_methods:
            symbol_types.append("method")

        # Fetch all function/method symbols in file
        stmt = (
            select(RepositorySymbol)
            .where(RepositorySymbol.repository_file_id == file_id)
            .where(RepositorySymbol.symbol_type.in_(symbol_types))
            .options(selectinload(RepositorySymbol.repository_file))
            .options(selectinload(RepositorySymbol.parent))
            .order_by(RepositorySymbol.start_line)
        )

        result = await self.session.execute(stmt)
        function_symbols = result.scalars().all()

        # Chunk each function
        chunks = []
        for function_symbol in function_symbols:
            try:
                chunk = await self.chunk_function(function_symbol.id)
                chunks.append(chunk)
            except Exception as e:
                # Log error but continue processing other functions
                print(f"Error chunking function {function_symbol.symbol_name}: {e}")
                continue

        return chunks

    async def _fetch_function_symbol(
        self, function_symbol_id: UUID
    ) -> RepositorySymbol | None:
        """Fetch function symbol with relationships.

        Args:
            function_symbol_id: UUID of the function symbol

        Returns:
            RepositorySymbol or None if not found
        """
        stmt = (
            select(RepositorySymbol)
            .where(RepositorySymbol.id == function_symbol_id)
            .options(
                selectinload(RepositorySymbol.repository_file),
                selectinload(RepositorySymbol.parent),
            )
        )

        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

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

    def _extract_function_content(
        self,
        file_content: str,
        function_symbol: RepositorySymbol,
    ) -> str:
        """Extract function content.

        Args:
            file_content: Complete file content
            function_symbol: The function symbol

        Returns:
            Extracted function content
        """
        lines = file_content.splitlines()

        # Validate line numbers
        if function_symbol.start_line < 1 or function_symbol.end_line > len(lines):
            raise ValueError(
                f"Invalid line range: {function_symbol.start_line}-{function_symbol.end_line} "
                f"(file has {len(lines)} lines)"
            )

        # Extract lines (convert from 1-indexed to 0-indexed)
        start_idx = function_symbol.start_line - 1
        end_idx = function_symbol.end_line  # end_line is inclusive, so no -1 needed

        function_lines = lines[start_idx:end_idx]
        return "\n".join(function_lines)

    async def _build_function_context(
        self,
        imports: list[str],
        function_symbol: RepositorySymbol,
        parent_class: RepositorySymbol | None,
        relationships: list[tuple[RepositoryEdge, RepositoryNode]],
    ) -> ChunkContext:
        """Build context for a function chunk.

        Args:
            imports: List of import statements
            function_symbol: The function symbol
            parent_class: Parent class symbol (if method)
            relationships: List of (edge, target_node) tuples

        Returns:
            ChunkContext object
        """
        # Parse function metadata
        function_metadata = self._parse_metadata(function_symbol.symbol_metadata)

        # Extract docstring from metadata
        docstring = function_metadata.get("docstring")

        # Extract decorators from metadata
        decorators = function_metadata.get("decorators", [])

        # Get parent class definition if exists
        parent_definition = None
        if parent_class:
            parent_definition = parent_class.signature or f"class {parent_class.symbol_name}:"

        # Extract dependencies from relationships
        dependencies = []
        related_chunks = []
        
        for edge, target_node in relationships:
            if edge.relationship_type in ("CALLS", "REFERENCES", "IMPORTS"):
                if target_node.symbol_id:
                    dependencies.append(target_node.symbol_id)
            
            # Related chunks could be other functions in same class/module
            if edge.relationship_type in ("CALLS",):
                if target_node.symbol_id:
                    related_chunks.append(target_node.symbol_id)

        return ChunkContext(
            imports=imports,
            parent_definition=parent_definition,
            dependencies=dependencies,
            related_chunks=related_chunks,
            docstring=docstring,
            decorators=decorators,
        )

    async def _build_function_metadata(
        self,
        function_symbol: RepositorySymbol,
        parent_class: RepositorySymbol | None,
        graph_node: RepositoryNode | None,
        relationships: list[tuple[RepositoryEdge, RepositoryNode]],
    ) -> ChunkMetadata:
        """Build metadata for a function chunk.

        Args:
            function_symbol: The function symbol
            parent_class: Parent class symbol (if method)
            graph_node: The graph node for this function
            relationships: List of (edge, target_node) tuples

        Returns:
            ChunkMetadata object
        """
        # Parse function metadata
        function_metadata = self._parse_metadata(function_symbol.symbol_metadata)

        # Extract parameters and return type
        parameters = function_metadata.get("parameters", [])
        return_type = function_metadata.get("return_type")

        # Extract called functions and references
        calls = []
        called_by = []

        for edge, target_node in relationships:
            if edge.relationship_type == "CALLS":
                if target_node.symbol_id:
                    calls.append(target_node.symbol_id)
            elif edge.relationship_type == "REFERENCES":
                if target_node.symbol_id:
                    calls.append(target_node.symbol_id)

        # Note: called_by would require fetching incoming edges
        # which we're not doing for performance reasons

        # Extract access modifier and flags
        access_modifier = function_metadata.get("access_modifier")
        is_static = function_metadata.get("is_static", False)
        is_async = function_metadata.get("is_async", False)

        # Complexity score if available
        complexity_score = function_metadata.get("complexity_score")

        return ChunkMetadata(
            symbol_type=function_symbol.symbol_type,
            signature=function_symbol.signature,
            parameters=parameters,
            return_type=return_type,
            start_line=function_symbol.start_line,
            end_line=function_symbol.end_line,
            start_column=function_symbol.start_column,
            end_column=function_symbol.end_column,
            parent_symbol_id=function_symbol.parent_symbol,
            node_id=graph_node.id if graph_node else None,
            calls=calls,
            called_by=called_by,
            access_modifier=access_modifier,
            is_static=is_static,
            is_async=is_async,
            complexity_score=complexity_score,
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


