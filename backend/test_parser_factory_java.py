"""Test ParserFactory Java registration (isolated from circular imports)."""

from pathlib import Path
import sys

# Test by directly importing what we need
print("Testing ParserFactory Java Registration")
print("=" * 60)

try:
    # Import parser factory components directly
    from tree_sitter import Language, Parser
    from tree_sitter_java import language
    print("✓ Tree-sitter dependencies available")
    
    # Check that JavaTreeSitterParser exists
    java_parser_file = Path(__file__).parent / "app" / "services" / "parser" / "java_parser.py"
    if java_parser_file.exists():
        print(f"✓ JavaTreeSitterParser module exists: {java_parser_file}")
    else:
        print(f"✗ JavaTreeSitterParser module not found: {java_parser_file}")
        sys.exit(1)
    
    # Check parser_factory.py has the import
    factory_file = Path(__file__).parent / "app" / "services" / "parser" / "parser_factory.py"
    if factory_file.exists():
        content = factory_file.read_text()
        if "from app.services.parser.java_parser import JavaTreeSitterParser" in content:
            print("✓ ParserFactory imports JavaTreeSitterParser")
        else:
            print("✗ ParserFactory does not import JavaTreeSitterParser")
            sys.exit(1)
        
        if "JavaParser = JavaTreeSitterParser" in content:
            print("✓ JavaParser alias registered")
        else:
            print("✗ JavaParser alias not found")
            sys.exit(1)
            
        # Check it's in the parsers dict
        if '"Java": JavaParser()' in content:
            print("✓ Java parser registered in factory")
        else:
            print("✗ Java parser not registered in factory")
            sys.exit(1)
    else:
        print(f"✗ ParserFactory not found: {factory_file}")
        sys.exit(1)
    
    # Check requirements.txt has tree-sitter-java
    req_file = Path(__file__).parent / "requirements" / "base.txt"
    if req_file.exists():
        content = req_file.read_text()
        if "tree-sitter-java" in content:
            print("✓ tree-sitter-java in requirements/base.txt")
        else:
            print("✗ tree-sitter-java not in requirements")
            sys.exit(1)
    else:
        print(f"✗ Requirements file not found: {req_file}")
        sys.exit(1)
    
    print("\n" + "=" * 60)
    print("✓ All ParserFactory Java integration checks passed!")
    print("=" * 60)
    print("\nNOTE: Full integration test requires running:")
    print("  docker compose build")
    print("  docker compose up")
    print("  Then import a Java repository to verify end-to-end parsing")
    
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
