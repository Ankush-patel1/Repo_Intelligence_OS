"""Chunk API endpoints.

Provides REST API for chunk operations:
- Create chunks for repository
- List chunks with filtering
- Get specific chunk
- Search chunks
"""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_db
from app.db.models.repository import Repository
from app.db.models.repository_chunk import RepositoryChunk
from app.db.models.repository_file import RepositoryFile
from app.db.models.repository_symbol import RepositorySymbol
from app.services.chunking.class_chunker import ClassChunker
from app.services.chunking.chunk_persister import ChunkPersister
from app.services.chunking.function_chunker import FunctionChunker

router = APIRouter()


# Request/Response models
class ChunkRepositoryRequest:
    """Request body for chunking a repository."""

    include_classes: bool = True
    include_functions: bool = True
    include_methods: bool = True
    force_update: bool = False


class ChunkRepositoryResponse:
    """Response for chunk creation."""

    def __init__(
        self,
        repository_id: UUID,
        total_chunks: int,
        created: int,
        updated: int,
        deleted: int = 0,
        unchanged: int = 0,
    ):
        self.repository_id = str(repository_id)
        self.total_chunks = total_chunks
        self.created = created
        self.updated = updated
        self.deleted = deleted
        self.unchanged = unchanged


class ChunkResponse:
    """Response model for a single chunk."""

    def __init__(self, chunk: RepositoryChunk):
        import json

        self.id = str(chunk.id)
        self.repository_id = str(chunk.repository_id)
        self.repository_file_id = str(chunk.repository_file_id) if chunk.repository_file_id else None
        self.symbol_id = str(chunk.symbol_id) if chunk.symbol_id else None
        self.chunk_type = chunk.chunk_type
        self.chunk_name = chunk.chunk_name
        self.language = chunk.language
        self.content = chunk.content
        self.token_count = chunk.token_count
        self.content_hash = chunk.content_hash
        self.created_at = chunk.created_at.isoformat() if chunk.created_at else None

        # Parse metadata JSON
        if chunk.chunk_metadata:
            try:
                self.metadata = json.loads(chunk.chunk_metadata)
            except json.JSONDecodeError:
                self.metadata = {}
        else:
            self.metadata = {}


class ChunkListResponse:
    """Response model for list of chunks."""

    def __init__(self, chunks: list[RepositoryChunk], total: int):
        self.chunks = [ChunkResponse(chunk).__dict__ for chunk in chunks]
        self.total = total
        self.count = len(chunks)


class ChunkSearchResponse:
    """Response model for chunk search."""

    def __init__(self, chunks: list[RepositoryChunk], query: str):
        self.query = query
        self.results = [ChunkResponse(chunk).__dict__ for chunk in chunks]
        self.count = len(chunks)


@router.post(
    "/repositories/{repository_id}/chunk",
    response_model=None,
    status_code=status.HTTP_200_OK,
)
async def chunk_repository(
    repository_id: UUID,
    include_classes: bool = Query(True, description="Include class chunks"),
    include_functions: bool = Query(True, description="Include function chunks"),
    include_methods: bool = Query(True, description="Include method chunks"),
    force_update: bool = Query(False, description="Force update existing chunks"),
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Create chunks for a repository.

    Generates semantic chunks from repository code using ClassChunker and FunctionChunker.
    Persists chunks to database with deduplication.

    Args:
        repository_id: UUID of the repository to chunk
        include_classes: Whether to create class chunks (default: True)
        include_functions: Whether to create function chunks (default: True)
        include_methods: Whether to create method chunks (default: True)
        force_update: Force update existing chunks even if content unchanged (default: False)
        session: Database session

    Returns:
        Statistics about chunk creation: {
            "repository_id": str,
            "total_chunks": int,
            "created": int,
            "updated": int,
            "deleted": int,
            "unchanged": int
        }

    Raises:
        404: Repository not found
    """
    # Verify repository exists
    stmt = select(Repository).where(Repository.id == repository_id)
    result = await session.execute(stmt)
    repository = result.scalar_one_or_none()

    if not repository:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Repository {repository_id} not found",
        )

    # Generate chunks
    all_chunks = []

    if include_classes:
        class_chunker = ClassChunker(session)
        try:
            class_chunks = await class_chunker.chunk_all_classes(repository_id)
            all_chunks.extend(class_chunks)
        except Exception as e:
            # Log error but continue
            print(f"Error chunking classes: {e}")

    if include_functions or include_methods:
        function_chunker = FunctionChunker(session)
        try:
            function_chunks = await function_chunker.chunk_all_functions(
                repository_id, include_methods=include_methods
            )
            all_chunks.extend(function_chunks)
        except Exception as e:
            # Log error but continue
            print(f"Error chunking functions: {e}")

    # Persist chunks
    persister = ChunkPersister(session)

    if force_update:
        # Use update strategy (create/update/delete)
        stats = await persister.update_repository_chunks(repository_id, all_chunks)
    else:
        # Use simple persist (create/update only)
        stats = await persister.persist_chunks(all_chunks)
        stats["deleted"] = 0  # Add deleted field for consistency

    # Get total count
    stmt = select(RepositoryChunk).where(
        RepositoryChunk.repository_id == repository_id
    )
    result = await session.execute(stmt)
    total_chunks = len(result.scalars().all())

    return {
        "repository_id": str(repository_id),
        "total_chunks": total_chunks,
        "created": stats["created"],
        "updated": stats["updated"],
        "deleted": stats.get("deleted", 0),
        "unchanged": stats.get("unchanged", 0),
    }


@router.get(
    "/repositories/{repository_id}/chunks",
    response_model=None,
    status_code=status.HTTP_200_OK,
)
async def list_repository_chunks(
    repository_id: UUID,
    chunk_type: str | None = Query(None, description="Filter by chunk type"),
    language: str | None = Query(None, description="Filter by language"),
    file_id: UUID | None = Query(None, description="Filter by file ID"),
    symbol_id: UUID | None = Query(None, description="Filter by symbol ID"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum results"),
    offset: int = Query(0, ge=0, description="Results offset"),
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """List chunks for a repository with filtering.

    Args:
        repository_id: UUID of the repository
        chunk_type: Optional filter by chunk type (function, method, class, etc.)
        language: Optional filter by programming language
        file_id: Optional filter by file ID
        symbol_id: Optional filter by symbol ID
        limit: Maximum number of results (1-1000, default: 100)
        offset: Results offset for pagination (default: 0)
        session: Database session

    Returns:
        {
            "chunks": [ChunkResponse, ...],
            "total": int,
            "count": int
        }

    Raises:
        404: Repository not found
    """
    # Verify repository exists
    stmt = select(Repository).where(Repository.id == repository_id)
    result = await session.execute(stmt)
    repository = result.scalar_one_or_none()

    if not repository:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Repository {repository_id} not found",
        )

    # Build query with filters
    stmt = select(RepositoryChunk).where(
        RepositoryChunk.repository_id == repository_id
    )

    if chunk_type:
        stmt = stmt.where(RepositoryChunk.chunk_type == chunk_type)

    if language:
        stmt = stmt.where(RepositoryChunk.language == language)

    if file_id:
        stmt = stmt.where(RepositoryChunk.repository_file_id == file_id)

    if symbol_id:
        stmt = stmt.where(RepositoryChunk.symbol_id == symbol_id)

    # Get total count (before pagination)
    count_stmt = stmt
    count_result = await session.execute(count_stmt)
    total = len(count_result.scalars().all())

    # Apply pagination
    stmt = stmt.limit(limit).offset(offset)

    # Execute query
    result = await session.execute(stmt)
    chunks = result.scalars().all()

    return {
        "chunks": [ChunkResponse(chunk).__dict__ for chunk in chunks],
        "total": total,
        "count": len(chunks),
    }


@router.get(
    "/repositories/{repository_id}/chunks/search",
    response_model=None,
    status_code=status.HTTP_200_OK,
)
async def search_chunks(
    repository_id: UUID,
    q: str = Query(..., min_length=1, description="Search query"),
    chunk_type: str | None = Query(None, description="Filter by chunk type"),
    language: str | None = Query(None, description="Filter by language"),
    limit: int = Query(50, ge=1, le=500, description="Maximum results"),
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Search chunks by content or name.

    Performs case-insensitive search on chunk name and content.

    Args:
        repository_id: UUID of the repository
        q: Search query (required, min length 1)
        chunk_type: Optional filter by chunk type
        language: Optional filter by language
        limit: Maximum number of results (1-500, default: 50)
        session: Database session

    Returns:
        {
            "query": str,
            "results": [ChunkResponse, ...],
            "count": int
        }

    Raises:
        404: Repository not found
    """
    # Verify repository exists
    stmt = select(Repository).where(Repository.id == repository_id)
    result = await session.execute(stmt)
    repository = result.scalar_one_or_none()

    if not repository:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Repository {repository_id} not found",
        )

    # Build search query
    stmt = select(RepositoryChunk).where(
        RepositoryChunk.repository_id == repository_id
    )

    # Search in chunk_name and content (case-insensitive)
    search_term = f"%{q}%"
    stmt = stmt.where(
        (RepositoryChunk.chunk_name.ilike(search_term))
        | (RepositoryChunk.content.ilike(search_term))
    )

    # Apply filters
    if chunk_type:
        stmt = stmt.where(RepositoryChunk.chunk_type == chunk_type)

    if language:
        stmt = stmt.where(RepositoryChunk.language == language)

    # Apply limit
    stmt = stmt.limit(limit)

    # Execute query
    result = await session.execute(stmt)
    chunks = result.scalars().all()

    return {
        "query": q,
        "results": [ChunkResponse(chunk).__dict__ for chunk in chunks],
        "count": len(chunks),
    }


@router.get(
    "/repositories/{repository_id}/chunks/statistics",
    response_model=None,
    status_code=status.HTTP_200_OK,
)
async def get_chunk_statistics(
    repository_id: UUID,
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Get statistics about chunks for a repository.

    Args:
        repository_id: UUID of the repository
        session: Database session

    Returns:
        Statistics dictionary with counts and metrics

    Raises:
        404: Repository not found
    """
    # Verify repository exists
    stmt = select(Repository).where(Repository.id == repository_id)
    result = await session.execute(stmt)
    repository = result.scalar_one_or_none()

    if not repository:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Repository {repository_id} not found",
        )

    # Get statistics using persister
    persister = ChunkPersister(session)
    stats = await persister.get_chunk_statistics(repository_id)

    return stats


@router.get(
    "/repositories/{repository_id}/chunks/{chunk_id}",
    response_model=None,
    status_code=status.HTTP_200_OK,
)
async def get_chunk(
    repository_id: UUID,
    chunk_id: UUID,
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Get a specific chunk by ID.

    Args:
        repository_id: UUID of the repository
        chunk_id: UUID of the chunk
        session: Database session

    Returns:
        ChunkResponse with full chunk details

    Raises:
        404: Repository or chunk not found
    """
    # Verify repository exists
    stmt = select(Repository).where(Repository.id == repository_id)
    result = await session.execute(stmt)
    repository = result.scalar_one_or_none()

    if not repository:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Repository {repository_id} not found",
        )

    # Get chunk
    stmt = (
        select(RepositoryChunk)
        .where(RepositoryChunk.id == chunk_id)
        .where(RepositoryChunk.repository_id == repository_id)
    )

    result = await session.execute(stmt)
    chunk = result.scalar_one_or_none()

    if not chunk:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Chunk {chunk_id} not found in repository {repository_id}",
        )

    return ChunkResponse(chunk).__dict__


