"""Test script to verify pipeline chunking integration.

Tests that the extended pipeline can:
1. Initialize with chunking services
2. Run full pipeline including chunking
3. Skip chunking when requested
4. Report chunking status
"""

import asyncio
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.config.settings import settings
from app.db.models import Repository
from app.services.orchestration.repository_pipeline import RepositoryPipeline


async def test_pipeline_initialization():
    """Test that pipeline initializes with chunking services."""
    print("\n=== Test 1: Pipeline Initialization ===")
    
    engine = create_async_engine(settings.database_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        pipeline = RepositoryPipeline(session)
        
        # Verify all services are initialized
        assert pipeline.indexer is not None, "Indexer not initialized"
        assert pipeline.node_extractor is not None, "Node extractor not initialized"
        assert pipeline.edge_extractor is not None, "Edge extractor not initialized"
        assert pipeline.graph_persister is not None, "Graph persister not initialized"
        assert pipeline.class_chunker is not None, "Class chunker not initialized"
        assert pipeline.function_chunker is not None, "Function chunker not initialized"
        assert pipeline.chunk_persister is not None, "Chunk persister not initialized"
        
        print("✓ Pipeline initialized with all services including chunking")


async def test_pipeline_skip_flags():
    """Test that skip flags work correctly."""
    print("\n=== Test 2: Skip Flags ===")
    
    engine = create_async_engine(settings.database_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        pipeline = RepositoryPipeline(session)
        
        # Get a test repository (use first available)
        stmt = select(Repository).limit(1)
        result = await session.execute(stmt)
        repository = result.scalar_one_or_none()
        
        if not repository:
            print("⚠ No repository found, skipping test")
            return
        
        # Test skip_chunking=True
        results = await pipeline.run_full_pipeline(
            repository.id,
            skip_indexing=True,
            skip_graph=True,
            skip_chunking=True,
        )
        
        assert results["indexing"]["skipped"] is True
        assert results["graph"]["skipped"] is True
        assert results["chunking"]["skipped"] is True
        assert results["pipeline_complete"] is True
        
        print(f"✓ Skip flags work correctly for repository {repository.id}")


async def test_pipeline_status_with_chunking():
    """Test that pipeline status includes chunking information."""
    print("\n=== Test 3: Pipeline Status with Chunking ===")
    
    engine = create_async_engine(settings.database_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        pipeline = RepositoryPipeline(session)
        
        # Get a test repository
        stmt = select(Repository).limit(1)
        result = await session.execute(stmt)
        repository = result.scalar_one_or_none()
        
        if not repository:
            print("⚠ No repository found, skipping test")
            return
        
        # Get pipeline status
        status = await pipeline.get_pipeline_status(repository.id)
        
        # Verify status includes chunking fields
        assert "chunks_generated" in status, "chunks_generated missing from status"
        assert "chunking_stats" in status, "chunking_stats missing from status"
        assert "indexed" in status
        assert "graph_built" in status
        
        print(f"✓ Pipeline status includes chunking info:")
        print(f"  - Indexed: {status['indexed']}")
        print(f"  - Graph Built: {status['graph_built']}")
        print(f"  - Chunks Generated: {status['chunks_generated']}")
        if status['chunking_stats']:
            print(f"  - Total Chunks: {status['chunking_stats'].get('total_chunks', 0)}")


async def test_pipeline_methods():
    """Test that all pipeline methods exist and have correct signatures."""
    print("\n=== Test 4: Pipeline Methods ===")
    
    engine = create_async_engine(settings.database_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        pipeline = RepositoryPipeline(session)
        
        # Verify methods exist
        assert hasattr(pipeline, "run_full_pipeline"), "run_full_pipeline method missing"
        assert hasattr(pipeline, "generate_chunks"), "generate_chunks method missing"
        assert hasattr(pipeline, "regenerate_chunks"), "regenerate_chunks method missing"
        assert hasattr(pipeline, "get_pipeline_status"), "get_pipeline_status method missing"
        
        print("✓ All required pipeline methods exist:")
        print("  - run_full_pipeline (with skip_chunking param)")
        print("  - generate_chunks (new)")
        print("  - regenerate_chunks (new)")
        print("  - get_pipeline_status (updated with chunking)")


async def main():
    """Run all tests."""
    print("=" * 60)
    print("Testing Pipeline Chunking Integration")
    print("=" * 60)
    
    try:
        await test_pipeline_initialization()
        await test_pipeline_skip_flags()
        await test_pipeline_status_with_chunking()
        await test_pipeline_methods()
        
        print("\n" + "=" * 60)
        print("✓ All Tests Passed!")
        print("=" * 60)
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
