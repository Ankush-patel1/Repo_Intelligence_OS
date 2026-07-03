"""Test Rust parser factory registration."""

from pathlib import Path
import sys

print("Testing Rust Parser Factory Registration")
print("=" * 60)

try:
    # Check tree-sitter-rust is available
    from tree_sitter import Language, Parser
    from tree_sitter_rust import language
    print("✓ tree-sitter-rust dependency available")
    
    # Check rust_parser.py exists
    rust_parser_file = Path(__file__).parent / "app" / "services" / "parser" / "rust_parser.py"
    if rust_parser_file.exists():
        print(f"✓ rust_parser.py exists: {rust_parser_file}")
    else:
        print(f"✗ rust_parser.py not found: {rust_parser_file}")
        sys.exit(1)
    
    # Check parser_factory.py has the import
    factory_file = Path(__file__).parent / "app" / "services" / "parser" / "parser_factory.py"
    if factory_file.exists():
        content = factory_file.read_text()
        
        checks = [
            ("RustTreeSitterParser import", "from app.services.parser.rust_parser import RustTreeSitterParser"),
            ("RustParser alias", "RustParser = RustTreeSitterParser"),
            ("Rust in parsers dict", '"Rust": RustParser()'),
        ]
        
        all_passed = True
        for check_name, check_string in checks:
            if check_string in content:
                print(f"✓ {check_name} found")
            else:
                print(f"✗ {check_name} not found")
                all_passed = False
        
        if not all_passed:
            sys.exit(1)
    else:
        print(f"✗ parser_factory.py not found: {factory_file}")
        sys.exit(1)
    
    # Check requirements.txt has tree-sitter-rust
    req_file = Path(__file__).parent / "requirements" / "base.txt"
    if req_file.exists():
        content = req_file.read_text()
        if "tree-sitter-rust" in content:
            print("✓ tree-sitter-rust in requirements/base.txt")
        else:
            print("✗ tree-sitter-rust not in requirements")
            sys.exit(1)
    else:
        print(f"✗ requirements/base.txt not found: {req_file}")
        sys.exit(1)
    
    # Verify Rust parser structure
    rust_parser_content = rust_parser_file.read_text()
    
    structure_checks = [
        ("RustTreeSitterParser class", "class RustTreeSitterParser"),
        ("language property", "def language(self)"),
        ("supported_extensions property", "def supported_extensions(self)"),
        ("parse method", "def parse(self, file_path: Path)"),
        ("extract modules", "def _extract_modules"),
        ("extract use statements", "def _extract_use_statements"),
        ("extract structs", "def _extract_structs"),
        ("extract enums", "def _extract_enums"),
        ("extract traits", "def _extract_traits"),
        ("extract impl blocks", "def _extract_impl_blocks"),
        ("extract functions", "def _extract_functions"),
        ("extract constants", "def _extract_constants"),
        ("extract macros", "def _extract_macros"),
    ]
    
    print("\n  Rust Parser structure verification:")
    all_passed = True
    for check_name, check_string in structure_checks:
        if check_string in rust_parser_content:
            print(f"    ✓ {check_name}")
        else:
            print(f"    ✗ {check_name}")
            all_passed = False
    
    if not all_passed:
        sys.exit(1)
    
    print("\n" + "=" * 60)
    print("✓ All Rust parser factory integration checks passed!")
    print("=" * 60)
    print("\nNOTE: Full integration test requires:")
    print("  docker compose build")
    print("  docker compose up")
    print("  Then import a Rust repository to verify end-to-end parsing")
    
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
