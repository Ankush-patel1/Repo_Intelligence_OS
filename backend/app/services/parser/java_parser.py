"""Java Tree-sitter parser implementation.

This module provides concrete implementation of Java source code parsing
using tree-sitter and tree-sitter-java.
"""

from pathlib import Path
from typing import Any

from tree_sitter import Language, Node, Parser, Tree
from tree_sitter_java import language

from app.services.parser.parser_interface import ParseResult, ParserInterface


class JavaTreeSitterParser(ParserInterface):
    """Parser for Java source files using tree-sitter.

    This parser uses tree-sitter-java to parse Java code and extract:
    - Package declarations
    - Imports
    - Classes (with methods, constructors, fields)
    - Interfaces
    - Enums
    - Annotations
    """

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
        """Parse a Java source file.

        Args:
            file_path: Path to the Java source file

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
                    error_message="Syntax errors found in Java code",
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
        """Extract symbols from the AST.

        Args:
            node: Root node of the parse tree
            source_code: Original source code as bytes

        Returns:
            List of symbol dictionaries
        """
        symbols: list[dict[str, Any]] = []

        # Extract package declaration
        symbols.extend(self._extract_package(node, source_code))

        # Extract imports
        symbols.extend(self._extract_imports(node, source_code))

        # Extract classes
        symbols.extend(self._extract_classes(node, source_code))

        # Extract interfaces
        symbols.extend(self._extract_interfaces(node, source_code))

        # Extract enums
        symbols.extend(self._extract_enums(node, source_code))

        return symbols

    def _extract_package(self, node: Node, source_code: bytes) -> list[dict[str, Any]]:
        """Extract package declaration from the AST.

        Args:
            node: Root node to search
            source_code: Original source code as bytes

        Returns:
            List with package declaration
        """
        packages: list[dict[str, Any]] = []

        def find_package(n: Node) -> None:
            if n.type == "package_declaration":
                package_name = ""
                for child in n.children:
                    if child.type == "scoped_identifier" or child.type == "identifier":
                        package_name = self._get_node_text(child, source_code)
                        break

                packages.append(
                    {
                        "type": "package",
                        "name": package_name,
                        "line": n.start_point[0] + 1,
                        "end_line": n.end_point[0] + 1,
                    }
                )
            # Only search top-level children
            elif n == node:
                for child in n.children:
                    find_package(child)

        find_package(node)
        return packages

    def _extract_imports(self, node: Node, source_code: bytes) -> list[dict[str, Any]]:
        """Extract import statements from the AST.

        Args:
            node: Root node to search
            source_code: Original source code as bytes

        Returns:
            List of import symbol dictionaries
        """
        imports: list[dict[str, Any]] = []

        def find_imports(n: Node) -> None:
            if n.type == "import_declaration":
                import_text = self._get_node_text(n, source_code)
                is_static = "static" in import_text

                imports.append(
                    {
                        "type": "import",
                        "kind": "static_import" if is_static else "import",
                        "name": import_text,
                        "line": n.start_point[0] + 1,
                        "end_line": n.end_point[0] + 1,
                    }
                )
            # Only search top-level children for imports
            elif n == node:
                for child in n.children:
                    find_imports(child)

        find_imports(node)
        return imports

    def _extract_classes(self, node: Node, source_code: bytes) -> list[dict[str, Any]]:
        """Extract class declarations from the AST.

        Args:
            node: Root node to search
            source_code: Original source code as bytes

        Returns:
            List of class symbol dictionaries
        """
        classes: list[dict[str, Any]] = []

        def find_classes(n: Node) -> None:
            if n.type == "class_declaration":
                class_info = self._parse_class(n, source_code)
                classes.append(class_info)
            # Recursively search children
            for child in n.children:
                find_classes(child)

        find_classes(node)
        return classes

    def _parse_class(self, node: Node, source_code: bytes) -> dict[str, Any]:
        """Parse a class declaration node.

        Args:
            node: Class declaration node
            source_code: Original source code as bytes

        Returns:
            Dictionary with class information
        """
        # Find class name
        class_name = "Unknown"
        for child in node.children:
            if child.type == "identifier":
                class_name = self._get_node_text(child, source_code)
                break

        # Extract modifiers and annotations
        modifiers = self._extract_modifiers(node, source_code)
        annotations = self._extract_annotations(node, source_code)

        # Extract methods, constructors, and fields
        methods: list[dict[str, Any]] = []
        constructors: list[dict[str, Any]] = []
        fields: list[dict[str, Any]] = []

        for child in node.children:
            if child.type == "class_body":
                for body_child in child.children:
                    if body_child.type == "method_declaration":
                        method_info = self._parse_method(body_child, source_code)
                        methods.append(method_info)
                    elif body_child.type == "constructor_declaration":
                        constructor_info = self._parse_constructor(body_child, source_code)
                        constructors.append(constructor_info)
                    elif body_child.type == "field_declaration":
                        field_infos = self._parse_field(body_child, source_code)
                        fields.extend(field_infos)

        return {
            "type": "class",
            "name": class_name,
            "line": node.start_point[0] + 1,
            "end_line": node.end_point[0] + 1,
            "modifiers": modifiers,
            "annotations": annotations,
            "methods": methods,
            "constructors": constructors,
            "fields": fields,
        }

    def _extract_interfaces(self, node: Node, source_code: bytes) -> list[dict[str, Any]]:
        """Extract interface declarations from the AST.

        Args:
            node: Root node to search
            source_code: Original source code as bytes

        Returns:
            List of interface symbol dictionaries
        """
        interfaces: list[dict[str, Any]] = []

        def find_interfaces(n: Node) -> None:
            if n.type == "interface_declaration":
                interface_info = self._parse_interface(n, source_code)
                interfaces.append(interface_info)
            # Recursively search children
            for child in n.children:
                find_interfaces(child)

        find_interfaces(node)
        return interfaces

    def _parse_interface(self, node: Node, source_code: bytes) -> dict[str, Any]:
        """Parse an interface declaration node.

        Args:
            node: Interface declaration node
            source_code: Original source code as bytes

        Returns:
            Dictionary with interface information
        """
        # Find interface name
        interface_name = "Unknown"
        for child in node.children:
            if child.type == "identifier":
                interface_name = self._get_node_text(child, source_code)
                break

        # Extract modifiers and annotations
        modifiers = self._extract_modifiers(node, source_code)
        annotations = self._extract_annotations(node, source_code)

        # Extract method declarations
        methods: list[dict[str, Any]] = []
        for child in node.children:
            if child.type == "interface_body":
                for body_child in child.children:
                    if body_child.type in ("method_declaration", "constant_declaration"):
                        if body_child.type == "method_declaration":
                            method_info = self._parse_method(body_child, source_code)
                            methods.append(method_info)

        return {
            "type": "interface",
            "name": interface_name,
            "line": node.start_point[0] + 1,
            "end_line": node.end_point[0] + 1,
            "modifiers": modifiers,
            "annotations": annotations,
            "methods": methods,
        }

    def _extract_enums(self, node: Node, source_code: bytes) -> list[dict[str, Any]]:
        """Extract enum declarations from the AST.

        Args:
            node: Root node to search
            source_code: Original source code as bytes

        Returns:
            List of enum symbol dictionaries
        """
        enums: list[dict[str, Any]] = []

        def find_enums(n: Node) -> None:
            if n.type == "enum_declaration":
                enum_info = self._parse_enum(n, source_code)
                enums.append(enum_info)
            # Recursively search children
            for child in n.children:
                find_enums(child)

        find_enums(node)
        return enums

    def _parse_enum(self, node: Node, source_code: bytes) -> dict[str, Any]:
        """Parse an enum declaration node.

        Args:
            node: Enum declaration node
            source_code: Original source code as bytes

        Returns:
            Dictionary with enum information
        """
        # Find enum name
        enum_name = "Unknown"
        for child in node.children:
            if child.type == "identifier":
                enum_name = self._get_node_text(child, source_code)
                break

        # Extract modifiers and annotations
        modifiers = self._extract_modifiers(node, source_code)
        annotations = self._extract_annotations(node, source_code)

        # Extract enum constants
        constants: list[str] = []
        for child in node.children:
            if child.type == "enum_body":
                for body_child in child.children:
                    if body_child.type == "enum_constant":
                        for constant_child in body_child.children:
                            if constant_child.type == "identifier":
                                constants.append(self._get_node_text(constant_child, source_code))
                                break

        return {
            "type": "enum",
            "name": enum_name,
            "line": node.start_point[0] + 1,
            "end_line": node.end_point[0] + 1,
            "modifiers": modifiers,
            "annotations": annotations,
            "constants": constants,
        }

    def _parse_method(self, node: Node, source_code: bytes) -> dict[str, Any]:
        """Parse a method declaration node.

        Args:
            node: Method declaration node
            source_code: Original source code as bytes

        Returns:
            Dictionary with method information
        """
        # Find method name
        method_name = "Unknown"
        for child in node.children:
            if child.type == "identifier":
                method_name = self._get_node_text(child, source_code)
                break

        # Extract modifiers and annotations
        modifiers = self._extract_modifiers(node, source_code)
        annotations = self._extract_annotations(node, source_code)

        # Extract parameters
        parameters: list[str] = []
        return_type = None

        for child in node.children:
            if child.type == "formal_parameters":
                parameters = self._extract_parameters(child, source_code)
            elif child.type in ("type_identifier", "void_type", "integral_type", 
                               "floating_point_type", "boolean_type", "generic_type",
                               "array_type", "scoped_type_identifier"):
                return_type = self._get_node_text(child, source_code)

        # Build signature
        params_str = ", ".join(parameters) if parameters else ""
        return_str = f"{return_type} " if return_type else ""
        signature = f"{return_str}{method_name}({params_str})"

        return {
            "type": "method",
            "name": method_name,
            "line": node.start_point[0] + 1,
            "end_line": node.end_point[0] + 1,
            "modifiers": modifiers,
            "annotations": annotations,
            "parameters": parameters,
            "return_type": return_type,
            "signature": signature,
        }

    def _parse_constructor(self, node: Node, source_code: bytes) -> dict[str, Any]:
        """Parse a constructor declaration node.

        Args:
            node: Constructor declaration node
            source_code: Original source code as bytes

        Returns:
            Dictionary with constructor information
        """
        # Find constructor name
        constructor_name = "Unknown"
        for child in node.children:
            if child.type == "identifier":
                constructor_name = self._get_node_text(child, source_code)
                break

        # Extract modifiers and annotations
        modifiers = self._extract_modifiers(node, source_code)
        annotations = self._extract_annotations(node, source_code)

        # Extract parameters
        parameters: list[str] = []
        for child in node.children:
            if child.type == "formal_parameters":
                parameters = self._extract_parameters(child, source_code)
                break

        # Build signature
        params_str = ", ".join(parameters) if parameters else ""
        signature = f"{constructor_name}({params_str})"

        return {
            "type": "constructor",
            "name": constructor_name,
            "line": node.start_point[0] + 1,
            "end_line": node.end_point[0] + 1,
            "modifiers": modifiers,
            "annotations": annotations,
            "parameters": parameters,
            "signature": signature,
        }

    def _parse_field(self, node: Node, source_code: bytes) -> list[dict[str, Any]]:
        """Parse a field declaration node.

        Args:
            node: Field declaration node
            source_code: Original source code as bytes

        Returns:
            List of field dictionaries (can declare multiple fields)
        """
        fields: list[dict[str, Any]] = []

        # Extract modifiers and annotations
        modifiers = self._extract_modifiers(node, source_code)
        annotations = self._extract_annotations(node, source_code)

        # Extract field type
        field_type = None
        for child in node.children:
            if child.type in ("type_identifier", "integral_type", "floating_point_type",
                            "boolean_type", "generic_type", "array_type", 
                            "scoped_type_identifier"):
                field_type = self._get_node_text(child, source_code)
                break

        # Extract variable declarators (can be multiple fields in one declaration)
        for child in node.children:
            if child.type == "variable_declarator":
                field_name = "Unknown"
                for declarator_child in child.children:
                    if declarator_child.type == "identifier":
                        field_name = self._get_node_text(declarator_child, source_code)
                        break

                fields.append(
                    {
                        "type": "field",
                        "name": field_name,
                        "line": node.start_point[0] + 1,
                        "end_line": node.end_point[0] + 1,
                        "modifiers": modifiers,
                        "annotations": annotations,
                        "field_type": field_type,
                    }
                )

        return fields

    def _extract_parameters(self, node: Node, source_code: bytes) -> list[str]:
        """Extract parameters from a formal_parameters node.

        Args:
            node: Formal parameters node
            source_code: Original source code as bytes

        Returns:
            List of parameter names
        """
        parameters: list[str] = []

        for child in node.children:
            if child.type == "formal_parameter":
                # Find the identifier in the formal parameter
                for param_child in child.children:
                    if param_child.type == "identifier":
                        parameters.append(self._get_node_text(param_child, source_code))
                        break
            elif child.type == "spread_parameter":
                # Handle varargs
                for param_child in child.children:
                    if param_child.type == "identifier":
                        param_name = self._get_node_text(param_child, source_code)
                        parameters.append(f"...{param_name}")
                        break

        return parameters

    def _extract_modifiers(self, node: Node, source_code: bytes) -> list[str]:
        """Extract modifiers from a declaration node.

        Args:
            node: Declaration node
            source_code: Original source code as bytes

        Returns:
            List of modifiers (public, private, static, etc.)
        """
        modifiers: list[str] = []

        for child in node.children:
            if child.type == "modifiers":
                for modifier_child in child.children:
                    if modifier_child.type in (
                        "public",
                        "private",
                        "protected",
                        "static",
                        "final",
                        "abstract",
                        "synchronized",
                        "native",
                        "strictfp",
                        "transient",
                        "volatile",
                    ):
                        modifiers.append(modifier_child.type)

        return modifiers

    def _extract_annotations(self, node: Node, source_code: bytes) -> list[str]:
        """Extract annotations from a declaration node.

        Args:
            node: Declaration node
            source_code: Original source code as bytes

        Returns:
            List of annotation names
        """
        annotations: list[str] = []

        for child in node.children:
            if child.type == "modifiers":
                for modifier_child in child.children:
                    if modifier_child.type == "marker_annotation":
                        annotation_text = self._get_node_text(modifier_child, source_code)
                        # Remove the @ symbol
                        annotations.append(annotation_text.lstrip("@").strip())
                    elif modifier_child.type in ("annotation", "marker_annotation"):
                        annotation_text = self._get_node_text(modifier_child, source_code)
                        annotations.append(annotation_text.lstrip("@").strip())

        return annotations

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
