"""Syntax and import test for pipeline chunking integration.

Tests that the pipeline imports and has the correct structure.
"""

import inspect


def test_imports():
    """Test that all imports work."""
    print("\n=== Test 1: Imports ===")
    
    try:
        from app.services.orchestration.repository_pipeline import RepositoryPipeline
        print("✓ RepositoryPipeline imported")
        
        from app.services.chunking import ClassChunker, ChunkPersister, FunctionChunker
        print("✓ Chunking services imported")
        
        return RepositoryPipeline
    except ImportError as e:
        print(f"✗ Import failed: {e}")
        raise


def test_class_structure(pipeline_class):
    """Test that the pipeline class has the expected structure."""
    print("\n=== Test 2: Class Structure ===")
    
    # Check __init__ parameters
    init_params = inspect.signature(pipeline_class.__init__).parameters
    assert "session" in init_params, "__init__ missing session parameter"
    print("✓ __init__ has session parameter")
    
    # Check methods exist
    expected_methods = [
        "run_full_pipeline",
        "run_index_and_graph",
        "run_graph_only",
        "build_graph",
        "rebuild_graph",
        "get_pipeline_status",
        "generate_chunks",  # NEW
        "regenerate_chunks",  # NEW
    ]
    
    for method_name in expected_methods:
        assert hasattr(pipeline_class, method_name), f"Missing method: {method_name}"
        print(f"✓ Method exists: {method_name}")


def test_method_signatures(pipeline_class):
    """Test that method signatures are correct."""
    print("\n=== Test 3: Method Signatures ===")
    
    # Check run_full_pipeline has skip_chunking parameter
    run_full_sig = inspect.signature(pipeline_class.run_full_pipeline)
    params = run_full_sig.parameters
    
    assert "repository_id" in params, "run_full_pipeline missing repository_id"
    assert "skip_indexing" in params, "run_full_pipeline missing skip_indexing"
    assert "skip_graph" in params, "run_full_pipeline missing skip_graph"
    assert "skip_chunking" in params, "run_full_pipeline missing skip_chunking (NEW)"
    print("✓ run_full_pipeline has skip_chunking parameter")
    
    # Check generate_chunks signature
    gen_chunks_sig = inspect.signature(pipeline_class.generate_chunks)
    params = gen_chunks_sig.parameters
    
    assert "repository_id" in params, "generate_chunks missing repository_id"
    assert "include_classes" in params, "generate_chunks missing include_classes"
    assert "include_functions" in params, "generate_chunks missing include_functions"
    assert "include_methods" in params, "generate_chunks missing include_methods"
    print("✓ generate_chunks has correct parameters")
    
    # Check regenerate_chunks signature
    regen_sig = inspect.signature(pipeline_class.regenerate_chunks)
    params = regen_sig.parameters
    
    assert "repository_id" in params, "regenerate_chunks missing repository_id"
    print("✓ regenerate_chunks has correct parameters")


def test_docstrings(pipeline_class):
    """Test that key methods have updated docstrings."""
    print("\n=== Test 4: Docstrings ===")
    
    # Check run_full_pipeline docstring mentions chunking
    run_full_doc = pipeline_class.run_full_pipeline.__doc__
    assert run_full_doc is not None, "run_full_pipeline missing docstring"
    assert "chunk" in run_full_doc.lower(), "run_full_pipeline docstring doesn't mention chunking"
    print("✓ run_full_pipeline docstring mentions chunking")
    
    # Check generate_chunks has docstring
    gen_doc = pipeline_class.generate_chunks.__doc__
    assert gen_doc is not None, "generate_chunks missing docstring"
    assert "semantic" in gen_doc.lower(), "generate_chunks docstring doesn't mention semantic"
    print("✓ generate_chunks has appropriate docstring")
    
    # Check class docstring updated
    class_doc = pipeline_class.__doc__
    assert class_doc is not None, "Class missing docstring"
    print("✓ Class has docstring")


def main():
    """Run all tests."""
    print("=" * 60)
    print("Testing Pipeline Chunking Integration (Syntax & Structure)")
    print("=" * 60)
    
    try:
        pipeline_class = test_imports()
        test_class_structure(pipeline_class)
        test_method_signatures(pipeline_class)
        test_docstrings(pipeline_class)
        
        print("\n" + "=" * 60)
        print("✓ All Syntax Tests Passed!")
        print("=" * 60)
        print("\nPipeline extended successfully with semantic chunking:")
        print("  • Import → Index → Parse → Knowledge Graph → Semantic Chunks")
        print("\nNew methods:")
        print("  • generate_chunks(repository_id, ...)")
        print("  • regenerate_chunks(repository_id)")
        print("\nUpdated methods:")
        print("  • run_full_pipeline(..., skip_chunking=False)")
        print("  • get_pipeline_status(...) - now includes chunking stats")
        
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
