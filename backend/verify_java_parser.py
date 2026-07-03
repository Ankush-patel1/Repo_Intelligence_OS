"""Verify Java parser integration."""

import sys
from pathlib import Path

# Add parent directory to path if needed
sys.path.insert(0, str(Path(__file__).parent))

# Test 1: Import Java parser directly (avoid circular imports)
try:
    # Import tree-sitter components first
    from tree_sitter import Language, Parser
    from tree_sitter_java import language
    print("✓ Tree-sitter dependencies available")
    
    # Import the Java parser directly without going through package init
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "java_parser",
        Path(__file__).parent / "app" / "services" / "parser" / "java_parser.py"
    )
    java_parser_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(java_parser_module)
    JavaTreeSitterParser = java_parser_module.JavaTreeSitterParser
    
    print("✓ JavaTreeSitterParser imported successfully")
except ImportError as e:
    print(f"✗ Failed to import JavaTreeSitterParser: {e}")
    sys.exit(1)
except Exception as e:
    print(f"✗ Error during import: {e}")
    sys.exit(1)

# Test 2: Instantiate Java parser
try:
    parser = JavaTreeSitterParser()
    print(f"✓ JavaTreeSitterParser instantiated")
    print(f"  - Language: {parser.language}")
    print(f"  - Extensions: {parser.supported_extensions}")
except Exception as e:
    print(f"✗ Failed to instantiate JavaTreeSitterParser: {e}")
    sys.exit(1)

# Test 3: Create sample Java file and parse it
sample_java = """
package com.example.app;

import java.util.List;
import java.util.ArrayList;

/**
 * Sample class for testing
 */
@Entity
public class User {
    private Long id;
    private String name;
    
    public User() {
    }
    
    public User(Long id, String name) {
        this.id = id;
        this.name = name;
    }
    
    public Long getId() {
        return id;
    }
    
    public void setId(Long id) {
        this.id = id;
    }
    
    public String getName() {
        return name;
    }
    
    public void setName(String name) {
        this.name = name;
    }
}

@Repository
public interface UserRepository {
    User findById(Long id);
    List<User> findAll();
}

public enum UserStatus {
    ACTIVE,
    INACTIVE,
    SUSPENDED
}
"""

# Create temporary test file
test_file = Path("test_sample.java")
try:
    test_file.write_text(sample_java)
    print("✓ Created test Java file")
    
    # Parse the file
    result = parser.parse(test_file)
    
    if result.success:
        print("✓ Java file parsed successfully")
        print(f"  - Parse tree type: {result.parse_tree.get('type')}")
        print(f"  - Symbols extracted: {len(result.symbols)}")
        
        # Count symbol types
        symbol_types = {}
        for symbol in result.symbols:
            sym_type = symbol.get('type')
            symbol_types[sym_type] = symbol_types.get(sym_type, 0) + 1
        
        print(f"  - Symbol breakdown:")
        for sym_type, count in sorted(symbol_types.items()):
            print(f"    - {sym_type}: {count}")
        
        # Show some example symbols
        print(f"\n  Sample symbols:")
        for symbol in result.symbols[:5]:
            name = symbol.get('name', 'N/A')
            sym_type = symbol.get('type', 'N/A')
            line = symbol.get('line', 'N/A')
            print(f"    - {sym_type}: {name} (line {line})")
    else:
        print(f"✗ Parse failed: {result.error_message}")
        sys.exit(1)
        
finally:
    # Cleanup
    if test_file.exists():
        test_file.unlink()
        print("\n✓ Cleaned up test file")

print("\n" + "="*60)
print("✓ All Java parser integration tests passed!")
print("="*60)
