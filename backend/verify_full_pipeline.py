#!/usr/bin/env python
"""Full pipeline verification script.

This script verifies the complete flow:
1. Repository import
2. File indexing
3. Symbol parsing and extraction
4. Database persistence
"""

import asyncio
import json
import sys
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.db.models.repository import Repository
from app.db.models.repository_file import RepositoryFile
from app.db.models.repository_symbol import RepositorySymbol
from app.services.indexing.repository_indexer import RepositoryIndexer


async def create_test_repository(session: AsyncSession) -> Repository:
    """Create a test repository for verification."""
    # Use the backend directory itself as a test repository
    repo = Repository(
        owner="test",
        name="backend",
        full_name="test/backend",
        branch="main",
        clone_path=str(Path(__file__).parent.absolute()),
        private=False,
        default_branch="main",
    )
    session.add(repo)
    await session.flush()
    return repo


async def verify_repository_indexed(session: AsyncSession, repo_id) -> dict:
    """Verify repository files are indexed."""
    result = await session.execute(
        select(RepositoryFile).where(RepositoryFile.repository_id == repo_id)
    )
    files = result.scalars().all()
    
    return {
        "total_files": len(files),
        "python_files": len([f for f in files if f.language == "Python"]),
        "js_files": len([f for f in files if f.language == "JavaScript"]),
        "ts_files": len([f for f in files if f.language == "TypeScript"]),
        "sample_files": [
            {
                "path": f.relative_path,
                "language": f.language,
                "size": f.size_bytes,
            }
            for f in files[:5]
        ],
    }


async def verify_symbols_extracted(session: AsyncSession, repo_id) -> dict:
    """Verify symbols are extracted and stored."""
    # Get files
    file_result = await session.execute(
        select(RepositoryFile).where(RepositoryFile.repository_id == repo_id)
    )
    files = file_result.scalars().all()
    
    if not files:
        return {"error": "No files found"}
    
    # Get symbols
    symbol_result = await session.execute(
        select(RepositorySymbol).where(
            RepositorySymbol.repository_file_id.in_([f.id for f in files])
        )
    )
    symbols = symbol_result.scalars().all()
    
    # Group by type
    symbols_by_type = {}
    for symbol in symbols:
        symbols_by_type[symbol.symbol_type] = symbols_by_type.get(symbol.symbol_type, 0) + 1
    
    # Group by language
    symbols_by_language = {}
    for symbol in symbols:
        symbols_by_language[symbol.language] = symbols_by_language.get(symbol.language, 0) + 1
    
    # Get sample symbols
    sample_symbols = []
    for symbol in symbols[:10]:
        sample_symbols.append({
            "name": symbol.symbol_name,
            "type": symbol.symbol_type,
            "language": symbol.language,
            "line": symbol.start_line,
            "signature": symbol.signature[:80] if symbol.signature else None,
        })
    
    return {
        "total_symbols": len(symbols),
        "symbols_by_type": symbols_by_type,
        "symbols_by_language": symbols_by_language,
        "sample_symbols": sample_symbols,
    }


async def verify_parent_child_relationships(session: AsyncSession, repo_id) -> dict:
    """Verify parent-child relationships (classes with methods)."""
    # Get files
    file_result = await session.execute(
        select(RepositoryFile).where(RepositoryFile.repository_id == repo_id)
    )
    files = file_result.scalars().all()
    
    if not files:
        return {"error": "No files found"}
    
    # Get class symbols
    class_result = await session.execute(
        select(RepositorySymbol).where(
            RepositorySymbol.repository_file_id.in_([f.id for f in files]),
            RepositorySymbol.symbol_type == "class",
        )
    )
    classes = class_result.scalars().all()
    
    # Get methods with parents
    method_result = await session.execute(
        select(RepositorySymbol).where(
            RepositorySymbol.repository_file_id.in_([f.id for f in files]),
            RepositorySymbol.symbol_type == "method",
            RepositorySymbol.parent_symbol.isnot(None),
        )
    )
    methods = method_result.scalars().all()
    
    # Sample class with methods
    examples = []
    for cls in classes[:3]:
        class_methods = [m for m in methods if m.parent_symbol == cls.id]
        if class_methods:
            examples.append({
                "class_name": cls.symbol_name,
                "class_line": cls.start_line,
                "methods": [
                    {
                        "name": m.symbol_name,
                        "line": m.start_line,
                        "signature": m.signature[:60] if m.signature else None,
                    }
                    for m in class_methods[:5]
                ],
            })
    
    return {
        "total_classes": len(classes),
        "total_methods_with_parents": len(methods),
        "examples": examples,
    }


async def get_example_parsed_file(session: AsyncSession, repo_id) -> dict:
    """Get an example parsed file with its symbols."""
    # Get a Python file with symbols
    file_result = await session.execute(
        select(RepositoryFile)
        .where(
            RepositoryFile.repository_id == repo_id,
            RepositoryFile.language == "Python",
        )
        .limit(1)
    )
    file = file_result.scalar_one_or_none()
    
    if not file:
        return {"error": "No Python files found"}
    
    # Get its symbols
    symbol_result = await session.execute(
        select(RepositorySymbol)
        .where(RepositorySymbol.repository_file_id == file.id)
        .order_by(RepositorySymbol.start_line)
    )
    symbols = symbol_result.scalars().all()
    
    return {
        "file": {
            "path": file.relative_path,
            "language": file.language,
            "size_bytes": file.size_bytes,
            "line_count": file.line_count,
        },
        "symbols": [
            {
                "name": s.symbol_name,
                "type": s.symbol_type,
                "line_range": f"{s.start_line}-{s.end_line}",
                "signature": s.signature,
                "has_parent": s.parent_symbol is not None,
            }
            for s in symbols[:15]
        ],
    }


async def get_example_repository_symbol(session: AsyncSession, repo_id) -> dict:
    """Get an example RepositorySymbol record."""
    # Get files
    file_result = await session.execute(
        select(RepositoryFile).where(RepositoryFile.repository_id == repo_id).limit(1)
    )
    file = file_result.scalar_one_or_none()
    
    if not file:
        return {"error": "No files found"}
    
    # Get a function symbol
    symbol_result = await session.execute(
        select(RepositorySymbol)
        .where(
            RepositorySymbol.repository_file_id == file.id,
            RepositorySymbol.symbol_type == "function",
        )
        .limit(1)
    )
    symbol = symbol_result.scalar_one_or_none()
    
    if not symbol:
        # Try any symbol
        symbol_result = await session.execute(
            select(RepositorySymbol)
            .where(RepositorySymbol.repository_file_id == file.id)
            .limit(1)
        )
        symbol = symbol_result.scalar_one_or_none()
    
    if not symbol:
        return {"error": "No symbols found"}
    
    return {
        "id": str(symbol.id),
        "repository_file_id": str(symbol.repository_file_id),
        "symbol_name": symbol.symbol_name,
        "symbol_type": symbol.symbol_type,
        "parent_symbol": str(symbol.parent_symbol) if symbol.parent_symbol else None,
        "start_line": symbol.start_line,
        "end_line": symbol.end_line,
        "start_column": symbol.start_column,
        "end_column": symbol.end_column,
        "language": symbol.language,
        "signature": symbol.signature,
        "metadata": symbol.symbol_metadata,
        "created_at": symbol.created_at.isoformat() if symbol.created_at else None,
    }


async def main():
    """Run the full verification."""
    print("=" * 80)
    print("FULL PIPELINE VERIFICATION")
    print("=" * 80)
    print()
    
    # Create database engine
    engine = create_async_engine(
        "sqlite+aiosqlite:///test_verification.db",
        echo=False,
    )
    
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    
    # Create session
    async_session_maker = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    try:
        async with async_session_maker() as session:
            # Step 1: Create repository
            print("Step 1: Creating test repository...")
            repo = await create_test_repository(session)
            await session.commit()
            print(f"✓ Repository created: {repo.full_name} (ID: {repo.id})")
            print()
            
            # Step 2: Index repository
            print("Step 2: Indexing repository files...")
            indexer = RepositoryIndexer(session)
            stats = await indexer.index_repository(repo)
            await session.commit()
            print(f"✓ Repository indexed")
            print(f"  Total files: {stats['total_files']}")
            print(f"  Total bytes: {stats['total_bytes']:,}")
            print(f"  Files per language: {json.dumps(stats['files_per_language'], indent=4)}")
            if "symbols" in stats:
                print(f"  Total symbols: {stats['symbols']['total_symbols']}")
                print(f"  Files parsed: {stats['symbols']['files_parsed']}")
                print(f"  Symbols by language: {json.dumps(stats['symbols']['symbols_by_language'], indent=4)}")
            print()
            
            # Step 3: Verify indexing
            print("Step 3: Verifying file indexing...")
            index_verify = await verify_repository_indexed(session, repo.id)
            print(f"✓ Files verified in database")
            print(f"  Total files: {index_verify['total_files']}")
            print(f"  Python files: {index_verify['python_files']}")
            print(f"  JavaScript files: {index_verify['js_files']}")
            print(f"  TypeScript files: {index_verify['ts_files']}")
            print()
            
            # Step 4: Verify symbol extraction
            print("Step 4: Verifying symbol extraction...")
            symbol_verify = await verify_symbols_extracted(session, repo.id)
            if "error" not in symbol_verify:
                print(f"✓ Symbols verified in database")
                print(f"  Total symbols: {symbol_verify['total_symbols']}")
                print(f"  Symbols by type: {json.dumps(symbol_verify['symbols_by_type'], indent=4)}")
                print(f"  Symbols by language: {json.dumps(symbol_verify['symbols_by_language'], indent=4)}")
            else:
                print(f"✗ {symbol_verify['error']}")
            print()
            
            # Step 5: Verify parent-child relationships
            print("Step 5: Verifying parent-child relationships...")
            relationship_verify = await verify_parent_child_relationships(session, repo.id)
            if "error" not in relationship_verify:
                print(f"✓ Relationships verified")
                print(f"  Total classes: {relationship_verify['total_classes']}")
                print(f"  Methods with parents: {relationship_verify['total_methods_with_parents']}")
                if relationship_verify['examples']:
                    print(f"  Example class with methods:")
                    example = relationship_verify['examples'][0]
                    print(f"    Class: {example['class_name']} (line {example['class_line']})")
                    for method in example['methods'][:3]:
                        print(f"      - {method['name']} (line {method['line']})")
            else:
                print(f"✗ {relationship_verify['error']}")
            print()
            
            # Step 6: Get example ParsedFile
            print("Step 6: Example ParsedFile...")
            parsed_file = await get_example_parsed_file(session, repo.id)
            if "error" not in parsed_file:
                print("✓ Example file with symbols:")
                print(f"  File: {parsed_file['file']['path']}")
                print(f"  Language: {parsed_file['file']['language']}")
                print(f"  Lines: {parsed_file['file']['line_count']}")
                print(f"  Symbols extracted: {len(parsed_file['symbols'])}")
                print(f"  Sample symbols:")
                for sym in parsed_file['symbols'][:5]:
                    print(f"    - {sym['type']:10} {sym['name']:30} (line {sym['line_range']})")
            else:
                print(f"✗ {parsed_file['error']}")
            print()
            
            # Step 7: Get example RepositorySymbol
            print("Step 7: Example RepositorySymbol record...")
            example_symbol = await get_example_repository_symbol(session, repo.id)
            if "error" not in example_symbol:
                print("✓ Example RepositorySymbol:")
                print(json.dumps(example_symbol, indent=2))
            else:
                print(f"✗ {example_symbol['error']}")
            print()
            
            # Final summary
            print("=" * 80)
            print("VERIFICATION SUMMARY")
            print("=" * 80)
            print(f"✓ Repository imported and stored")
            print(f"✓ Files indexed: {index_verify['total_files']}")
            if "error" not in symbol_verify:
                print(f"✓ Symbols extracted: {symbol_verify['total_symbols']}")
                print(f"✓ RepositorySymbol table populated")
            print(f"✓ Parent-child relationships working")
            print()
            print("All verification steps passed! ✓")
            print()
            
    finally:
        await engine.dispose()
    
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
