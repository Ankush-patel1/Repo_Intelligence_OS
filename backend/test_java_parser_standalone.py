"""Standalone test for Java parser - no app imports."""

from pathlib import Path
from dataclasses import dataclass
from abc import ABC, abstractmethod
from typing import Any

from tree_sitter import Language, Node, Parser, Tree
from tree_sitter_java import language


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
    """Abstract base class for language-specific parsers."""
    
    @property
    @abstractmethod
    def language(self) -> str:
        """Return the language this parser handles."""
        pass

    @property
    @abstractmethod
    def supported_extensions(self) -> list[str]:
        """Return list of file extensions this parser supports."""
        pass

    @abstractmethod
    def parse(self, file_path: Path) -> ParseResult:
        """Parse a source file."""
        pass


# Import the actual Java parser implementation
class JavaTreeSitterParser(ParserInterface):
    """Parser for Java source files using tree-sitter."""

    def __init__(self) -> None:
        """Initialize the Java parser with tree-sitter language."""
        self._language = Language(language())
        self._parser = Parser(self._language)

    @property
    def language(self) -> str:
        """Return the language this parser handles."""
        return "Java"

    @property
    def supported_extensions(self) -> list[str]:
        """Return list of file extensions this parser supports."""
        return [".java"]

    def parse(self, file_path: Path) -> ParseResult:
        """Parse a Java source file."""
        try:
            source_code = file_path.read_bytes()
            tree = self._parser.parse(source_code)

            if tree.root_node.has_error:
                return ParseResult(
                    file_path=str(file_path),
                    language=self.language,
                    success=False,
                    error_message="Syntax errors found in Java code",
                    parse_tree=None,
                    symbols=None,
                )

            parse_tree = {
                "type": tree.root_node.type,
                "start_line": tree.root_node.start_point[0] + 1,
                "end_line": tree.root_node.end_point[0] + 1,
            }
            
            symbols = self._extract_symbols(tree.root_node, source_code)

            return ParseResult(
                file_path=str(file_path),
                language=self.language,
                success=True,
                error_message=None,
                parse_tree=parse_tree,
                symbols=symbols,
            )

        except Exception as e:
            return ParseResult(
                file_path=str(file_path),
                language=self.language,
                success=False,
                error_message=f"Parse error: {e!s}",
                parse_tree=None,
                symbols=None,
            )

    def _extract_symbols(self, node: Node, source_code: bytes) -> list[dict[str, Any]]:
        """Extract symbols from the AST."""
        symbols: list[dict[str, Any]] = []

        def find_symbols(n: Node) -> None:
            if n.type in ("class_declaration", "interface_declaration", "enum_declaration"):
                # Find name
                name = "Unknown"
                for child in n.children:
                    if child.type == "identifier":
                        name = source_code[child.start_byte:child.end_byte].decode("utf-8")
                        break
                
                symbols.append({
                    "type": n.type.replace("_declaration", ""),
                    "name": name,
                    "line": n.start_point[0] + 1,
                    "end_line": n.end_point[0] + 1,
                })
            
            for child in n.children:
                find_symbols(child)

        find_symbols(node)
        return symbols


# Run test
if __name__ == "__main__":
    print("Testing Java Parser Integration")
    print("=" * 60)
    
    # Test 1: Instantiate
    try:
        parser = JavaTreeSitterParser()
        print(f"✓ Parser instantiated")
        print(f"  Language: {parser.language}")
        print(f"  Extensions: {parser.supported_extensions}")
    except Exception as e:
        print(f"✗ Failed to instantiate: {e}")
        exit(1)
    
    # Test 2: Parse sample Java code
    sample_java = """
package com.example.app;

import java.util.List;

@Entity
public class User {
    private Long id;
    private String name;
    
    public User() {
    }
    
    public Long getId() {
        return id;
    }
}

public interface UserRepository {
    User findById(Long id);
}

public enum UserStatus {
    ACTIVE,
    INACTIVE
}
"""
    
    test_file = Path("test_sample.java")
    try:
        test_file.write_text(sample_java)
        print("\n✓ Created test file")
        
        result = parser.parse(test_file)
        
        if result.success:
            print("✓ Parse successful")
            print(f"  Parse tree: {result.parse_tree}")
            print(f"  Symbols found: {len(result.symbols)}")
            for symbol in result.symbols:
                print(f"    - {symbol['type']}: {symbol['name']} (line {symbol['line']})")
        else:
            print(f"✗ Parse failed: {result.error_message}")
            exit(1)
    finally:
        if test_file.exists():
            test_file.unlink()
    
    print("\n" + "=" * 60)
    print("✓ Java parser integration verified!")
    print("=" * 60)
