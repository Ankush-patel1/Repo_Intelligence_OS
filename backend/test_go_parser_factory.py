"""Test Go parser factory registration."""

from pathlib import Path
import sys

print("Testing Go Parser Factory Registration")
print("=" * 60)

try:
    # Check tree-sitter-go is available
    from tree_sitter import Language, Parser
    from tree_sitter_go import language
    print("✓ tree-sitter-go dependency available")
    
    # Check go_parser.py exists
    go_parser_file = Path(__file__).parent / "app" / "services" / "parser" / "go_parser.py"
    if go_parser_file.exists():
        print(f"✓ go_parser.py exists: {go_parser_file}")
    else:
        print(f"✗ go_parser.py not found: {go_parser_file}")
        sys.exit(1)
    
    # Check parser_factory.py has the import
    factory_file = Path(__file__).parent / "app" / "services" / "parser" / "parser_factory.py"
    if factory_file.exists():
        content = factory_file.read_text()
        
        checks = [
            ("GoTreeSitterParser import", "from app.services.parser.go_parser import GoTreeSitterParser"),
            ("GoParser alias", "GoParser = GoTreeSitterParser"),
            ("Go in parsers dict", '"Go": GoParser()'),
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
    
    # Check requirements.txt has tree-sitter-go
    req_file = Path(__file__).parent / "requirements" / "base.txt"
    if req_file.exists():
        content = req_file.read_text()
        if "tree-sitter-go" in content:
            print("✓ tree-sitter-go in requirements/base.txt")
        else:
            print("✗ tree-sitter-go not in requirements")
            sys.exit(1)
    else:
        print(f"✗ requirements/base.txt not found: {req_file}")
        sys.exit(1)
    
    # Verify Go parser structure
    go_parser_content = go_parser_file.read_text()
    
    structure_checks = [
        ("GoTreeSitterParser class", "class GoTreeSitterParser"),
        ("language property", "def language(self)"),
        ("supported_extensions property", "def supported_extensions(self)"),
        ("parse method", "def parse(self, file_path: Path)"),
        ("extract package", "def _extract_package"),
        ("extract imports", "def _extract_imports"),
        ("extract structs", "def _extract_struct_fields"),
        ("extract interfaces", "def _extract_interface_methods"),
        ("extract functions", "def _extract_functions"),
        ("extract methods", "def _extract_methods"),
        ("extract constants", "def _extract_constants"),
        ("extract variables", "def _extract_variables"),
        ("extract type declarations", "def _extract_type_declarations"),
    ]
    
    print("\n  Go Parser structure verification:")
    all_passed = True
    for check_name, check_string in structure_checks:
        if check_string in go_parser_content:
            print(f"    ✓ {check_name}")
        else:
            print(f"    ✗ {check_name}")
            all_passed = False
    
    if not all_passed:
        sys.exit(1)
    
    print("\n" + "=" * 60)
    print("✓ All Go parser factory integration checks passed!")
    print("=" * 60)
    print("\nNOTE: Full integration test requires:")
    print("  docker compose build")
    print("  docker compose up")
    print("  Then import a Go repository to verify end-to-end parsing")
    
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
