"""Test C++ parser factory registration."""

from pathlib import Path
import sys

print("Testing C++ Parser Factory Registration")
print("=" * 60)

try:
    # Check tree-sitter-cpp is available
    from tree_sitter import Language, Parser
    from tree_sitter_cpp import language
    print("✓ tree-sitter-cpp dependency available")
    
    # Check cpp_parser.py exists
    cpp_parser_file = Path(__file__).parent / "app" / "services" / "parser" / "cpp_parser.py"
    if cpp_parser_file.exists():
        print(f"✓ cpp_parser.py exists: {cpp_parser_file}")
    else:
        print(f"✗ cpp_parser.py not found: {cpp_parser_file}")
        sys.exit(1)
    
    # Check parser_factory.py has the import
    factory_file = Path(__file__).parent / "app" / "services" / "parser" / "parser_factory.py"
    if factory_file.exists():
        content = factory_file.read_text()
        
        checks = [
            ("CppTreeSitterParser import", "from app.services.parser.cpp_parser import CppTreeSitterParser"),
            ("CppParser alias", "CppParser = CppTreeSitterParser"),
            ("C++ in parsers dict", '"C++": CppParser()'),
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
    
    # Check requirements.txt has tree-sitter-cpp
    req_file = Path(__file__).parent / "requirements" / "base.txt"
    if req_file.exists():
        content = req_file.read_text()
        if "tree-sitter-cpp" in content:
            print("✓ tree-sitter-cpp in requirements/base.txt")
        else:
            print("✗ tree-sitter-cpp not in requirements")
            sys.exit(1)
    else:
        print(f"✗ requirements/base.txt not found: {req_file}")
        sys.exit(1)
    
    # Verify C++ parser structure
    cpp_parser_content = cpp_parser_file.read_text()
    
    structure_checks = [
        ("CppTreeSitterParser class", "class CppTreeSitterParser"),
        ("language property", "def language(self)"),
        ("supported_extensions property", "def supported_extensions(self)"),
        ("parse method", "def parse(self, file_path: Path)"),
        ("extract namespaces", "def _extract_namespaces"),
        ("extract classes", "def _extract_classes"),
        ("extract structs", "def _extract_structs"),
        ("extract methods", "def _parse_method"),
        ("extract templates", "def _extract_templates"),
        ("extract enums", "def _extract_enums"),
        ("extract using statements", "def _extract_using_statements"),
        ("extract includes", "def _extract_includes"),
        ("extract free functions", "def _extract_free_functions"),
    ]
    
    print("\n  C++ Parser structure verification:")
    all_passed = True
    for check_name, check_string in structure_checks:
        if check_string in cpp_parser_content:
            print(f"    ✓ {check_name}")
        else:
            print(f"    ✗ {check_name}")
            all_passed = False
    
    if not all_passed:
        sys.exit(1)
    
    print("\n" + "=" * 60)
    print("✓ All C++ parser factory integration checks passed!")
    print("=" * 60)
    print("\nNOTE: Full integration test requires:")
    print("  docker compose build")
    print("  docker compose up")
    print("  Then import a C++ repository to verify end-to-end parsing")
    
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
