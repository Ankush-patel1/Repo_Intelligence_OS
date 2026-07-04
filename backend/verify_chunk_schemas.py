"""Verification script for chunk schemas."""

import json
from uuid import UUID, uuid4

from app.schemas.chunk import (
    ChunkContext,
    ChunkMetadata,
    ChunkResult,
    ChunkRelationship,
)


def test_chunk_context():
    """Test ChunkContext schema."""
    print("\n" + "=" * 60)
    print("Testing ChunkContext Schema")
    print("=" * 60)
    
    # Test with minimal data
    context1 = ChunkContext()
    print(f"✓ Created minimal ChunkContext: {len(context1.imports)} imports")
    
    # Test with full data
    context2 = ChunkContext(
        imports=["from typing import List", "import json"],
        parent_definition="class MyClass:",
        dependencies=[uuid4()],
        related_chunks=[uuid4()],
        docstring="Calculate the total of all items.",
        decorators=["@staticmethod", "@lru_cache"],
        context_before="# Helper functions",
        context_after="# End of helper section",
    )
    print(f"✓ Created full ChunkContext: {len(context2.imports)} imports, {len(context2.decorators)} decorators")
    
    # Test serialization
    json_str = context2.model_dump_json()
    print(f"✓ Serialized to JSON: {len(json_str)} characters")
    
    # Test deserialization
    context3 = ChunkContext.model_validate_json(json_str)
    print(f"✓ Deserialized from JSON: {len(context3.imports)} imports")
    
    return True


def test_chunk_metadata():
    """Test ChunkMetadata schema."""
    print("\n" + "=" * 60)
    print("Testing ChunkMetadata Schema")
    print("=" * 60)
    
    # Test with minimal data
    metadata1 = ChunkMetadata()
    print(f"✓ Created minimal ChunkMetadata")
    
    # Test with function metadata
    metadata2 = ChunkMetadata(
        symbol_type="function",
        signature="def calculate_total(items: List[float]) -> float:",
        parameters=["items"],
        return_type="float",
        start_line=10,
        end_line=20,
        node_id=uuid4(),
        is_async=True,
        complexity_score=3.5,
        tags=["business-logic", "calculations"],
    )
    print(f"✓ Created function ChunkMetadata: {metadata2.symbol_type}, {len(metadata2.parameters)} params")
    
    # Test with class metadata
    metadata3 = ChunkMetadata(
        symbol_type="class",
        signature="class MyClass:",
        start_line=1,
        end_line=100,
        inherits_from=["BaseClass"],
        implements=["IMyInterface"],
        method_count=15,
        is_abstract=False,
    )
    print(f"✓ Created class ChunkMetadata: {metadata3.method_count} methods, inherits from {len(metadata3.inherits_from)}")
    
    # Test with test metadata
    metadata4 = ChunkMetadata(
        symbol_type="test",
        test_framework="pytest",
        tests_symbol_id=uuid4(),
        assertion_count=5,
        start_line=50,
        end_line=65,
    )
    print(f"✓ Created test ChunkMetadata: {metadata4.test_framework}, {metadata4.assertion_count} assertions")
    
    # Test validation (end_line >= start_line)
    try:
        invalid = ChunkMetadata(start_line=100, end_line=50)
        print("✗ Validation failed: should reject end_line < start_line")
        return False
    except ValueError as e:
        print(f"✓ Validation works: {str(e)}")
    
    # Test serialization
    json_str = metadata2.model_dump_json()
    print(f"✓ Serialized to JSON: {len(json_str)} characters")
    
    return True


def test_chunk_result():
    """Test ChunkResult schema."""
    print("\n" + "=" * 60)
    print("Testing ChunkResult Schema")
    print("=" * 60)
    
    repo_id = uuid4()
    file_id = uuid4()
    symbol_id = uuid4()
    
    # Create metadata and context
    metadata = ChunkMetadata(
        symbol_type="function",
        signature="def calculate_total(items):",
        parameters=["items"],
        start_line=10,
        end_line=15,
    )
    
    context = ChunkContext(
        imports=["from typing import List"],
        docstring="Calculate sum of items.",
    )
    
    # Test with full data
    chunk = ChunkResult(
        id=uuid4(),
        repository_id=repo_id,
        repository_file_id=file_id,
        symbol_id=symbol_id,
        chunk_type="function",
        chunk_name="calculate_total",
        language="python",
        content="def calculate_total(items):\n    return sum(items)",
        token_count=25,
        content_hash="a" * 64,
        metadata=metadata,
        context=context,
    )
    
    print(f"✓ Created ChunkResult: {chunk.chunk_type} '{chunk.chunk_name}' ({chunk.language})")
    print(f"  - Token count: {chunk.token_count}")
    print(f"  - Content hash: {chunk.content_hash[:16]}...")
    print(f"  - Lines: {chunk.metadata.start_line}-{chunk.metadata.end_line}")
    
    # Test chunk_type validation
    try:
        invalid = ChunkResult(
            repository_id=repo_id,
            chunk_type="invalid_type",
            chunk_name="test",
            language="python",
            content="test",
            token_count=1,
            content_hash="a" * 64,
            metadata=metadata,
        )
        print("✗ Validation failed: should reject invalid chunk_type")
        return False
    except ValueError as e:
        print(f"✓ Chunk type validation works: prevented invalid type")
    
    # Test content_hash validation
    try:
        invalid = ChunkResult(
            repository_id=repo_id,
            chunk_type="function",
            chunk_name="test",
            language="python",
            content="test",
            token_count=1,
            content_hash="not_a_valid_hash",
            metadata=metadata,
        )
        print("✗ Validation failed: should reject invalid hash")
        return False
    except ValueError as e:
        print(f"✓ Hash validation works: prevented invalid hash format")
    
    # Test serialization
    json_str = chunk.model_dump_json()
    print(f"✓ Serialized to JSON: {len(json_str)} characters")
    
    # Test deserialization
    chunk2 = ChunkResult.model_validate_json(json_str)
    print(f"✓ Deserialized from JSON: '{chunk2.chunk_name}'")
    
    # Test conversion to dict
    chunk_dict = chunk.model_dump()
    print(f"✓ Converted to dict: {len(chunk_dict)} keys")
    
    return True


def test_chunk_relationship():
    """Test ChunkRelationship schema."""
    print("\n" + "=" * 60)
    print("Testing ChunkRelationship Schema")
    print("=" * 60)
    
    source_id = uuid4()
    target_id = uuid4()
    
    # Test with minimal data
    rel1 = ChunkRelationship(
        source_chunk_id=source_id,
        target_chunk_id=target_id,
        relationship_type="calls",
    )
    print(f"✓ Created minimal ChunkRelationship: {rel1.relationship_type}")
    print(f"  - Strength: {rel1.relationship_strength}")
    
    # Test with full data
    rel2 = ChunkRelationship(
        id=uuid4(),
        source_chunk_id=source_id,
        target_chunk_id=target_id,
        relationship_type="calls",
        relationship_strength=0.95,
        metadata={
            "call_count": 5,
            "is_direct": True,
            "call_type": "method_call",
        },
    )
    print(f"✓ Created full ChunkRelationship: {rel2.relationship_type} (strength={rel2.relationship_strength})")
    print(f"  - Metadata keys: {list(rel2.metadata.keys())}")
    
    # Test different relationship types
    relationship_types = ["calls", "imports", "inherits", "tests", "documents", "similar_to"]
    for rel_type in relationship_types:
        rel = ChunkRelationship(
            source_chunk_id=source_id,
            target_chunk_id=target_id,
            relationship_type=rel_type,
        )
        print(f"✓ Created {rel_type} relationship")
    
    # Test relationship_type validation
    try:
        invalid = ChunkRelationship(
            source_chunk_id=source_id,
            target_chunk_id=target_id,
            relationship_type="invalid_type",
        )
        print("✗ Validation failed: should reject invalid relationship_type")
        return False
    except ValueError as e:
        print(f"✓ Relationship type validation works: prevented invalid type")
    
    # Test same chunk validation
    try:
        same_id = uuid4()
        invalid = ChunkRelationship(
            source_chunk_id=same_id,
            target_chunk_id=same_id,
            relationship_type="calls",
        )
        print("✗ Validation failed: should reject same source and target")
        return False
    except ValueError as e:
        print(f"✓ Same chunk validation works: prevented self-reference")
    
    # Test strength bounds
    try:
        invalid = ChunkRelationship(
            source_chunk_id=source_id,
            target_chunk_id=target_id,
            relationship_type="calls",
            relationship_strength=1.5,  # > 1.0
        )
        print("✗ Validation failed: should reject strength > 1.0")
        return False
    except ValueError as e:
        print(f"✓ Strength validation works: prevented out-of-bounds value")
    
    # Test serialization
    json_str = rel2.model_dump_json()
    print(f"✓ Serialized to JSON: {len(json_str)} characters")
    
    return True


def test_schema_integration():
    """Test integration between schemas."""
    print("\n" + "=" * 60)
    print("Testing Schema Integration")
    print("=" * 60)
    
    # Create a complete chunk with all components
    repo_id = uuid4()
    file_id = uuid4()
    symbol_id = uuid4()
    node_id = uuid4()
    
    # Build context
    context = ChunkContext(
        imports=["from typing import List, Dict"],
        parent_definition="class Calculator:",
        docstring="Advanced calculation method",
        decorators=["@classmethod"],
    )
    
    # Build metadata
    metadata = ChunkMetadata(
        symbol_type="method",
        signature="def calculate(cls, data: Dict) -> List:",
        parameters=["cls", "data"],
        return_type="List",
        start_line=42,
        end_line=58,
        parent_symbol_id=uuid4(),
        node_id=node_id,
        access_modifier="public",
        is_static=False,
        complexity_score=5.2,
        tags=["calculation", "data-processing"],
    )
    
    # Build chunk
    chunk = ChunkResult(
        id=uuid4(),
        repository_id=repo_id,
        repository_file_id=file_id,
        symbol_id=symbol_id,
        chunk_type="method",
        chunk_name="Calculator.calculate",
        language="python",
        content="@classmethod\ndef calculate(cls, data: Dict) -> List:\n    # Implementation\n    pass",
        token_count=50,
        content_hash="b" * 64,
        metadata=metadata,
        context=context,
    )
    
    print(f"✓ Created integrated chunk structure:")
    print(f"  - Type: {chunk.chunk_type}")
    print(f"  - Name: {chunk.chunk_name}")
    print(f"  - Language: {chunk.language}")
    print(f"  - Imports: {len(chunk.context.imports)}")
    print(f"  - Parameters: {len(chunk.metadata.parameters)}")
    print(f"  - Tags: {len(chunk.metadata.tags)}")
    
    # Test full serialization/deserialization cycle
    json_str = chunk.model_dump_json(indent=2)
    print(f"✓ Serialized complete structure: {len(json_str)} characters")
    
    chunk_restored = ChunkResult.model_validate_json(json_str)
    print(f"✓ Deserialized complete structure:")
    print(f"  - Type: {chunk_restored.chunk_type}")
    print(f"  - Name: {chunk_restored.chunk_name}")
    print(f"  - Metadata preserved: {chunk_restored.metadata.symbol_type}")
    print(f"  - Context preserved: {len(chunk_restored.context.imports)} imports")
    
    # Verify data integrity
    assert chunk.chunk_name == chunk_restored.chunk_name
    assert chunk.token_count == chunk_restored.token_count
    assert chunk.metadata.symbol_type == chunk_restored.metadata.symbol_type
    assert len(chunk.context.imports) == len(chunk_restored.context.imports)
    print(f"✓ Data integrity verified across serialization")
    
    return True


def test_json_schema_generation():
    """Test JSON schema generation for all models."""
    print("\n" + "=" * 60)
    print("Testing JSON Schema Generation")
    print("=" * 60)
    
    schemas = {
        "ChunkContext": ChunkContext,
        "ChunkMetadata": ChunkMetadata,
        "ChunkResult": ChunkResult,
        "ChunkRelationship": ChunkRelationship,
    }
    
    for name, schema_class in schemas.items():
        schema = schema_class.model_json_schema()
        print(f"✓ Generated JSON schema for {name}:")
        print(f"  - Properties: {len(schema.get('properties', {}))}")
        print(f"  - Required: {len(schema.get('required', []))}")
        
        # Check for examples
        if "examples" in schema or "$defs" in schema:
            print(f"  - Has examples/definitions: Yes")
    
    return True


def main():
    """Run all tests."""
    print("\n" + "=" * 70)
    print(" " * 15 + "CHUNK SCHEMAS VERIFICATION")
    print("=" * 70)
    
    tests = [
        ("ChunkContext", test_chunk_context),
        ("ChunkMetadata", test_chunk_metadata),
        ("ChunkResult", test_chunk_result),
        ("ChunkRelationship", test_chunk_relationship),
        ("Schema Integration", test_schema_integration),
        ("JSON Schema Generation", test_json_schema_generation),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n✗ {test_name} test failed with error: {e}")
            import traceback
            traceback.print_exc()
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    all_passed = all(passed for _, passed in results)
    
    print("\n" + "=" * 70)
    if all_passed:
        print("✅ ALL TESTS PASSED - Schemas are ready for use!")
    else:
        print("❌ SOME TESTS FAILED - Please review errors above")
    print("=" * 70)
    
    return all_passed


if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)

