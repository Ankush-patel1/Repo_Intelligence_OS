"""Node extraction service.

Converts existing database models (Repository, RepositoryFile, RepositorySymbol)
into RepositoryNode objects for the knowledge graph.

No edge creation, no persistence - only node object generation.
"""

import json
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.repository import Repository
from app.db.models.repository_file import RepositoryFile
from app.db.models.repository_node import RepositoryNode
from app.db.models.repository_symbol import RepositorySymbol


class NodeExtractor:
    """Extracts graph nodes from existing database models.

    Converts Repository, RepositoryFile, and RepositorySymbol records
    into RepositoryNode objects suitable for graph operations.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the node extractor.

        Args:
            session: Database session for queries
        """
        self.session = session

    async def extract_repository_nodes(
        self, repository_id: UUID
    ) -> list[RepositoryNode]:
        """Extract all graph nodes for a repository.

        Converts:
        - Repository → repository node
        - RepositoryFiles → file nodes
        - RepositorySymbols → symbol nodes

        Args:
            repository_id: UUID of the repository

        Returns:
            List of RepositoryNode objects (not persisted)
        """
        nodes: list[RepositoryNode] = []

        # Extract repository node
        repo_node = await self.extract_repository_node(repository_id)
        if repo_node:
            nodes.append(repo_node)

        # Extract file nodes
        file_nodes = await self.extract_file_nodes(repository_id)
        nodes.extend(file_nodes)

        # Extract symbol nodes
        symbol_nodes = await self.extract_symbol_nodes(repository_id)
        nodes.extend(symbol_nodes)

        return nodes

    async def extract_repository_node(self, repository_id: UUID) -> RepositoryNode | None:
        """Extract repository node.

        Args:
            repository_id: UUID of the repository

        Returns:
            RepositoryNode for the repository, or None if not found
        """
        # Query repository
        result = await self.session.execute(
            select(Repository).where(Repository.id == repository_id)
        )
        repository = result.scalar_one_or_none()

        if not repository:
            return None

        # Build metadata
        metadata = {
            "full_name": repository.full_name,
            "owner": repository.owner,
            "name": repository.name,
            "branch": repository.branch,
            "default_branch": repository.default_branch,
            "private": repository.private,
            "clone_path": repository.clone_path,
        }

        # Create node
        return RepositoryNode(
            repository_id=repository.id,
            repository_file_id=None,
            symbol_id=None,
            node_type="repository",
            display_name=repository.full_name,
            language=None,
            node_metadata=json.dumps(metadata),
        )

    async def extract_file_nodes(self, repository_id: UUID) -> list[RepositoryNode]:
        """Extract file nodes for a repository.

        Args:
            repository_id: UUID of the repository

        Returns:
            List of RepositoryNode objects for files
        """
        # Query all files for repository
        result = await self.session.execute(
            select(RepositoryFile)
            .where(RepositoryFile.repository_id == repository_id)
            .order_by(RepositoryFile.relative_path)
        )
        files = result.scalars().all()

        nodes: list[RepositoryNode] = []

        for file in files:
            # Build metadata
            metadata = {
                "relative_path": file.relative_path,
                "absolute_path": file.absolute_path,
                "file_name": file.file_name,
                "extension": file.extension,
                "size_bytes": file.size_bytes,
                "line_count": file.line_count,
                "sha256_hash": file.sha256_hash,
                "is_binary": file.is_binary,
            }

            # Create node
            node = RepositoryNode(
                repository_id=repository_id,
                repository_file_id=file.id,
                symbol_id=None,
                node_type="file",
                display_name=file.relative_path,
                language=file.language,
                node_metadata=json.dumps(metadata),
            )

            nodes.append(node)

        return nodes

    async def extract_symbol_nodes(self, repository_id: UUID) -> list[RepositoryNode]:
        """Extract symbol nodes for a repository.

        Args:
            repository_id: UUID of the repository

        Returns:
            List of RepositoryNode objects for symbols
        """
        # Query all symbols for repository (via files)
        result = await self.session.execute(
            select(RepositorySymbol)
            .join(RepositoryFile, RepositorySymbol.repository_file_id == RepositoryFile.id)
            .where(RepositoryFile.repository_id == repository_id)
            .order_by(RepositoryFile.relative_path, RepositorySymbol.start_line)
        )
        symbols = result.scalars().all()

        nodes: list[RepositoryNode] = []

        for symbol in symbols:
            # Build metadata
            metadata = {
                "symbol_type": symbol.symbol_type,
                "signature": symbol.signature,
                "start_line": symbol.start_line,
                "end_line": symbol.end_line,
                "start_column": symbol.start_column,
                "end_column": symbol.end_column,
                "parent_symbol_id": str(symbol.parent_symbol) if symbol.parent_symbol else None,
            }

            # Include original symbol metadata if present
            if symbol.symbol_metadata:
                try:
                    original_metadata = json.loads(symbol.symbol_metadata)
                    metadata["original_metadata"] = original_metadata
                except (json.JSONDecodeError, TypeError):
                    metadata["original_metadata_raw"] = symbol.symbol_metadata

            # Create node
            node = RepositoryNode(
                repository_id=repository_id,
                repository_file_id=symbol.repository_file_id,
                symbol_id=symbol.id,
                node_type="symbol",
                display_name=symbol.symbol_name,
                language=symbol.language,
                node_metadata=json.dumps(metadata),
            )

            nodes.append(node)

        return nodes

    async def extract_file_node(self, file_id: UUID) -> RepositoryNode | None:
        """Extract single file node.

        Args:
            file_id: UUID of the file

        Returns:
            RepositoryNode for the file, or None if not found
        """
        # Query file
        result = await self.session.execute(
            select(RepositoryFile).where(RepositoryFile.id == file_id)
        )
        file = result.scalar_one_or_none()

        if not file:
            return None

        # Build metadata
        metadata = {
            "relative_path": file.relative_path,
            "absolute_path": file.absolute_path,
            "file_name": file.file_name,
            "extension": file.extension,
            "size_bytes": file.size_bytes,
            "line_count": file.line_count,
            "sha256_hash": file.sha256_hash,
            "is_binary": file.is_binary,
        }

        # Create node
        return RepositoryNode(
            repository_id=file.repository_id,
            repository_file_id=file.id,
            symbol_id=None,
            node_type="file",
            display_name=file.relative_path,
            language=file.language,
            node_metadata=json.dumps(metadata),
        )

    async def extract_symbol_node(self, symbol_id: UUID) -> RepositoryNode | None:
        """Extract single symbol node.

        Args:
            symbol_id: UUID of the symbol

        Returns:
            RepositoryNode for the symbol, or None if not found
        """
        # Query symbol with file for repository_id
        result = await self.session.execute(
            select(RepositorySymbol)
            .join(RepositoryFile, RepositorySymbol.repository_file_id == RepositoryFile.id)
            .where(RepositorySymbol.id == symbol_id)
        )
        symbol = result.scalar_one_or_none()

        if not symbol:
            return None

        # Build metadata
        metadata = {
            "symbol_type": symbol.symbol_type,
            "signature": symbol.signature,
            "start_line": symbol.start_line,
            "end_line": symbol.end_line,
            "start_column": symbol.start_column,
            "end_column": symbol.end_column,
            "parent_symbol_id": str(symbol.parent_symbol) if symbol.parent_symbol else None,
        }

        # Include original symbol metadata if present
        if symbol.symbol_metadata:
            try:
                original_metadata = json.loads(symbol.symbol_metadata)
                metadata["original_metadata"] = original_metadata
            except (json.JSONDecodeError, TypeError):
                metadata["original_metadata_raw"] = symbol.symbol_metadata

        # Get repository_id from file relationship
        repository_id = symbol.repository_file.repository_id

        # Create node
        return RepositoryNode(
            repository_id=repository_id,
            repository_file_id=symbol.repository_file_id,
            symbol_id=symbol.id,
            node_type="symbol",
            display_name=symbol.symbol_name,
            language=symbol.language,
            node_metadata=json.dumps(metadata),
        )

    async def extract_nodes_by_type(
        self, repository_id: UUID, node_type: str
    ) -> list[RepositoryNode]:
        """Extract nodes of a specific type.

        Args:
            repository_id: UUID of the repository
            node_type: Type of nodes to extract ("repository", "file", "symbol")

        Returns:
            List of RepositoryNode objects

        Raises:
            ValueError: If node_type is invalid
        """
        if node_type == "repository":
            repo_node = await self.extract_repository_node(repository_id)
            return [repo_node] if repo_node else []
        elif node_type == "file":
            return await self.extract_file_nodes(repository_id)
        elif node_type == "symbol":
            return await self.extract_symbol_nodes(repository_id)
        else:
            raise ValueError(
                f"Invalid node_type '{node_type}'. Must be 'repository', 'file', or 'symbol'"
            )

    async def get_node_statistics(self, repository_id: UUID) -> dict[str, Any]:
        """Get statistics about extractable nodes.

        Args:
            repository_id: UUID of the repository

        Returns:
            Dictionary with node counts by type
        """
        # Count files
        file_result = await self.session.execute(
            select(RepositoryFile).where(RepositoryFile.repository_id == repository_id)
        )
        file_count = len(list(file_result.scalars().all()))

        # Count symbols
        symbol_result = await self.session.execute(
            select(RepositorySymbol)
            .join(RepositoryFile, RepositorySymbol.repository_file_id == RepositoryFile.id)
            .where(RepositoryFile.repository_id == repository_id)
        )
        symbol_count = len(list(symbol_result.scalars().all()))

        # Count by language
        file_lang_result = await self.session.execute(
            select(RepositoryFile).where(RepositoryFile.repository_id == repository_id)
        )
        files = list(file_lang_result.scalars().all())
        files_by_language: dict[str, int] = {}
        for file in files:
            lang = file.language
            files_by_language[lang] = files_by_language.get(lang, 0) + 1

        symbol_lang_result = await self.session.execute(
            select(RepositorySymbol)
            .join(RepositoryFile, RepositorySymbol.repository_file_id == RepositoryFile.id)
            .where(RepositoryFile.repository_id == repository_id)
        )
        symbols = list(symbol_lang_result.scalars().all())
        symbols_by_language: dict[str, int] = {}
        symbols_by_type: dict[str, int] = {}
        for symbol in symbols:
            lang = symbol.language
            sym_type = symbol.symbol_type
            symbols_by_language[lang] = symbols_by_language.get(lang, 0) + 1
            symbols_by_type[sym_type] = symbols_by_type.get(sym_type, 0) + 1

        return {
            "repository_nodes": 1,
            "file_nodes": file_count,
            "symbol_nodes": symbol_count,
            "total_nodes": 1 + file_count + symbol_count,
            "files_by_language": files_by_language,
            "symbols_by_language": symbols_by_language,
            "symbols_by_type": symbols_by_type,
        }
