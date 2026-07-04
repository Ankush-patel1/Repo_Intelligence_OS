"""Chunk persistence service.

Handles saving chunks to database with deduplication and update logic.
"""

import json
from typing import Any
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.repository_chunk import RepositoryChunk
from app.schemas.chunk import ChunkResult


class ChunkPersister:
    """Persists chunks to database with deduplication and update support.

    Features:
    - Deduplication by content hash
    - Update existing chunks when content changes
    - Batch operations for performance
    - Cleanup of orphaned chunks
    """

    def __init__(self, session: AsyncSession):
        """Initialize chunk persister.

        Args:
            session: Database session
        """
        self.session = session

    async def persist_chunk(
        self, chunk: ChunkResult, force_update: bool = False
    ) -> tuple[RepositoryChunk, bool]:
        """Persist a single chunk to database.

        Args:
            chunk: ChunkResult to persist
            force_update: If True, always update existing chunks even if hash matches

        Returns:
            Tuple of (RepositoryChunk, is_new) where is_new indicates if chunk was created
        """
        # Check if chunk already exists (by repository, file, and symbol)
        existing_chunk = await self._find_existing_chunk(
            chunk.repository_id,
            chunk.repository_file_id,
            chunk.symbol_id,
            chunk.content_hash,
        )

        if existing_chunk:
            # Check if content changed (by comparing hashes)
            content_changed = existing_chunk.content_hash != chunk.content_hash
            
            if content_changed or force_update:
                # Update existing chunk
                updated_chunk = await self._update_chunk(existing_chunk, chunk)
                return updated_chunk, False
            else:
                # Content unchanged, no update needed
                return existing_chunk, False
        else:
            # Create new chunk
            new_chunk = await self._create_chunk(chunk)
            return new_chunk, True

    async def persist_chunks(
        self, chunks: list[ChunkResult], force_update: bool = False
    ) -> dict[str, int]:
        """Persist multiple chunks to database.

        Args:
            chunks: List of ChunkResult objects to persist
            force_update: If True, always update existing chunks

        Returns:
            Dictionary with statistics: {"created": int, "updated": int, "unchanged": int}
        """
        stats = {"created": 0, "updated": 0, "unchanged": 0}

        for chunk in chunks:
            _, is_new = await self.persist_chunk(chunk, force_update)
            if is_new:
                stats["created"] += 1
            else:
                stats["updated"] += 1

        await self.session.commit()
        return stats

    async def delete_repository_chunks(self, repository_id: UUID) -> int:
        """Delete all chunks for a repository.

        Args:
            repository_id: UUID of the repository

        Returns:
            Number of chunks deleted
        """
        stmt = delete(RepositoryChunk).where(
            RepositoryChunk.repository_id == repository_id
        )

        result = await self.session.execute(stmt)
        await self.session.commit()

        return result.rowcount

    async def delete_file_chunks(self, file_id: UUID) -> int:
        """Delete all chunks for a file.

        Args:
            file_id: UUID of the file

        Returns:
            Number of chunks deleted
        """
        stmt = delete(RepositoryChunk).where(
            RepositoryChunk.repository_file_id == file_id
        )

        result = await self.session.execute(stmt)
        await self.session.commit()

        return result.rowcount

    async def delete_symbol_chunks(self, symbol_id: UUID) -> int:
        """Delete all chunks for a symbol.

        Args:
            symbol_id: UUID of the symbol

        Returns:
            Number of chunks deleted
        """
        stmt = delete(RepositoryChunk).where(RepositoryChunk.symbol_id == symbol_id)

        result = await self.session.execute(stmt)
        await self.session.commit()

        return result.rowcount

    async def update_repository_chunks(
        self,
        repository_id: UUID,
        new_chunks: list[ChunkResult],
    ) -> dict[str, int]:
        """Update chunks for a repository after re-analysis.

        Strategy:
        1. Get all existing chunk hashes for repository
        2. Compare with new chunks
        3. Delete chunks no longer present
        4. Update changed chunks
        5. Create new chunks

        Args:
            repository_id: UUID of the repository
            new_chunks: List of new ChunkResult objects from re-analysis

        Returns:
            Dictionary with statistics: {
                "created": int,
                "updated": int,
                "deleted": int,
                "unchanged": int
            }
        """
        # Get existing chunks for repository
        existing_chunks = await self._get_existing_chunks(repository_id)

        # Build maps for comparison
        existing_map = {
            (chunk.repository_file_id, chunk.symbol_id, chunk.chunk_type): chunk
            for chunk in existing_chunks
        }

        new_map = {
            (chunk.repository_file_id, chunk.symbol_id, chunk.chunk_type): chunk
            for chunk in new_chunks
        }

        stats = {"created": 0, "updated": 0, "deleted": 0, "unchanged": 0}

        # Process new chunks
        for key, new_chunk in new_map.items():
            if key in existing_map:
                existing_chunk = existing_map[key]

                # Check if content changed (by hash)
                if existing_chunk.content_hash != new_chunk.content_hash:
                    # Content changed, update
                    await self._update_chunk(existing_chunk, new_chunk)
                    stats["updated"] += 1
                else:
                    # Content unchanged
                    stats["unchanged"] += 1
            else:
                # New chunk, create
                await self._create_chunk(new_chunk)
                stats["created"] += 1

        # Delete chunks no longer present
        for key, existing_chunk in existing_map.items():
            if key not in new_map:
                await self.session.delete(existing_chunk)
                stats["deleted"] += 1

        await self.session.commit()
        return stats

    async def get_chunk_statistics(self, repository_id: UUID) -> dict[str, Any]:
        """Get statistics about chunks for a repository.

        Args:
            repository_id: UUID of the repository

        Returns:
            Dictionary with statistics
        """
        stmt = select(RepositoryChunk).where(
            RepositoryChunk.repository_id == repository_id
        )

        result = await self.session.execute(stmt)
        chunks = result.scalars().all()

        if not chunks:
            return {
                "total_chunks": 0,
                "by_type": {},
                "by_language": {},
                "total_tokens": 0,
                "avg_tokens": 0,
                "min_tokens": 0,
                "max_tokens": 0,
            }

        # Calculate statistics
        by_type = {}
        by_language = {}
        token_counts = []

        for chunk in chunks:
            # Count by type
            by_type[chunk.chunk_type] = by_type.get(chunk.chunk_type, 0) + 1

            # Count by language
            by_language[chunk.language] = by_language.get(chunk.language, 0) + 1

            # Collect token counts
            token_counts.append(chunk.token_count)

        return {
            "total_chunks": len(chunks),
            "by_type": by_type,
            "by_language": by_language,
            "total_tokens": sum(token_counts),
            "avg_tokens": sum(token_counts) // len(token_counts),
            "min_tokens": min(token_counts),
            "max_tokens": max(token_counts),
        }

    async def _find_existing_chunk(
        self,
        repository_id: UUID,
        file_id: UUID | None,
        symbol_id: UUID | None,
        content_hash: str,
    ) -> RepositoryChunk | None:
        """Find existing chunk by identifiers.

        First looks for chunk with same repository, file, and symbol (regardless of hash).
        If found and hash differs, it can be updated.
        If found and hash matches, no update needed.
        If not found, new chunk will be created.

        Args:
            repository_id: Repository UUID
            file_id: File UUID
            symbol_id: Symbol UUID
            content_hash: Content hash (not used in query, just for reference)

        Returns:
            Existing RepositoryChunk or None
        """
        stmt = (
            select(RepositoryChunk)
            .where(RepositoryChunk.repository_id == repository_id)
            .where(RepositoryChunk.repository_file_id == file_id)
            .where(RepositoryChunk.symbol_id == symbol_id)
        )

        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def _get_existing_chunks(
        self, repository_id: UUID
    ) -> list[RepositoryChunk]:
        """Get all existing chunks for a repository.

        Args:
            repository_id: UUID of the repository

        Returns:
            List of RepositoryChunk objects
        """
        stmt = select(RepositoryChunk).where(
            RepositoryChunk.repository_id == repository_id
        )

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def _create_chunk(self, chunk: ChunkResult) -> RepositoryChunk:
        """Create new chunk in database.

        Args:
            chunk: ChunkResult to create

        Returns:
            Created RepositoryChunk
        """
        # Serialize metadata and context to JSON
        metadata_json = self._serialize_metadata(chunk)

        db_chunk = RepositoryChunk(
            repository_id=chunk.repository_id,
            repository_file_id=chunk.repository_file_id,
            symbol_id=chunk.symbol_id,
            chunk_type=chunk.chunk_type,
            chunk_name=chunk.chunk_name,
            language=chunk.language,
            content=chunk.content,
            chunk_metadata=metadata_json,
            token_count=chunk.token_count,
            content_hash=chunk.content_hash,
        )

        self.session.add(db_chunk)
        await self.session.flush()  # Get ID without committing

        return db_chunk

    async def _update_chunk(
        self, existing: RepositoryChunk, new_chunk: ChunkResult
    ) -> RepositoryChunk:
        """Update existing chunk with new content.

        Args:
            existing: Existing RepositoryChunk
            new_chunk: New ChunkResult with updated content

        Returns:
            Updated RepositoryChunk
        """
        # Update fields
        existing.content = new_chunk.content
        existing.chunk_metadata = self._serialize_metadata(new_chunk)
        existing.token_count = new_chunk.token_count
        existing.content_hash = new_chunk.content_hash

        await self.session.flush()

        return existing

    def _serialize_metadata(self, chunk: ChunkResult) -> str:
        """Serialize chunk metadata and context to JSON.

        Args:
            chunk: ChunkResult with metadata and context

        Returns:
            JSON string
        """
        # Combine metadata and context into single JSON object
        combined = {
            "metadata": {
                "symbol_type": chunk.metadata.symbol_type,
                "signature": chunk.metadata.signature,
                "parameters": chunk.metadata.parameters,
                "return_type": chunk.metadata.return_type,
                "start_line": chunk.metadata.start_line,
                "end_line": chunk.metadata.end_line,
                "start_column": chunk.metadata.start_column,
                "end_column": chunk.metadata.end_column,
                "parent_symbol_id": str(chunk.metadata.parent_symbol_id)
                if chunk.metadata.parent_symbol_id
                else None,
                "node_id": str(chunk.metadata.node_id)
                if chunk.metadata.node_id
                else None,
                "calls": [str(uid) for uid in chunk.metadata.calls],
                "called_by": [str(uid) for uid in chunk.metadata.called_by],
                "inherits_from": chunk.metadata.inherits_from,
                "implements": chunk.metadata.implements,
                "method_count": chunk.metadata.method_count,
                "is_abstract": chunk.metadata.is_abstract,
                "access_modifier": chunk.metadata.access_modifier,
                "is_static": chunk.metadata.is_static,
                "is_async": chunk.metadata.is_async,
                "complexity_score": chunk.metadata.complexity_score,
                "has_examples": chunk.metadata.has_examples,
                "tags": chunk.metadata.tags,
                "custom": chunk.metadata.custom,
            },
            "context": {
                "imports": chunk.context.imports if chunk.context else [],
                "parent_definition": chunk.context.parent_definition
                if chunk.context
                else None,
                "dependencies": [str(uid) for uid in chunk.context.dependencies]
                if chunk.context
                else [],
                "related_chunks": [str(uid) for uid in chunk.context.related_chunks]
                if chunk.context
                else [],
                "docstring": chunk.context.docstring if chunk.context else None,
                "decorators": chunk.context.decorators if chunk.context else [],
                "context_before": chunk.context.context_before
                if chunk.context
                else None,
                "context_after": chunk.context.context_after if chunk.context else None,
            },
        }

        return json.dumps(combined)


