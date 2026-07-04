"""Test script for chunk persistence.

Demonstrates the ChunkPersister functionality with deduplication and updates.
"""

import asyncio
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.db.models.repository import Repository
from app.db.models.repository_chunk import RepositoryChunk
from app.db.models.repository_file import RepositoryFile
from app.db.models.repository_symbol import RepositorySymbol
from app.schemas.chunk import ChunkContext, ChunkMetadata, ChunkResult
from app.services.chunking.chunk_persister import ChunkPersister


# In-memory SQLite for testing
DATABASE_URL = "sqlite+aiosqlite:///:memory:"


async def setup_test_database():
    """Create test database and tables."""
    engine = create_async_engine(DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    return engine, async_session


async def create_test_data(session: AsyncSession):
    """Create test data."""
    # Create repository
    repo = Repository(
        id=uuid4(),
        owner="test",
        name="test-persistence",
        full_name="test/test-persistence",
        branch="main",
        clone_path="/tmp/test",
        default_branch="main",
        private=False,
    )
    session.add(repo)

    # Create file
    file = RepositoryFile(
        id=uuid4(),
        repository_id=repo.id,
        relative_path="test.py",
        absolute_path="/tmp/test/test.py",
        file_name="test.py",
        extension=".py",
        language="python",
        size_bytes=1000,
        line_count=50,
        sha256_hash="abc123",
        last_modified=datetime.now(),
        is_binary=False,
    )
    session.add(file)

    # Create symbol
    symbol = RepositorySymbol(
        id=uuid4(),
        repository_file_id=file.id,
        symbol_name="test_function",
        symbol_type="function",
        start_line=10,
        end_line=20,
        language="python",
        signature="def test_function():",
    )
    session.add(symbol)

    await session.commit()

    return {"repository": repo, "file": file, "symbol": symbol}


def create_chunk_result(
    repository_id, file_id, symbol_id, content="test content", chunk_name="test_func"
) -> ChunkResult:
    """Create a test ChunkResult."""
    import hashlib

    content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()

    return ChunkResult(
        repository_id=repository_id,
        repository_file_id=file_id,
        symbol_id=symbol_id,
        chunk_type="function",
        chunk_name=chunk_name,
        language="python",
        content=content,
        token_count=len(content) // 4,
        content_hash=content_hash,
        metadata=ChunkMetadata(
            symbol_type="function",
            signature="def test_function():",
            parameters=["param1"],
            return_type="str",
            start_line=10,
            end_line=20,
        ),
        context=ChunkContext(
            imports=["import os", "import sys"],
            dependencies=[],
            related_chunks=[],
        ),
    )


async def test_chunk_persistence():
    """Test chunk persistence functionality."""
    print("=" * 70)
    print("CHUNK PERSISTENCE TEST")
    print("=" * 70)

    # Setup database
    engine, async_session_factory = await setup_test_database()

    async with async_session_factory() as session:
        # Create test data
        print("\n📦 Creating test data...")
        test_data = await create_test_data(session)
        print("✅ Test data created")

        # Initialize persister
        persister = ChunkPersister(session)

        # Test 1: Create new chunk
        print("\n" + "=" * 70)
        print("TEST 1: Create New Chunk")
        print("=" * 70)

        chunk1 = create_chunk_result(
            test_data["repository"].id,
            test_data["file"].id,
            test_data["symbol"].id,
            content="def test_function():\n    return 'hello'",
            chunk_name="test_function",
        )

        db_chunk, is_new = await persister.persist_chunk(chunk1)
        await session.commit()

        print(f"\n✅ Chunk persisted")
        print(f"  - Is New: {is_new}")
        print(f"  - ID: {db_chunk.id}")
        print(f"  - Chunk Type: {db_chunk.chunk_type}")
        print(f"  - Chunk Name: {db_chunk.chunk_name}")
        print(f"  - Content Hash: {db_chunk.content_hash[:16]}...")
        print(f"  - Token Count: {db_chunk.token_count}")

        # Verify in database
        stmt = select(RepositoryChunk).where(
            RepositoryChunk.repository_id == test_data["repository"].id
        )
        result = await session.execute(stmt)
        chunks = result.scalars().all()
        print(f"  - Total chunks in DB: {len(chunks)}")

        # Test 2: Duplicate prevention (same content hash)
        print("\n" + "=" * 70)
        print("TEST 2: Duplicate Prevention")
        print("=" * 70)

        chunk2 = create_chunk_result(
            test_data["repository"].id,
            test_data["file"].id,
            test_data["symbol"].id,
            content="def test_function():\n    return 'hello'",  # Same content
            chunk_name="test_function",
        )

        db_chunk2, is_new2 = await persister.persist_chunk(chunk2)
        await session.commit()

        print(f"\n✅ Duplicate check completed")
        print(f"  - Is New: {is_new2}")
        print(f"  - Same ID: {db_chunk.id == db_chunk2.id}")
        print(f"  - Content Hash: {db_chunk2.content_hash[:16]}...")

        # Verify still only 1 chunk
        result = await session.execute(stmt)
        chunks = result.scalars().all()
        print(f"  - Total chunks in DB: {len(chunks)} (should be 1)")

        if len(chunks) == 1:
            print("  ✅ No duplicate created")
        else:
            print("  ❌ Duplicate was created!")

        # Test 3: Update when content changes
        print("\n" + "=" * 70)
        print("TEST 3: Update Changed Content")
        print("=" * 70)

        chunk3 = create_chunk_result(
            test_data["repository"].id,
            test_data["file"].id,
            test_data["symbol"].id,
            content="def test_function():\n    return 'world'",  # Different content
            chunk_name="test_function",
        )

        db_chunk3, is_new3 = await persister.persist_chunk(chunk3, force_update=True)
        await session.commit()

        print(f"\n✅ Update completed")
        print(f"  - Is New: {is_new3}")
        print(f"  - Same ID: {db_chunk.id == db_chunk3.id}")
        print(f"  - Old Hash: {db_chunk.content_hash[:16]}...")
        print(f"  - New Hash: {db_chunk3.content_hash[:16]}...")
        print(f"  - Content Changed: {db_chunk.content_hash != db_chunk3.content_hash}")

        # Verify still only 1 chunk
        result = await session.execute(stmt)
        chunks = result.scalars().all()
        print(f"  - Total chunks in DB: {len(chunks)} (should be 1)")

        # Test 4: Batch persistence
        print("\n" + "=" * 70)
        print("TEST 4: Batch Persistence")
        print("=" * 70)

        # Create multiple chunks
        batch_chunks = []
        for i in range(5):
            symbol_id = uuid4()
            symbol = RepositorySymbol(
                id=symbol_id,
                repository_file_id=test_data["file"].id,
                symbol_name=f"func_{i}",
                symbol_type="function",
                start_line=i * 10,
                end_line=(i * 10) + 5,
                language="python",
                signature=f"def func_{i}():",
            )
            session.add(symbol)

            chunk = create_chunk_result(
                test_data["repository"].id,
                test_data["file"].id,
                symbol_id,
                content=f"def func_{i}():\n    return {i}",
                chunk_name=f"func_{i}",
            )
            batch_chunks.append(chunk)

        await session.commit()

        stats = await persister.persist_chunks(batch_chunks)

        print(f"\n✅ Batch persistence completed")
        print(f"  - Created: {stats['created']}")
        print(f"  - Updated: {stats['updated']}")
        print(f"  - Unchanged: {stats['unchanged']}")

        # Verify total chunks
        result = await session.execute(stmt)
        chunks = result.scalars().all()
        print(f"  - Total chunks in DB: {len(chunks)} (should be 6)")

        # Test 5: Repository update (re-analysis)
        print("\n" + "=" * 70)
        print("TEST 5: Repository Update After Re-analysis")
        print("=" * 70)

        # Simulate re-analysis with some changes:
        # - func_0: unchanged
        # - func_1: modified
        # - func_2: deleted (not in new list)
        # - func_3: unchanged
        # - func_4: modified
        # - func_5: new

        new_chunks_after_reanalysis = []

        # func_0: unchanged
        new_chunks_after_reanalysis.append(batch_chunks[0])

        # func_1: modified
        symbol_1_id = batch_chunks[1].symbol_id
        modified_chunk_1 = create_chunk_result(
            test_data["repository"].id,
            test_data["file"].id,
            symbol_1_id,
            content=f"def func_1():\n    return 'modified'",
            chunk_name="func_1",
        )
        new_chunks_after_reanalysis.append(modified_chunk_1)

        # func_2: deleted (not added to new list)

        # func_3: unchanged
        new_chunks_after_reanalysis.append(batch_chunks[3])

        # func_4: modified
        symbol_4_id = batch_chunks[4].symbol_id
        modified_chunk_4 = create_chunk_result(
            test_data["repository"].id,
            test_data["file"].id,
            symbol_4_id,
            content=f"def func_4():\n    return 'also modified'",
            chunk_name="func_4",
        )
        new_chunks_after_reanalysis.append(modified_chunk_4)

        # func_5: new
        symbol_5_id = uuid4()
        symbol_5 = RepositorySymbol(
            id=symbol_5_id,
            repository_file_id=test_data["file"].id,
            symbol_name="func_5",
            symbol_type="function",
            start_line=50,
            end_line=55,
            language="python",
            signature="def func_5():",
        )
        session.add(symbol_5)
        await session.commit()

        new_chunk_5 = create_chunk_result(
            test_data["repository"].id,
            test_data["file"].id,
            symbol_5_id,
            content="def func_5():\n    return 'new function'",
            chunk_name="func_5",
        )
        new_chunks_after_reanalysis.append(new_chunk_5)

        # Also add the original test_function
        new_chunks_after_reanalysis.append(chunk3)

        update_stats = await persister.update_repository_chunks(
            test_data["repository"].id, new_chunks_after_reanalysis
        )

        print(f"\n✅ Repository update completed")
        print(f"  - Created: {update_stats['created']} (expected: 1 - func_5)")
        print(f"  - Updated: {update_stats['updated']} (expected: 2 - func_1, func_4)")
        print(
            f"  - Deleted: {update_stats['deleted']} (expected: 1 - func_2)"
        )
        print(
            f"  - Unchanged: {update_stats['unchanged']} (expected: 3 - test_function, func_0, func_3)"
        )

        # Verify final count
        result = await session.execute(stmt)
        chunks = result.scalars().all()
        print(f"  - Total chunks in DB: {len(chunks)} (should be 6)")

        # Test 6: Statistics
        print("\n" + "=" * 70)
        print("TEST 6: Chunk Statistics")
        print("=" * 70)

        stats = await persister.get_chunk_statistics(test_data["repository"].id)

        print(f"\n✅ Statistics retrieved")
        print(f"  - Total Chunks: {stats['total_chunks']}")
        print(f"  - By Type: {stats['by_type']}")
        print(f"  - By Language: {stats['by_language']}")
        print(f"  - Total Tokens: {stats['total_tokens']}")
        print(f"  - Avg Tokens: {stats['avg_tokens']}")
        print(f"  - Min Tokens: {stats['min_tokens']}")
        print(f"  - Max Tokens: {stats['max_tokens']}")

        # Test 7: Cleanup
        print("\n" + "=" * 70)
        print("TEST 7: Delete Repository Chunks")
        print("=" * 70)

        deleted_count = await persister.delete_repository_chunks(
            test_data["repository"].id
        )

        print(f"\n✅ Deletion completed")
        print(f"  - Deleted: {deleted_count} chunks")

        # Verify empty
        result = await session.execute(stmt)
        chunks = result.scalars().all()
        print(f"  - Total chunks in DB: {len(chunks)} (should be 0)")

    await engine.dispose()

    print("\n" + "=" * 70)
    print("✅ ALL TESTS COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(test_chunk_persistence())


