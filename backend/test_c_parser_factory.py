"""Test C parser factory registration."""

from pathlib import Path
import sys

print("Testing C Parser Factory Registration")
print("=" * 60)

try:
    # Check tree-sitter-c is available
    from tree_sitter import Language, Parser
    from tree_sitter_c import language
    print("✓ tree-sitter-c dependency available")
    
    # Check c_parser.py exists
    c_parser_file = Path(__file__).parent / "app" / "services" / "parser" / "c_parser.py"
    if c_parser_file.exists():
        print(f"✓ c_parser.py exists: {c_parser_file}")
    else:
        print(f"✗ c_parser.py not found: {c_parser_file}")
        sys.exit(1)
    
    # Check parser_factory.py has the import
    factory_file = Path(__file__).parent / "app" / "services" / "parser" / "parser_factory.py"
    if factory_file.exists():
        content = factory_file.read_text()
        
        checks = [
            ("CTreeSitterParser import", "from app.services.parser.c_parser import CTreeSitterParser"),
            ("CParser alias", "CParser = CTreeSitterParser"),
            ("C in parsers dict", '"C": CParser()'),
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
    
    # Check requirements.txt has tree-sitter-c
    req_file = Path(__file__).parent / "requirements" / "base.txt"
    if req_file.exists():
        content = req_file.read_text()
        if "tree-sitter-c" in content:
            print("✓ tree-sitter-c in requirements/base.txt")
        else:
            print("✗ tree-sitter-c not in requirements")
            sys.exit(1)
    else:
        print(f"✗ requirements/base.txt not found: {req_file}")
        sys.exit(1)
    
    # Verify C parser structure
    c_parser_content = c_parser_file.read_text()
    
    structure_checks = [
        ("CTreeSitterParser class", "class CTreeSitterParser"),
        ("language property", "def language(self)"),
        ("supported_extensions property", "def supported_extensions(self)"),
        ("parse method", "def parse(self, file_path: Path)"),
        ("extract includes", "def _extract_includes"),
        ("extract macros", "def _extract_macros"),
        ("extract typedefs", "def _extract_typedefs"),
        ("extract structs", "def _extract_structs"),
        ("extract enums", "def _extract_enums"),
        ("extract functions", "def _extract_functions"),
        ("extract global variables", "def _extract_global_variables"),
    ]
    
    print("\n  C Parser structure verification:")
    all_passed = True
    for check_name, check_string in structure_checks:
        if check_string in c_parser_content:
            print(f"    ✓ {check_name}")
        else:
            print(f"    ✗ {check_name}")
            all_passed = False
    
    if not all_passed:
        sys.exit(1)
    
    print("\n" + "=" * 60)
    print("✓ All C parser factory integration checks passed!")
    print("=" * 60)
    print("\nNOTE: Full integration test requires:")
    print("  docker compose build")
    print("  docker compose up")
    print("  Then import a C repository to verify end-to-end parsing")
    
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
