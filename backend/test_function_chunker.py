"""Test script for function-based chunking.

Demonstrates the FunctionChunker functionality with mock data.
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
from app.services.chunking.function_chunker import FunctionChunker


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
    """Create test data for function chunking demonstration.

    Creates:
    - Repository
    - Python file with functions and a class with methods
    - Function symbols
    - Method symbols
    - Graph nodes and edges
    """
    # Create temporary test file
    test_file_path = Path("test_functions.py")
    test_file_content = '''"""Sample module for testing function chunking."""

import json
import math
from typing import List, Dict, Optional


def calculate_sum(numbers: List[float]) -> float:
    """Calculate the sum of a list of numbers.
    
    Args:
        numbers: List of numbers to sum
        
    Returns:
        The sum of all numbers
    """
    total = 0.0
    for num in numbers:
        total = add_values(total, num)
    return total


def add_values(a: float, b: float) -> float:
    """Add two values together.
    
    Args:
        a: First value
        b: Second value
        
    Returns:
        Sum of a and b
    """
    return a + b


def format_result(value: float, precision: int = 2) -> str:
    """Format a numeric result as a string.
    
    Args:
        value: The numeric value to format
        precision: Number of decimal places (default: 2)
        
    Returns:
        Formatted string representation
    """
    return f"{value:.{precision}f}"


async def fetch_data(url: str) -> Optional[Dict]:
    """Fetch data from a URL asynchronously.
    
    Args:
        url: The URL to fetch from
        
    Returns:
        Parsed JSON data or None if failed
    """
    try:
        # Simulated async fetch
        data = json.loads('{"status": "ok"}')
        return data
    except Exception:
        return None


class Calculator:
    """Simple calculator class."""
    
    def __init__(self, precision: int = 2):
        """Initialize calculator.
        
        Args:
            precision: Decimal precision for results
        """
        self.precision = precision
        self.history = []
    
    def add(self, a: float, b: float) -> float:
        """Add two numbers.
        
        Args:
            a: First number
            b: Second number
            
        Returns:
            Sum of a and b
        """
        result = add_values(a, b)
        self.history.append(('add', a, b, result))
        return result
    
    def multiply(self, a: float, b: float) -> float:
        """Multiply two numbers.
        
        Args:
            a: First number
            b: Second number
            
        Returns:
            Product of a and b
        """
        result = a * b
        self.history.append(('multiply', a, b, result))
        return result
    
    def get_history(self) -> List[tuple]:
        """Get calculation history.
        
        Returns:
            List of (operation, a, b, result) tuples
        """
        return self.history.copy()
'''

    test_file_path.write_text(test_file_content)

    try:
        # Create repository
        repo = Repository(
            id=uuid4(),
            owner="test",
            name="test-functions",
            full_name="test/test-functions",
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
            relative_path="test_functions.py",
            absolute_path=str(test_file_path.absolute()),
            file_name="test_functions.py",
            extension=".py",
            language="python",
            size_bytes=len(test_file_content),
            line_count=test_file_content.count("\n") + 1,
            sha256_hash="def456",
            last_modified=datetime.now(),
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
            symbol_name="math",
            symbol_type="import",
            start_line=4,
            end_line=4,
            language="python",
            signature="import math",
        )
        session.add(import2)

        import3 = RepositorySymbol(
            id=uuid4(),
            repository_file_id=file.id,
            symbol_name="List, Dict, Optional",
            symbol_type="import",
            start_line=5,
            end_line=5,
            language="python",
            signature="from typing import List, Dict, Optional",
        )
        session.add(import3)

        # Create function symbols
        calculate_sum_func = RepositorySymbol(
            id=uuid4(),
            repository_file_id=file.id,
            symbol_name="calculate_sum",
            symbol_type="function",
            start_line=8,
            end_line=19,
            language="python",
            signature="def calculate_sum(numbers: List[float]) -> float:",
            symbol_metadata=json.dumps({
                "docstring": "Calculate the sum of a list of numbers.",
                "parameters": ["numbers"],
                "return_type": "float",
                "decorators": [],
                "is_async": False,
            }),
        )
        session.add(calculate_sum_func)

        add_values_func = RepositorySymbol(
            id=uuid4(),
            repository_file_id=file.id,
            symbol_name="add_values",
            symbol_type="function",
            start_line=22,
            end_line=32,
            language="python",
            signature="def add_values(a: float, b: float) -> float:",
            symbol_metadata=json.dumps({
                "docstring": "Add two values together.",
                "parameters": ["a", "b"],
                "return_type": "float",
                "decorators": [],
                "is_async": False,
            }),
        )
        session.add(add_values_func)

        format_result_func = RepositorySymbol(
            id=uuid4(),
            repository_file_id=file.id,
            symbol_name="format_result",
            symbol_type="function",
            start_line=35,
            end_line=45,
            language="python",
            signature="def format_result(value: float, precision: int = 2) -> str:",
            symbol_metadata=json.dumps({
                "docstring": "Format a numeric result as a string.",
                "parameters": ["value", "precision"],
                "return_type": "str",
                "decorators": [],
                "is_async": False,
            }),
        )
        session.add(format_result_func)

        fetch_data_func = RepositorySymbol(
            id=uuid4(),
            repository_file_id=file.id,
            symbol_name="fetch_data",
            symbol_type="function",
            start_line=48,
            end_line=60,
            language="python",
            signature="async def fetch_data(url: str) -> Optional[Dict]:",
            symbol_metadata=json.dumps({
                "docstring": "Fetch data from a URL asynchronously.",
                "parameters": ["url"],
                "return_type": "Optional[Dict]",
                "decorators": [],
                "is_async": True,
            }),
        )
        session.add(fetch_data_func)

        # Create Calculator class
        calculator_class = RepositorySymbol(
            id=uuid4(),
            repository_file_id=file.id,
            symbol_name="Calculator",
            symbol_type="class",
            start_line=63,
            end_line=115,
            language="python",
            signature="class Calculator:",
            symbol_metadata=json.dumps({
                "docstring": "Simple calculator class.",
            }),
        )
        session.add(calculator_class)

        # Create method symbols for Calculator
        init_method = RepositorySymbol(
            id=uuid4(),
            repository_file_id=file.id,
            symbol_name="__init__",
            symbol_type="method",
            parent_symbol=calculator_class.id,
            start_line=66,
            end_line=73,
            language="python",
            signature="def __init__(self, precision: int = 2):",
            symbol_metadata=json.dumps({
                "docstring": "Initialize calculator.",
                "parameters": ["self", "precision"],
                "decorators": [],
            }),
        )
        session.add(init_method)

        add_method = RepositorySymbol(
            id=uuid4(),
            repository_file_id=file.id,
            symbol_name="add",
            symbol_type="method",
            parent_symbol=calculator_class.id,
            start_line=75,
            end_line=86,
            language="python",
            signature="def add(self, a: float, b: float) -> float:",
            symbol_metadata=json.dumps({
                "docstring": "Add two numbers.",
                "parameters": ["self", "a", "b"],
                "return_type": "float",
                "decorators": [],
            }),
        )
        session.add(add_method)

        multiply_method = RepositorySymbol(
            id=uuid4(),
            repository_file_id=file.id,
            symbol_name="multiply",
            symbol_type="method",
            parent_symbol=calculator_class.id,
            start_line=88,
            end_line=99,
            language="python",
            signature="def multiply(self, a: float, b: float) -> float:",
            symbol_metadata=json.dumps({
                "docstring": "Multiply two numbers.",
                "parameters": ["self", "a", "b"],
                "return_type": "float",
                "decorators": [],
            }),
        )
        session.add(multiply_method)

        get_history_method = RepositorySymbol(
            id=uuid4(),
            repository_file_id=file.id,
            symbol_name="get_history",
            symbol_type="method",
            parent_symbol=calculator_class.id,
            start_line=101,
            end_line=107,
            language="python",
            signature="def get_history(self) -> List[tuple]:",
            symbol_metadata=json.dumps({
                "docstring": "Get calculation history.",
                "parameters": ["self"],
                "return_type": "List[tuple]",
                "decorators": [],
            }),
        )
        session.add(get_history_method)

        # Create graph nodes
        repo_node = RepositoryNode(
            id=uuid4(),
            repository_id=repo.id,
            node_type="repository",
            display_name="test-functions",
        )
        session.add(repo_node)

        file_node = RepositoryNode(
            id=uuid4(),
            repository_id=repo.id,
            repository_file_id=file.id,
            node_type="file",
            display_name="test_functions.py",
            language="python",
        )
        session.add(file_node)

        calculate_sum_node = RepositoryNode(
            id=uuid4(),
            repository_id=repo.id,
            repository_file_id=file.id,
            symbol_id=calculate_sum_func.id,
            node_type="symbol",
            display_name="calculate_sum",
            language="python",
        )
        session.add(calculate_sum_node)

        add_values_node = RepositoryNode(
            id=uuid4(),
            repository_id=repo.id,
            repository_file_id=file.id,
            symbol_id=add_values_func.id,
            node_type="symbol",
            display_name="add_values",
            language="python",
        )
        session.add(add_values_node)

        add_method_node = RepositoryNode(
            id=uuid4(),
            repository_id=repo.id,
            repository_file_id=file.id,
            symbol_id=add_method.id,
            node_type="symbol",
            display_name="Calculator.add",
            language="python",
        )
        session.add(add_method_node)

        # Create edges (relationships)
        # Repo contains file
        edge1 = RepositoryEdge(
            id=uuid4(),
            source_node_id=repo_node.id,
            target_node_id=file_node.id,
            relationship_type="CONTAINS",
        )
        session.add(edge1)

        # File contains functions
        edge2 = RepositoryEdge(
            id=uuid4(),
            source_node_id=file_node.id,
            target_node_id=calculate_sum_node.id,
            relationship_type="CONTAINS",
        )
        session.add(edge2)

        edge3 = RepositoryEdge(
            id=uuid4(),
            source_node_id=file_node.id,
            target_node_id=add_values_node.id,
            relationship_type="CONTAINS",
        )
        session.add(edge3)

        # calculate_sum CALLS add_values
        edge4 = RepositoryEdge(
            id=uuid4(),
            source_node_id=calculate_sum_node.id,
            target_node_id=add_values_node.id,
            relationship_type="CALLS",
        )
        session.add(edge4)

        # Calculator.add CALLS add_values
        edge5 = RepositoryEdge(
            id=uuid4(),
            source_node_id=add_method_node.id,
            target_node_id=add_values_node.id,
            relationship_type="CALLS",
        )
        session.add(edge5)

        await session.commit()

        return {
            "repository": repo,
            "file": file,
            "calculate_sum_func": calculate_sum_func,
            "add_values_func": add_values_func,
            "format_result_func": format_result_func,
            "fetch_data_func": fetch_data_func,
            "calculator_class": calculator_class,
            "add_method": add_method,
            "calculate_sum_node": calculate_sum_node,
            "add_values_node": add_values_node,
            "test_file_path": test_file_path,
        }

    except Exception as e:
        await session.rollback()
        # Clean up test file
        if test_file_path.exists():
            test_file_path.unlink()
        raise e


async def test_function_chunking():
    """Test function chunking functionality."""
    print("=" * 70)
    print("FUNCTION-BASED SEMANTIC CHUNKING TEST")
    print("=" * 70)

    # Setup database
    engine, async_session_factory = await setup_test_database()

    async with async_session_factory() as session:
        # Create test data
        print("\n📦 Creating test data...")
        test_data = await create_test_data(session)
        print("✅ Test data created")

        # Initialize chunker
        chunker = FunctionChunker(session)

        # Test 1: Chunk standalone function
        print("\n" + "=" * 70)
        print("TEST 1: Chunk Standalone Function (calculate_sum)")
        print("=" * 70)

        try:
            chunk = await chunker.chunk_function(test_data["calculate_sum_func"].id)

            print("\n✅ Successfully created chunk for calculate_sum")
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
            print(f"  - Parameters: {chunk.metadata.parameters}")
            print(f"  - Return Type: {chunk.metadata.return_type}")
            print(f"  - Is Async: {chunk.metadata.is_async}")
            print(f"  - Calls: {len(chunk.metadata.calls)} functions")
            print(f"  - Node ID: {chunk.metadata.node_id}")

            print(f"\nContext:")
            print(f"  - Imports ({len(chunk.context.imports)}):")
            for imp in chunk.context.imports:
                print(f"    • {imp}")
            print(f"  - Dependencies: {len(chunk.context.dependencies)} symbols")
            print(f"  - Related Chunks: {len(chunk.context.related_chunks)}")
            print(f"  - Docstring: {chunk.context.docstring[:50]}..." if chunk.context.docstring else "  - Docstring: None")

            print(f"\nContent:")
            print("-" * 70)
            print(chunk.content)
            print("-" * 70)

        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()

        # Test 2: Chunk async function
        print("\n" + "=" * 70)
        print("TEST 2: Chunk Async Function (fetch_data)")
        print("=" * 70)

        try:
            chunk = await chunker.chunk_function(test_data["fetch_data_func"].id)

            print("\n✅ Successfully created chunk for fetch_data")
            print(f"\nChunk Details:")
            print(f"  - Type: {chunk.chunk_type}")
            print(f"  - Name: {chunk.chunk_name}")
            print(f"  - Is Async: {chunk.metadata.is_async}")
            print(f"  - Parameters: {chunk.metadata.parameters}")
            print(f"  - Return Type: {chunk.metadata.return_type}")
            print(f"  - Token Count: {chunk.token_count}")

            print(f"\nContent Preview:")
            print("-" * 70)
            print(chunk.content)
            print("-" * 70)

        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()

        # Test 3: Chunk method (with parent class)
        print("\n" + "=" * 70)
        print("TEST 3: Chunk Method with Parent Class (Calculator.add)")
        print("=" * 70)

        try:
            chunk = await chunker.chunk_function(test_data["add_method"].id)

            print("\n✅ Successfully created chunk for Calculator.add")
            print(f"\nChunk Details:")
            print(f"  - Type: {chunk.chunk_type}")
            print(f"  - Name: {chunk.chunk_name}")
            print(f"  - Parent Symbol ID: {chunk.metadata.parent_symbol_id}")
            print(f"  - Parameters: {chunk.metadata.parameters}")
            print(f"  - Calls: {len(chunk.metadata.calls)} functions")

            print(f"\nContext:")
            print(f"  - Parent Definition: {chunk.context.parent_definition}")
            print(f"  - Dependencies: {len(chunk.context.dependencies)}")

            print(f"\nContent:")
            print("-" * 70)
            print(chunk.content)
            print("-" * 70)

        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()

        # Test 4: Chunk all functions in file
        print("\n" + "=" * 70)
        print("TEST 4: Chunk All Functions in File")
        print("=" * 70)

        try:
            chunks = await chunker.chunk_file_functions(test_data["file"].id)

            print(f"\n✅ Successfully chunked {len(chunks)} functions/methods")
            
            functions = [c for c in chunks if c.chunk_type == "function"]
            methods = [c for c in chunks if c.chunk_type == "method"]
            
            print(f"\nBreakdown:")
            print(f"  - Functions: {len(functions)}")
            print(f"  - Methods: {len(methods)}")
            
            print(f"\nFunctions:")
            for chunk in functions:
                print(f"  • {chunk.chunk_name}")
                print(f"    - Params: {chunk.metadata.parameters}")
                print(f"    - Return: {chunk.metadata.return_type}")
                print(f"    - Tokens: {chunk.token_count}")
                print(f"    - Calls: {len(chunk.metadata.calls)}")
            
            print(f"\nMethods:")
            for chunk in methods:
                print(f"  • {chunk.chunk_name}")
                print(f"    - Params: {chunk.metadata.parameters}")
                print(f"    - Tokens: {chunk.token_count}")

        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()

        # Test 5: Chunk all functions in repository
        print("\n" + "=" * 70)
        print("TEST 5: Chunk All Functions in Repository")
        print("=" * 70)

        try:
            chunks = await chunker.chunk_all_functions(
                test_data["repository"].id,
                include_methods=True
            )

            print(f"\n✅ Successfully chunked {len(chunks)} functions/methods")
            
            print(f"\nSummary by Type:")
            type_counts = {}
            for chunk in chunks:
                type_counts[chunk.chunk_type] = type_counts.get(chunk.chunk_type, 0) + 1
            
            for chunk_type, count in type_counts.items():
                print(f"  - {chunk_type}: {count}")
            
            print(f"\nTotal Tokens: {sum(c.token_count for c in chunks)}")

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
    asyncio.run(test_function_chunking())


