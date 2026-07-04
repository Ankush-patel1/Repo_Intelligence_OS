"""Test script for class-based chunking.

Demonstrates the ClassChunker functionality with mock data.
"""

import asyncio
import json
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.db.models.repository import Repository
from app.db.models.repository_edge import RepositoryEdge
from app.db.models.repository_file import RepositoryFile
from app.db.models.repository_node import RepositoryNode
from app.db.models.repository_symbol import RepositorySymbol
from app.services.chunking.class_chunker import ClassChunker


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
    """Create test data for class chunking demonstration.

    Creates:
    - Repository
    - Python file with a class
    - Class symbol with methods
    - Graph nodes and edges
    """
    # Create temporary test file
    test_file_path = Path("test_sample.py")
    test_file_content = '''"""Sample module for testing class chunking."""

import json
from typing import List, Optional
from datetime import datetime


class UserManager:
    """Manages user operations.
    
    This class handles user creation, retrieval, and deletion
    with built-in validation and error handling.
    """
    
    def __init__(self, db_connection):
        """Initialize user manager.
        
        Args:
            db_connection: Database connection object
        """
        self.db = db_connection
        self.cache = {}
    
    def create_user(self, username: str, email: str) -> Optional[dict]:
        """Create a new user.
        
        Args:
            username: The username for the new user
            email: The email address
            
        Returns:
            User dictionary if successful, None otherwise
        """
        if not self._validate_email(email):
            return None
        
        user_data = {
            "username": username,
            "email": email,
            "created_at": datetime.now()
        }
        
        user_id = self.db.insert("users", user_data)
        user_data["id"] = user_id
        self.cache[user_id] = user_data
        
        return user_data
    
    def get_user(self, user_id: int) -> Optional[dict]:
        """Retrieve user by ID.
        
        Args:
            user_id: The user ID to retrieve
            
        Returns:
            User dictionary if found, None otherwise
        """
        if user_id in self.cache:
            return self.cache[user_id]
        
        user_data = self.db.query("users", {"id": user_id})
        if user_data:
            self.cache[user_id] = user_data
        
        return user_data
    
    def delete_user(self, user_id: int) -> bool:
        """Delete a user.
        
        Args:
            user_id: The user ID to delete
            
        Returns:
            True if successful, False otherwise
        """
        if user_id in self.cache:
            del self.cache[user_id]
        
        return self.db.delete("users", {"id": user_id})
    
    def _validate_email(self, email: str) -> bool:
        """Validate email format.
        
        Args:
            email: Email to validate
            
        Returns:
            True if valid, False otherwise
        """
        return "@" in email and "." in email


class AdminManager(UserManager):
    """Manages admin user operations.
    
    Extends UserManager with admin-specific functionality.
    """
    
    def grant_admin_privileges(self, user_id: int) -> bool:
        """Grant admin privileges to a user.
        
        Args:
            user_id: The user ID to grant privileges
            
        Returns:
            True if successful, False otherwise
        """
        user = self.get_user(user_id)
        if not user:
            return False
        
        return self.db.update("users", {"id": user_id}, {"is_admin": True})
'''

    test_file_path.write_text(test_file_content)

    try:
        # Create repository
        repo = Repository(
            id=uuid4(),
            owner="test",
            name="test-repo",
            full_name="test/test-repo",
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
            relative_path="test_sample.py",
            absolute_path=str(test_file_path.absolute()),
            file_name="test_sample.py",
            extension=".py",
            language="python",
            size_bytes=len(test_file_content),
            line_count=test_file_content.count("\n") + 1,
            sha256_hash="abc123",
            last_modified=datetime.utcnow(),
            is_binary=False,
        )
        session.add(file)

        # Create import symbols
        import1 = RepositorySymbol(
            id=uuid4(),
            repository_file_id=file.id,
            symbol_name="json",
            symbol_type="import",
            start_line=3,
            end_line=3,
            language="python",
            signature="import json",
        )
        session.add(import1)

        import2 = RepositorySymbol(
            id=uuid4(),
            repository_file_id=file.id,
            symbol_name="List, Optional",
            symbol_type="import",
            start_line=4,
            end_line=4,
            language="python",
            signature="from typing import List, Optional",
        )
        session.add(import2)

        import3 = RepositorySymbol(
            id=uuid4(),
            repository_file_id=file.id,
            symbol_name="datetime",
            symbol_type="import",
            start_line=5,
            end_line=5,
            language="python",
            signature="from datetime import datetime",
        )
        session.add(import3)

        # Create UserManager class symbol
        class_metadata = {
            "docstring": "Manages user operations.\n\nThis class handles user creation, retrieval, and deletion\nwith built-in validation and error handling.",
            "access_modifier": "public",
            "is_abstract": False,
        }

        user_manager_class = RepositorySymbol(
            id=uuid4(),
            repository_file_id=file.id,
            symbol_name="UserManager",
            symbol_type="class",
            start_line=8,
            end_line=88,
            language="python",
            signature="class UserManager:",
            symbol_metadata=json.dumps(class_metadata),
        )
        session.add(user_manager_class)

        # Create method symbols for UserManager
        methods = [
            {
                "name": "__init__",
                "start": 14,
                "end": 21,
                "signature": "def __init__(self, db_connection):",
            },
            {
                "name": "create_user",
                "start": 23,
                "end": 47,
                "signature": "def create_user(self, username: str, email: str) -> Optional[dict]:",
            },
            {
                "name": "get_user",
                "start": 49,
                "end": 65,
                "signature": "def get_user(self, user_id: int) -> Optional[dict]:",
            },
            {
                "name": "delete_user",
                "start": 67,
                "end": 79,
                "signature": "def delete_user(self, user_id: int) -> bool:",
            },
            {
                "name": "_validate_email",
                "start": 81,
                "end": 88,
                "signature": "def _validate_email(self, email: str) -> bool:",
            },
        ]

        method_symbols = []
        for method in methods:
            method_symbol = RepositorySymbol(
                id=uuid4(),
                repository_file_id=file.id,
                symbol_name=method["name"],
                symbol_type="method",
                parent_symbol=user_manager_class.id,
                start_line=method["start"],
                end_line=method["end"],
                language="python",
                signature=method["signature"],
            )
            session.add(method_symbol)
            method_symbols.append(method_symbol)

        # Create AdminManager class (inherits from UserManager)
        admin_class_metadata = {
            "docstring": "Manages admin user operations.\n\nExtends UserManager with admin-specific functionality.",
            "access_modifier": "public",
            "is_abstract": False,
        }

        admin_manager_class = RepositorySymbol(
            id=uuid4(),
            repository_file_id=file.id,
            symbol_name="AdminManager",
            symbol_type="class",
            start_line=91,
            end_line=108,
            language="python",
            signature="class AdminManager(UserManager):",
            symbol_metadata=json.dumps(admin_class_metadata),
        )
        session.add(admin_manager_class)

        # Create method for AdminManager
        admin_method = RepositorySymbol(
            id=uuid4(),
            repository_file_id=file.id,
            symbol_name="grant_admin_privileges",
            symbol_type="method",
            parent_symbol=admin_manager_class.id,
            start_line=97,
            end_line=108,
            language="python",
            signature="def grant_admin_privileges(self, user_id: int) -> bool:",
        )
        session.add(admin_method)

        # Create graph nodes
        repo_node = RepositoryNode(
            id=uuid4(),
            repository_id=repo.id,
            node_type="repository",
            display_name="test-repo",
        )
        session.add(repo_node)

        file_node = RepositoryNode(
            id=uuid4(),
            repository_id=repo.id,
            repository_file_id=file.id,
            node_type="file",
            display_name="test_sample.py",
            language="python",
        )
        session.add(file_node)

        user_manager_node = RepositoryNode(
            id=uuid4(),
            repository_id=repo.id,
            repository_file_id=file.id,
            symbol_id=user_manager_class.id,
            node_type="symbol",
            display_name="UserManager",
            language="python",
            node_metadata=json.dumps({"symbol_type": "class"}),
        )
        session.add(user_manager_node)

        admin_manager_node = RepositoryNode(
            id=uuid4(),
            repository_id=repo.id,
            repository_file_id=file.id,
            symbol_id=admin_manager_class.id,
            node_type="symbol",
            display_name="AdminManager",
            language="python",
            node_metadata=json.dumps({"symbol_type": "class"}),
        )
        session.add(admin_manager_node)

        # Create edges (relationships)
        # Repo contains file
        edge1 = RepositoryEdge(
            id=uuid4(),
            source_node_id=repo_node.id,
            target_node_id=file_node.id,
            relationship_type="CONTAINS",
        )
        session.add(edge1)

        # File contains UserManager class
        edge2 = RepositoryEdge(
            id=uuid4(),
            source_node_id=file_node.id,
            target_node_id=user_manager_node.id,
            relationship_type="CONTAINS",
        )
        session.add(edge2)

        # File contains AdminManager class
        edge3 = RepositoryEdge(
            id=uuid4(),
            source_node_id=file_node.id,
            target_node_id=admin_manager_node.id,
            relationship_type="CONTAINS",
        )
        session.add(edge3)

        # AdminManager inherits from UserManager
        edge4 = RepositoryEdge(
            id=uuid4(),
            source_node_id=admin_manager_node.id,
            target_node_id=user_manager_node.id,
            relationship_type="INHERITS",
        )
        session.add(edge4)

        await session.commit()

        return {
            "repository": repo,
            "file": file,
            "user_manager_class": user_manager_class,
            "admin_manager_class": admin_manager_class,
            "user_manager_node": user_manager_node,
            "admin_manager_node": admin_manager_node,
            "test_file_path": test_file_path,
        }

    except Exception as e:
        await session.rollback()
        # Clean up test file
        if test_file_path.exists():
            test_file_path.unlink()
        raise e


async def test_class_chunking():
    """Test class chunking functionality."""
    print("=" * 70)
    print("CLASS-BASED SEMANTIC CHUNKING TEST")
    print("=" * 70)

    # Setup database
    engine, async_session_factory = await setup_test_database()

    async with async_session_factory() as session:
        # Create test data
        print("\n📦 Creating test data...")
        test_data = await create_test_data(session)
        print("✅ Test data created")

        # Initialize chunker
        chunker = ClassChunker(session)

        # Test 1: Chunk UserManager class
        print("\n" + "=" * 70)
        print("TEST 1: Chunk UserManager Class")
        print("=" * 70)

        try:
            chunk = await chunker.chunk_class(test_data["user_manager_class"].id)

            print("\n✅ Successfully created chunk for UserManager")
            print(f"\nChunk Details:")
            print(f"  - Type: {chunk.chunk_type}")
            print(f"  - Name: {chunk.chunk_name}")
            print(f"  - Language: {chunk.language}")
            print(f"  - Token Count: {chunk.token_count}")
            print(f"  - Content Hash: {chunk.content_hash[:16]}...")
            print(f"  - Lines: {chunk.metadata.start_line}-{chunk.metadata.end_line}")

            print(f"\nMetadata:")
            print(f"  - Symbol Type: {chunk.metadata.symbol_type}")
            print(f"  - Signature: {chunk.metadata.signature}")
            print(f"  - Method Count: {chunk.metadata.method_count}")
            print(f"  - Is Abstract: {chunk.metadata.is_abstract}")
            print(f"  - Access Modifier: {chunk.metadata.access_modifier}")
            print(f"  - Node ID: {chunk.metadata.node_id}")

            print(f"\nContext:")
            print(f"  - Imports ({len(chunk.context.imports)}):")
            for imp in chunk.context.imports:
                print(f"    • {imp}")
            print(f"  - Dependencies: {len(chunk.context.dependencies)} symbols")
            print(f"  - Docstring: {chunk.context.docstring[:50]}..." if chunk.context.docstring else "  - Docstring: None")

            print(f"\nContent Preview (first 500 chars):")
            print("-" * 70)
            print(chunk.content[:500])
            print("...")
            print("-" * 70)

        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()

        # Test 2: Chunk AdminManager class (with inheritance)
        print("\n" + "=" * 70)
        print("TEST 2: Chunk AdminManager Class (with Inheritance)")
        print("=" * 70)

        try:
            chunk = await chunker.chunk_class(test_data["admin_manager_class"].id)

            print("\n✅ Successfully created chunk for AdminManager")
            print(f"\nChunk Details:")
            print(f"  - Type: {chunk.chunk_type}")
            print(f"  - Name: {chunk.chunk_name}")
            print(f"  - Language: {chunk.language}")
            print(f"  - Token Count: {chunk.token_count}")
            print(f"  - Lines: {chunk.metadata.start_line}-{chunk.metadata.end_line}")

            print(f"\nMetadata:")
            print(f"  - Method Count: {chunk.metadata.method_count}")
            print(f"  - Inherits From: {chunk.metadata.inherits_from}")
            print(f"  - Implements: {chunk.metadata.implements}")

            print(f"\nContent Preview:")
            print("-" * 70)
            print(chunk.content)
            print("-" * 70)

        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()

        # Test 3: Chunk all classes in repository
        print("\n" + "=" * 70)
        print("TEST 3: Chunk All Classes in Repository")
        print("=" * 70)

        try:
            chunks = await chunker.chunk_all_classes(test_data["repository"].id)

            print(f"\n✅ Successfully chunked {len(chunks)} classes")
            for i, chunk in enumerate(chunks, 1):
                print(f"\n{i}. {chunk.chunk_name}")
                print(f"   - Type: {chunk.chunk_type}")
                print(f"   - Methods: {chunk.metadata.method_count}")
                print(f"   - Tokens: {chunk.token_count}")
                print(f"   - Imports: {len(chunk.context.imports)}")

        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()

        # Cleanup
        print("\n" + "=" * 70)
        print("CLEANUP")
        print("=" * 70)

        test_file_path = test_data["test_file_path"]
        if test_file_path.exists():
            test_file_path.unlink()
            print("✅ Test file removed")

    await engine.dispose()

    print("\n" + "=" * 70)
    print("✅ ALL TESTS COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(test_class_chunking())


