"""Simple standalone test for C parser."""

from pathlib import Path
from dataclasses import dataclass
from abc import ABC, abstractmethod
from typing import Any

from tree_sitter import Language, Node, Parser, Tree
from tree_sitter_c import language


# Copy minimal interfaces needed
@dataclass(frozen=True)
class ParseResult:
    """Result of parsing a source code file."""
    file_path: str
    language: str
    success: bool
    error_message: str | None = None
    parse_tree: dict | None = None
    symbols: list[dict] | None = None


class ParserInterface(ABC):
    """Abstract base class for parsers."""
    
    @property
    @abstractmethod
    def language(self) -> str:
        pass

    @property
    @abstractmethod
    def supported_extensions(self) -> list[str]:
        pass

    @abstractmethod
    def parse(self, file_path: Path) -> ParseResult:
        pass


# Import the C parser by reading and executing it
exec(open('app/services/parser/c_parser.py').read())

# Run test
if __name__ == "__main__":
    print("Testing C Parser Implementation")
    print("=" * 60)
    
    # Test instantiation
    try:
        parser = CTreeSitterParser()
        print(f"✓ Parser instantiated")
        print(f"  Language: {parser.language}")
        print(f"  Extensions: {parser.supported_extensions}")
    except Exception as e:
        print(f"✗ Failed to instantiate: {e}")
        exit(1)
    
    # Test parsing sample C code
    sample_c = """
#include <stdio.h>
#include <stdlib.h>

#define MAX_SIZE 100
#define MIN(a, b) ((a) < (b) ? (a) : (b))

typedef struct Point {
    int x;
    int y;
} Point;

typedef enum Color {
    RED,
    GREEN,
    BLUE
} Color;

static int global_counter = 0;
extern int external_var;

static void helper_function(void);

int add(int a, int b) {
    return a + b;
}

void print_point(Point *p) {
    printf("Point: (%d, %d)\\n", p->x, p->y);
}

int main(int argc, char *argv[]) {
    Point p = {10, 20};
    print_point(&p);
    return 0;
}
"""
    
    test_file = Path("test_sample.c")
    try:
        test_file.write_text(sample_c)
        print("\n✓ Created test C file")
        
        result = parser.parse(test_file)
        
        if result.success:
            print("✓ Parse successful")
            print(f"  Parse tree type: {result.parse_tree.get('type')}")
            print(f"  Total symbols: {len(result.symbols)}")
            
            # Count symbol types
            symbol_types = {}
            for symbol in result.symbols:
                sym_type = symbol.get('type')
                symbol_types[sym_type] = symbol_types.get(sym_type, 0) + 1
            
            print(f"\n  Symbol breakdown:")
            for sym_type, count in sorted(symbol_types.items()):
                print(f"    - {sym_type}: {count}")
            
            print(f"\n  Sample symbols:")
            for i, symbol in enumerate(result.symbols[:12]):
                name = symbol.get('name', 'N/A')
                sym_type = symbol.get('type', 'N/A')
                line = symbol.get('line', 'N/A')
                print(f"    {i+1}. {sym_type}: {name} (line {line})")
        else:
            print(f"✗ Parse failed: {result.error_message}")
            exit(1)
    finally:
        if test_file.exists():
            test_file.unlink()
    
    print("\n" + "=" * 60)
    print("✓ C parser verified successfully!")
    print("=" * 60)
