"""Test script for Chunk APIs.

Tests all chunk endpoints:
- POST /repositories/{id}/chunk
- GET /repositories/{id}/chunks
- GET /repositories/{id}/chunks/{id}
- GET /repositories/{id}/chunks/search
"""

import asyncio
import json
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.api.deps import get_db
from app.db.base import Base
from app.db.models.repository import Repository
from app.db.models.repository_file import RepositoryFile
from app.db.models.repository_node import RepositoryNode
from app.db.models.repository_symbol import RepositorySymbol
from app.main import app

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
    """Create test repository with symbols."""
    # Create temporary test file
    test_file_path = Path("test_api.py")
    test_file_content = '''"""Test module."""

import os
import sys


def hello_world():
    """Say hello."""
    return "Hello, World!"


def goodbye_world():
    """Say goodbye."""
    return "Goodbye, World!"


class Greeter:
    """A greeter class."""
    
    def greet(self, name: str) -> str:
        """Greet someone."""
        return f"Hello, {name}!"
    
    def farewell(self, name: str) -> str:
        """Say farewell."""
        return f"Goodbye, {name}!"
'''

    test_file_path.write_text(test_file_content)

    try:
        # Create repository
        repo = Repository(
            id=uuid4(),
            owner="test",
            name="test-api",
            full_name="test/test-api",
            branch="main",
            clone_path=str(test_file_path.parent.absolute()),
            default_branch="main",
            private=False,
        )
        session.add(repo)

        # Create file
        file = RepositoryFile(
            id=uuid4(),
            repository_id=repo.id,
            relative_path="test_api.py",
            absolute_path=str(test_file_path.absolute()),
            file_name="test_api.py",
            extension=".py",
            language="python",
            size_bytes=len(test_file_content),
            line_count=test_file_content.count("\n") + 1,
            sha256_hash="abc123",
            last_modified=datetime.now(),
            is_binary=False,
        )
        session.add(file)

        # Create import symbols
        import1 = RepositorySymbol(
            id=uuid4(),
            repository_file_id=file.id,
            symbol_name="os",
            symbol_type="import",
            start_line=3,
            end_line=3,
            language="python",
            signature="import os",
        )
        session.add(import1)

        import2 = RepositorySymbol(
            id=uuid4(),
            repository_file_id=file.id,
            symbol_name="sys",
            symbol_type="import",
            start_line=4,
            end_line=4,
            language="python",
            signature="import sys",
        )
        session.add(import2)

        # Create function symbols
        hello_func = RepositorySymbol(
            id=uuid4(),
            repository_file_id=file.id,
            symbol_name="hello_world",
            symbol_type="function",
            start_line=7,
            end_line=9,
            language="python",
            signature="def hello_world():",
            symbol_metadata=json.dumps({
                "docstring": "Say hello.",
                "parameters": [],
                "return_type": "str",
            }),
        )
        session.add(hello_func)

        goodbye_func = RepositorySymbol(
            id=uuid4(),
            repository_file_id=file.id,
            symbol_name="goodbye_world",
            symbol_type="function",
            start_line=12,
            end_line=14,
            language="python",
            signature="def goodbye_world():",
            symbol_metadata=json.dumps({
                "docstring": "Say goodbye.",
                "parameters": [],
                "return_type": "str",
            }),
        )
        session.add(goodbye_func)

        # Create class
        greeter_class = RepositorySymbol(
            id=uuid4(),
            repository_file_id=file.id,
            symbol_name="Greeter",
            symbol_type="class",
            start_line=17,
            end_line=27,
            language="python",
            signature="class Greeter:",
            symbol_metadata=json.dumps({
                "docstring": "A greeter class.",
            }),
        )
        session.add(greeter_class)

        # Create methods
        greet_method = RepositorySymbol(
            id=uuid4(),
            repository_file_id=file.id,
            symbol_name="greet",
            symbol_type="method",
            parent_symbol=greeter_class.id,
            start_line=20,
            end_line=22,
            language="python",
            signature="def greet(self, name: str) -> str:",
            symbol_metadata=json.dumps({
                "docstring": "Greet someone.",
                "parameters": ["self", "name"],
                "return_type": "str",
            }),
        )
        session.add(greet_method)

        farewell_method = RepositorySymbol(
            id=uuid4(),
            repository_file_id=file.id,
            symbol_name="farewell",
            symbol_type="method",
            parent_symbol=greeter_class.id,
            start_line=24,
            end_line=26,
            language="python",
            signature="def farewell(self, name: str) -> str:",
            symbol_metadata=json.dumps({
                "docstring": "Say farewell.",
                "parameters": ["self", "name"],
                "return_type": "str",
            }),
        )
        session.add(farewell_method)

        # Create graph nodes
        repo_node = RepositoryNode(
            id=uuid4(),
            repository_id=repo.id,
            node_type="repository",
            display_name="test-api",
        )
        session.add(repo_node)

        await session.commit()

        return {
            "repository": repo,
            "file": file,
            "test_file_path": test_file_path,
        }

    except Exception as e:
        await session.rollback()
        if test_file_path.exists():
            test_file_path.unlink()
        raise e


async def test_chunk_apis():
    """Test Chunk APIs."""
    print("=" * 70)
    print("CHUNK API TESTS")
    print("=" * 70)

    # Setup database
    engine, async_session_factory = await setup_test_database()

    async with async_session_factory() as session:
        # Create test data
        print("\n[*] Creating test data...")
        test_data = await create_test_data(session)
        repo_id = str(test_data["repository"].id)
        print("[OK] Test data created")

        # Override get_session dependency
        async def override_get_session():
            async with async_session_factory() as s:
                yield s

        app.dependency_overrides[get_db] = override_get_session

        # Create test client
        client = TestClient(app)

        # Test 1: POST /repositories/{id}/chunk - Create chunks
        print("\n" + "=" * 70)
        print("TEST 1: POST /repositories/{id}/chunk")
        print("=" * 70)

        response = client.post(
            f"/api/v1/repositories/{repo_id}/chunk",
            params={
                "include_classes": True,
                "include_functions": True,
                "include_methods": True,
            },
        )

        print(f"\nStatus Code: {response.status_code}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"

        data = response.json()
        print(f"[OK] Chunks created successfully")
        print(f"  - Repository ID: {data['repository_id']}")
        print(f"  - Total Chunks: {data['total_chunks']}")
        print(f"  - Created: {data['created']}")
        print(f"  - Updated: {data['updated']}")
        print(f"  - Deleted: {data['deleted']}")
        print(f"  - Unchanged: {data['unchanged']}")

        assert data["total_chunks"] > 0, "Should have created chunks"
        assert data["created"] > 0, "Should have created at least one chunk"

        # Test 2: GET /repositories/{id}/chunks - List all chunks
        print("\n" + "=" * 70)
        print("TEST 2: GET /repositories/{id}/chunks")
        print("=" * 70)

        response = client.get(f"/api/v1/repositories/{repo_id}/chunks")

        print(f"\nStatus Code: {response.status_code}")
        assert response.status_code == 200

        data = response.json()
        print(f"[OK] Chunks listed successfully")
        print(f"  - Total: {data['total']}")
        print(f"  - Count: {data['count']}")
        print(f"  - Chunks returned: {len(data['chunks'])}")

        assert data["total"] > 0, "Should have chunks"
        assert len(data["chunks"]) > 0, "Should return chunks"

        # Save first chunk ID for later tests
        first_chunk = data["chunks"][0]
        chunk_id = first_chunk["id"]

        print(f"\n  First chunk:")
        print(f"    - ID: {first_chunk['id']}")
        print(f"    - Type: {first_chunk['chunk_type']}")
        print(f"    - Name: {first_chunk['chunk_name']}")
        print(f"    - Language: {first_chunk['language']}")
        print(f"    - Tokens: {first_chunk['token_count']}")

        # Test 3: GET /repositories/{id}/chunks with filters
        print("\n" + "=" * 70)
        print("TEST 3: GET /repositories/{id}/chunks (with filters)")
        print("=" * 70)

        # Filter by chunk type
        response = client.get(
            f"/api/v1/repositories/{repo_id}/chunks",
            params={"chunk_type": "function"},
        )

        print(f"\nStatus Code: {response.status_code}")
        assert response.status_code == 200

        data = response.json()
        print(f"[OK] Filtered by type=function")
        print(f"  - Total: {data['total']}")
        print(f"  - Count: {data['count']}")

        # Verify all returned chunks are functions
        for chunk in data["chunks"]:
            assert chunk["chunk_type"] == "function", "Should only return functions"

        # Filter by language
        response = client.get(
            f"/api/v1/repositories/{repo_id}/chunks",
            params={"language": "python"},
        )

        data = response.json()
        print(f"\n[OK] Filtered by language=python")
        print(f"  - Total: {data['total']}")

        # Test pagination
        response = client.get(
            f"/api/v1/repositories/{repo_id}/chunks",
            params={"limit": 2, "offset": 0},
        )

        data = response.json()
        print(f"\n[OK] Pagination (limit=2)")
        print(f"  - Count: {data['count']} (should be 2)")
        assert data["count"] <= 2, "Should respect limit"

        # Test 4: GET /repositories/{id}/chunks/{chunk_id} - Get specific chunk
        print("\n" + "=" * 70)
        print("TEST 4: GET /repositories/{id}/chunks/{chunk_id}")
        print("=" * 70)

        response = client.get(f"/api/v1/repositories/{repo_id}/chunks/{chunk_id}")

        print(f"\nStatus Code: {response.status_code}")
        assert response.status_code == 200

        data = response.json()
        print(f"[OK] Chunk retrieved successfully")
        print(f"  - ID: {data['id']}")
        print(f"  - Type: {data['chunk_type']}")
        print(f"  - Name: {data['chunk_name']}")
        print(f"  - Language: {data['language']}")
        print(f"  - Tokens: {data['token_count']}")
        print(f"  - Content Hash: {data['content_hash'][:16]}...")
        print(f"  - Has Metadata: {'metadata' in data}")
        print(f"  - Content Length: {len(data['content'])} chars")

        assert data["id"] == chunk_id, "Should return requested chunk"

        # Test 5: GET /repositories/{id}/chunks/search - Search chunks
        print("\n" + "=" * 70)
        print("TEST 5: GET /repositories/{id}/chunks/search")
        print("=" * 70)

        # Search for "hello"
        response = client.get(
            f"/api/v1/repositories/{repo_id}/chunks/search",
            params={"q": "hello"},
        )

        print(f"\nStatus Code: {response.status_code}")
        assert response.status_code == 200

        data = response.json()
        print(f"[OK] Search completed: query='hello'")
        print(f"  - Count: {data['count']}")
        print(f"  - Query: {data['query']}")

        if data["count"] > 0:
            print(f"\n  Matching chunks:")
            for result in data["results"]:
                print(f"    - {result['chunk_name']} ({result['chunk_type']})")

        # Search for "goodbye"
        response = client.get(
            f"/api/v1/repositories/{repo_id}/chunks/search",
            params={"q": "goodbye"},
        )

        data = response.json()
        print(f"\n[OK] Search completed: query='goodbye'")
        print(f"  - Count: {data['count']}")

        # Search with type filter
        response = client.get(
            f"/api/v1/repositories/{repo_id}/chunks/search",
            params={"q": "greet", "chunk_type": "method"},
        )

        data = response.json()
        print(f"\n[OK] Search with filter: query='greet', type='method'")
        print(f"  - Count: {data['count']}")

        # Test 6: GET /repositories/{id}/chunks/statistics
        print("\n" + "=" * 70)
        print("TEST 6: GET /repositories/{id}/chunks/statistics")
        print("=" * 70)

        response = client.get(f"/api/v1/repositories/{repo_id}/chunks/statistics")

        print(f"\nStatus Code: {response.status_code}")
        assert response.status_code == 200

        data = response.json()
        print(f"[OK] Statistics retrieved")
        print(f"  - Total Chunks: {data['total_chunks']}")
        print(f"  - By Type: {data['by_type']}")
        print(f"  - By Language: {data['by_language']}")
        print(f"  - Total Tokens: {data['total_tokens']}")
        print(f"  - Avg Tokens: {data['avg_tokens']}")
        print(f"  - Min Tokens: {data['min_tokens']}")
        print(f"  - Max Tokens: {data['max_tokens']}")

        # Test 7: Error handling - Repository not found
        print("\n" + "=" * 70)
        print("TEST 7: Error Handling")
        print("=" * 70)

        fake_repo_id = str(uuid4())
        response = client.get(f"/api/v1/repositories/{fake_repo_id}/chunks")

        print(f"\nStatus Code: {response.status_code}")
        assert response.status_code == 404, "Should return 404 for non-existent repo"
        print("[OK] Correctly returns 404 for non-existent repository")

        # Test 8: Error handling - Chunk not found
        fake_chunk_id = str(uuid4())
        response = client.get(
            f"/api/v1/repositories/{repo_id}/chunks/{fake_chunk_id}"
        )

        print(f"\nStatus Code: {response.status_code}")
        assert response.status_code == 404, "Should return 404 for non-existent chunk"
        print("[OK] Correctly returns 404 for non-existent chunk")

        # Cleanup
        print("\n" + "=" * 70)
        print("CLEANUP")
        print("=" * 70)

        test_file_path = test_data["test_file_path"]
        if test_file_path.exists():
            test_file_path.unlink()
            print("[OK] Test file removed")

    await engine.dispose()

    print("\n" + "=" * 70)
    print("[OK] ALL API TESTS COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(test_chunk_apis())


