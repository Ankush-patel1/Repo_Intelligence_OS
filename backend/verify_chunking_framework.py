"""Verification script for chunking framework architecture.

Verifies that all framework components are properly structured,
interfaces are defined, and imports work correctly.
"""

import sys
from abc import ABC
from inspect import isabstract, isclass, signature


def test_imports():
    """Test that all framework components can be imported."""
    print("=" * 70)
    print("TEST 1: Import Verification")
    print("=" * 70)
    
    try:
        from app.services.chunking import (
            ChunkBuilder,
            ChunkInterface,
            ChunkStrategy,
            ChunkManager,
            SymbolLevelStrategy,
            LogicalUnitStrategy,
            FileLevelStrategy,
            ModuleLevelStrategy,
        )
        print("✅ All components imported successfully")
        return True, {
            "ChunkBuilder": ChunkBuilder,
            "ChunkInterface": ChunkInterface,
            "ChunkStrategy": ChunkStrategy,
            "ChunkManager": ChunkManager,
            "SymbolLevelStrategy": SymbolLevelStrategy,
            "LogicalUnitStrategy": LogicalUnitStrategy,
            "FileLevelStrategy": FileLevelStrategy,
            "ModuleLevelStrategy": ModuleLevelStrategy,
        }
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        return False, {}


def test_interfaces(components):
    """Test that abstract interfaces are properly defined."""
    print("\n" + "=" * 70)
    print("TEST 2: Interface Definition Verification")
    print("=" * 70)
    
    ChunkInterface = components.get("ChunkInterface")
    ChunkStrategy = components.get("ChunkStrategy")
    
    if not ChunkInterface or not ChunkStrategy:
        print("❌ Cannot verify interfaces - components not loaded")
        return False
    
    # Check ChunkInterface
    print("\n--- ChunkInterface ---")
    if not isabstract(ChunkInterface):
        print("❌ ChunkInterface is not abstract")
        return False
    print("✅ ChunkInterface is abstract")
    
    expected_methods = ["generate_chunks", "validate_chunk", "estimate_token_count"]
    for method_name in expected_methods:
        if not hasattr(ChunkInterface, method_name):
            print(f"❌ Missing method: {method_name}")
            return False
        print(f"✅ Method exists: {method_name}")
    
    # Check ChunkStrategy
    print("\n--- ChunkStrategy ---")
    if not isabstract(ChunkStrategy):
        print("❌ ChunkStrategy is not abstract")
        return False
    print("✅ ChunkStrategy is abstract")
    
    expected_methods = [
        "should_apply",
        "calculate_boundaries",
        "build_context",
        "extract_metadata",
        "get_priority",
    ]
    for method_name in expected_methods:
        if not hasattr(ChunkStrategy, method_name):
            print(f"❌ Missing method: {method_name}")
            return False
        print(f"✅ Method exists: {method_name}")
    
    return True


def test_chunk_builder(components):
    """Test ChunkBuilder class structure."""
    print("\n" + "=" * 70)
    print("TEST 3: ChunkBuilder Structure Verification")
    print("=" * 70)
    
    ChunkBuilder = components.get("ChunkBuilder")
    if not ChunkBuilder:
        print("❌ ChunkBuilder not loaded")
        return False
    
    if isabstract(ChunkBuilder):
        print("❌ ChunkBuilder should be concrete, not abstract")
        return False
    print("✅ ChunkBuilder is concrete")
    
    expected_methods = [
        "build_chunk",
        "extract_content",
        "build_context",
        "build_metadata",
        "calculate_token_count",
        "calculate_content_hash",
        "merge_chunks",
        "split_oversized_chunk",
    ]
    
    for method_name in expected_methods:
        if not hasattr(ChunkBuilder, method_name):
            print(f"❌ Missing method: {method_name}")
            return False
        print(f"✅ Method exists: {method_name}")
    
    return True


def test_strategies(components):
    """Test concrete strategy implementations."""
    print("\n" + "=" * 70)
    print("TEST 4: Strategy Implementation Verification")
    print("=" * 70)
    
    ChunkStrategy = components.get("ChunkStrategy")
    strategies = [
        ("SymbolLevelStrategy", components.get("SymbolLevelStrategy")),
        ("LogicalUnitStrategy", components.get("LogicalUnitStrategy")),
        ("FileLevelStrategy", components.get("FileLevelStrategy")),
        ("ModuleLevelStrategy", components.get("ModuleLevelStrategy")),
    ]
    
    if not ChunkStrategy:
        print("❌ ChunkStrategy base class not loaded")
        return False
    
    for name, strategy_cls in strategies:
        print(f"\n--- {name} ---")
        
        if not strategy_cls:
            print(f"❌ {name} not loaded")
            return False
        
        if not issubclass(strategy_cls, ChunkStrategy):
            print(f"❌ {name} does not inherit from ChunkStrategy")
            return False
        print(f"✅ {name} inherits from ChunkStrategy")
        
        if isabstract(strategy_cls):
            print(f"❌ {name} should be concrete")
            return False
        print(f"✅ {name} is concrete")
        
        # Check required methods exist
        required_methods = [
            "should_apply",
            "calculate_boundaries",
            "build_context",
            "extract_metadata",
            "get_priority",
        ]
        for method_name in required_methods:
            if not hasattr(strategy_cls, method_name):
                print(f"❌ Missing method: {method_name}")
                return False
        print(f"✅ All required methods present")
    
    return True


def test_chunk_manager(components):
    """Test ChunkManager class structure."""
    print("\n" + "=" * 70)
    print("TEST 5: ChunkManager Structure Verification")
    print("=" * 70)
    
    ChunkManager = components.get("ChunkManager")
    if not ChunkManager:
        print("❌ ChunkManager not loaded")
        return False
    
    if isabstract(ChunkManager):
        print("❌ ChunkManager should be concrete")
        return False
    print("✅ ChunkManager is concrete")
    
    expected_public_methods = [
        "chunk_repository",
        "chunk_file",
        "chunk_symbols",
        "rechunk_repository",
        "delete_repository_chunks",
        "delete_file_chunks",
        "get_chunking_statistics",
        "validate_chunks",
    ]
    
    print("\n--- Public Methods ---")
    for method_name in expected_public_methods:
        if not hasattr(ChunkManager, method_name):
            print(f"❌ Missing method: {method_name}")
            return False
        print(f"✅ Method exists: {method_name}")
    
    expected_private_methods = [
        "_process_file",
        "_select_strategy_for_file",
        "_fetch_file_data",
        "_persist_chunks",
        "_build_chunk_relationships",
        "_detect_changed_files",
        "_cleanup_orphaned_chunks",
    ]
    
    print("\n--- Private Methods ---")
    for method_name in expected_private_methods:
        if not hasattr(ChunkManager, method_name):
            print(f"❌ Missing method: {method_name}")
            return False
        print(f"✅ Method exists: {method_name}")
    
    return True


def test_schema_integration():
    """Test integration with chunk schemas."""
    print("\n" + "=" * 70)
    print("TEST 6: Schema Integration Verification")
    print("=" * 70)
    
    try:
        from app.schemas.chunk import (
            ChunkContext,
            ChunkMetadata,
            ChunkResult,
            ChunkRelationship,
        )
        print("✅ All chunk schemas imported successfully")
        
        # Verify schemas are Pydantic models
        from pydantic import BaseModel
        
        schemas = [
            ("ChunkContext", ChunkContext),
            ("ChunkMetadata", ChunkMetadata),
            ("ChunkResult", ChunkResult),
            ("ChunkRelationship", ChunkRelationship),
        ]
        
        for name, schema_cls in schemas:
            if not issubclass(schema_cls, BaseModel):
                print(f"❌ {name} is not a Pydantic BaseModel")
                return False
            print(f"✅ {name} is a valid Pydantic model")
        
        return True
        
    except ImportError as e:
        print(f"❌ Schema import failed: {e}")
        return False


def test_enum_definitions():
    """Test enum definitions."""
    print("\n" + "=" * 70)
    print("TEST 7: Enum Definition Verification")
    print("=" * 70)
    
    try:
        from app.services.chunking.chunk_interface import ChunkStrategyType
        from enum import Enum
        
        if not issubclass(ChunkStrategyType, Enum):
            print("❌ ChunkStrategyType is not an Enum")
            return False
        print("✅ ChunkStrategyType is an Enum")
        
        expected_values = [
            "SYMBOL_LEVEL",
            "LOGICAL_UNIT",
            "FILE_LEVEL",
            "MODULE_LEVEL",
            "AUTO",
        ]
        
        for value in expected_values:
            if not hasattr(ChunkStrategyType, value):
                print(f"❌ Missing enum value: {value}")
                return False
            print(f"✅ Enum value exists: {value}")
        
        return True
        
    except ImportError as e:
        print(f"❌ Enum import failed: {e}")
        return False


def test_method_signatures():
    """Test that key methods have proper signatures."""
    print("\n" + "=" * 70)
    print("TEST 8: Method Signature Verification")
    print("=" * 70)
    
    try:
        from app.services.chunking import ChunkBuilder, ChunkManager
        
        # Check ChunkBuilder.build_chunk signature
        sig = signature(ChunkBuilder.build_chunk)
        params = list(sig.parameters.keys())
        expected_params = [
            "self",
            "repository_id",
            "repository_file_id",
            "symbol_id",
            "chunk_type",
            "chunk_name",
            "language",
            "content",
            "metadata",
            "context",
        ]
        
        print("\n--- ChunkBuilder.build_chunk ---")
        for param in expected_params:
            if param not in params:
                print(f"❌ Missing parameter: {param}")
                return False
        print(f"✅ All expected parameters present: {len(expected_params)} params")
        
        # Check ChunkManager.chunk_repository signature
        sig = signature(ChunkManager.chunk_repository)
        params = list(sig.parameters.keys())
        expected_params = [
            "self",
            "repository_id",
            "strategy",
            "force_rebuild",
            "file_filters",
        ]
        
        print("\n--- ChunkManager.chunk_repository ---")
        for param in expected_params:
            if param not in params:
                print(f"❌ Missing parameter: {param}")
                return False
        print(f"✅ All expected parameters present: {len(expected_params)} params")
        
        return True
        
    except Exception as e:
        print(f"❌ Signature verification failed: {e}")
        return False


def main():
    """Run all verification tests."""
    print("\n" + "=" * 70)
    print("CHUNKING FRAMEWORK ARCHITECTURE VERIFICATION")
    print("=" * 70)
    
    results = []
    
    # Test 1: Imports
    success, components = test_imports()
    results.append(("Import Verification", success))
    
    if not success:
        print("\n❌ Cannot continue - import failed")
        return False
    
    # Test 2: Interfaces
    success = test_interfaces(components)
    results.append(("Interface Definition", success))
    
    # Test 3: ChunkBuilder
    success = test_chunk_builder(components)
    results.append(("ChunkBuilder Structure", success))
    
    # Test 4: Strategies
    success = test_strategies(components)
    results.append(("Strategy Implementations", success))
    
    # Test 5: ChunkManager
    success = test_chunk_manager(components)
    results.append(("ChunkManager Structure", success))
    
    # Test 6: Schema Integration
    success = test_schema_integration()
    results.append(("Schema Integration", success))
    
    # Test 7: Enum Definitions
    success = test_enum_definitions()
    results.append(("Enum Definitions", success))
    
    # Test 8: Method Signatures
    success = test_method_signatures()
    results.append(("Method Signatures", success))
    
    # Summary
    print("\n" + "=" * 70)
    print("VERIFICATION SUMMARY")
    print("=" * 70)
    
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - {test_name}")
    
    all_passed = all(result[1] for result in results)
    
    print("\n" + "=" * 70)
    if all_passed:
        print("✅ ALL TESTS PASSED - Framework architecture is valid")
        print("=" * 70)
        return True
    else:
        print("❌ SOME TESTS FAILED - Please review errors above")
        print("=" * 70)
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)


