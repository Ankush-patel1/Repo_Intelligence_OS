"""Python Tree-sitter parser implementation.

This module provides concrete implementation of Python source code parsing
using tree-sitter and tree-sitter-python.
"""

from pathlib import Path
from typing import Any

from tree_sitter import Language, Node, Parser, Tree
from tree_sitter_python import language

from app.services.parser.parser_interface import ParseResult, ParserInterface


class PythonTreeSitterParser(ParserInterface):
    """Parser for Python source files using tree-sitter.

    This parser uses tree-sitter-python to parse Python code and extract:
    - Functions (regular functions, async functions, methods)
    - Classes (with methods and decorators)
    - Imports (import statements, from-import statements)
    - Decorators (function and class decorators)
    """

    def __init__(self) -> None:
        """Initialize the Python parser with tree-sitter language."""
        self._language = Language(language())
        self._parser = Parser(self._language)

    @property
    def language(self) -> str:
        """Return the language this parser handles."""
        return "Python"

    @property
    def supported_extensions(self) -> list[str]:
        """Return list of file extensions this parser supports."""
        return [".py"]

    def parse(self, file_path: Path) -> ParseResult:
        """Parse a Python source file.

        Args:
            file_path: Path to the Python source file

        Returns:
            ParseResult containing parsed AST and extracted symbols
        """
        try:
            # Read the source code
            source_code = file_path.read_bytes()

            # Parse the source code
            tree = self._parser.parse(source_code)

            if tree.root_node.has_error:
                return ParseResult(
                    file_path=str(file_path),
                    language=self.language,
                    success=False,
                    error_message="Syntax errors found in Python code",
                    parse_tree=None,
                    symbols=None,
                )

            # Extract structured information
            parse_tree = self._build_parse_tree(tree)
            symbols = self._extract_symbols(tree.root_node, source_code)

            return ParseResult(
                file_path=str(file_path),
                language=self.language,
                success=True,
                error_message=None,
                parse_tree=parse_tree,
                symbols=symbols,
            )

        except FileNotFoundError:
            return ParseResult(
                file_path=str(file_path),
                language=self.language,
                success=False,
                error_message=f"File not found: {file_path}",
                parse_tree=None,
                symbols=None,
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

    def _build_parse_tree(self, tree: Tree) -> dict[str, Any]:
        """Build a simplified parse tree structure.

        Args:
            tree: Tree-sitter parse tree

        Returns:
            Dictionary representing the parse tree structure
        """
        root = tree.root_node
        return {
            "type": root.type,
            "start_line": root.start_point[0] + 1,
            "end_line": root.end_point[0] + 1,
            "children_count": len(root.children),
            "has_error": root.has_error,
        }

    def _extract_symbols(self, node: Node, source_code: bytes) -> list[dict[str, Any]]:
        """Extract symbols (functions, classes, imports) from the AST.

        Args:
            node: Root node of the parse tree
            source_code: Original source code as bytes

        Returns:
            List of symbol dictionaries
        """
        symbols: list[dict[str, Any]] = []

        # Extract imports
        symbols.extend(self._extract_imports(node, source_code))

        # Extract classes
        symbols.extend(self._extract_classes(node, source_code))

        # Extract top-level functions
        symbols.extend(self._extract_functions(node, source_code))

        return symbols

    def _extract_imports(self, node: Node, source_code: bytes) -> list[dict[str, Any]]:
        """Extract import statements from the AST.

        Args:
            node: Root node to search
            source_code: Original source code as bytes

        Returns:
            List of import symbol dictionaries
        """
        imports: list[dict[str, Any]] = []

        # Find all import_statement and import_from_statement nodes
        for child in node.children:
            if child.type == "import_statement":
                imports.append(
                    {
                        "type": "import",
                        "kind": "import",
                        "name": self._get_node_text(child, source_code),
                        "line": child.start_point[0] + 1,
                        "end_line": child.end_point[0] + 1,
                    }
                )
            elif child.type == "import_from_statement":
                imports.append(
                    {
                        "type": "import",
                        "kind": "from_import",
                        "name": self._get_node_text(child, source_code),
                        "line": child.start_point[0] + 1,
                        "end_line": child.end_point[0] + 1,
                    }
                )

        return imports

    def _extract_classes(self, node: Node, source_code: bytes) -> list[dict[str, Any]]:
        """Extract class definitions from the AST.

        Args:
            node: Root node to search
            source_code: Original source code as bytes

        Returns:
            List of class symbol dictionaries
        """
        classes: list[dict[str, Any]] = []

        def find_classes(n: Node) -> None:
            if n.type == "class_definition":
                class_info = self._parse_class(n, source_code)
                classes.append(class_info)
            # Recursively search children
            for child in n.children:
                find_classes(child)

        find_classes(node)
        return classes

    def _parse_class(self, node: Node, source_code: bytes) -> dict[str, Any]:
        """Parse a class definition node.

        Args:
            node: Class definition node
            source_code: Original source code as bytes

        Returns:
            Dictionary with class information
        """
        # Find class name
        name_node = None
        for child in node.children:
            if child.type == "identifier":
                name_node = child
                break

        class_name = self._get_node_text(name_node, source_code) if name_node else "Unknown"

        # Extract decorators
        decorators = self._extract_decorators(node, source_code)

        # Extract methods
        methods: list[dict[str, Any]] = []
        for child in node.children:
            if child.type == "block":
                for method_node in child.children:
                    if method_node.type == "function_definition":
                        method_info = self._parse_function(method_node, source_code)
                        method_info["is_method"] = True
                        methods.append(method_info)
                    elif method_node.type == "decorated_definition":
                        # Handle decorated methods
                        for decorated_child in method_node.children:
                            if decorated_child.type == "function_definition":
                                method_info = self._parse_function(
                                    decorated_child, source_code
                                )
                                method_info["is_method"] = True
                                method_info["decorators"] = self._extract_decorators(
                                    method_node, source_code
                                )
                                methods.append(method_info)

        return {
            "type": "class",
            "name": class_name,
            "line": node.start_point[0] + 1,
            "end_line": node.end_point[0] + 1,
            "decorators": decorators,
            "methods": methods,
        }

    def _extract_functions(self, node: Node, source_code: bytes) -> list[dict[str, Any]]:
        """Extract top-level function definitions from the AST.

        Args:
            node: Root node to search
            source_code: Original source code as bytes

        Returns:
            List of function symbol dictionaries
        """
        functions: list[dict[str, Any]] = []

        for child in node.children:
            if child.type == "function_definition":
                func_info = self._parse_function(child, source_code)
                functions.append(func_info)
            elif child.type == "decorated_definition":
                # Handle decorated functions
                for decorated_child in child.children:
                    if decorated_child.type == "function_definition":
                        func_info = self._parse_function(decorated_child, source_code)
                        func_info["decorators"] = self._extract_decorators(child, source_code)
                        functions.append(func_info)

        return functions

    def _parse_function(self, node: Node, source_code: bytes) -> dict[str, Any]:  # noqa: PLR0912
        """Parse a function definition node.

        Args:
            node: Function definition node
            source_code: Original source code as bytes

        Returns:
            Dictionary with function information
        """
        # Find function name
        name_node = None
        parameters_node = None
        is_async = False

        for child in node.children:
            if child.type == "identifier":
                name_node = child
            elif child.type == "parameters":
                parameters_node = child

        # Check if it's an async function (parent might be async)
        if node.parent and node.parent.type == "async":
            is_async = True

        func_name = self._get_node_text(name_node, source_code) if name_node else "Unknown"

        # Extract parameters
        parameters: list[str] = []
        if parameters_node:
            for param_child in parameters_node.children:
                if param_child.type == "identifier":
                    parameters.append(self._get_node_text(param_child, source_code))
                elif param_child.type == "typed_parameter":
                    # For typed parameters, get the identifier part
                    for typed_child in param_child.children:
                        if typed_child.type == "identifier":
                            parameters.append(self._get_node_text(typed_child, source_code))
                            break
                elif param_child.type == "default_parameter":
                    # For parameters with defaults
                    for default_child in param_child.children:
                        if default_child.type == "identifier":
                            parameters.append(self._get_node_text(default_child, source_code))
                            break

        return {
            "type": "function",
            "name": func_name,
            "line": node.start_point[0] + 1,
            "end_line": node.end_point[0] + 1,
            "parameters": parameters,
            "is_async": is_async,
            "is_method": False,
            "decorators": [],
        }

    def _extract_decorators(self, node: Node, source_code: bytes) -> list[str]:
        """Extract decorators from a decorated definition.

        Args:
            node: Decorated definition node or class/function node
            source_code: Original source code as bytes

        Returns:
            List of decorator names
        """
        decorators: list[str] = []

        # If this is a decorated_definition, look for decorator children
        if node.type == "decorated_definition":
            for child in node.children:
                if child.type == "decorator":
                    decorator_text = self._get_node_text(child, source_code)
                    # Remove the @ symbol
                    decorators.append(decorator_text.lstrip("@").strip())

        return decorators

    def _get_node_text(self, node: Node | None, source_code: bytes) -> str:
        """Extract text content from a node.

        Args:
            node: Tree-sitter node
            source_code: Original source code as bytes

        Returns:
            Text content of the node
        """
        if node is None:
            return ""
        return source_code[node.start_byte : node.end_byte].decode("utf-8")
