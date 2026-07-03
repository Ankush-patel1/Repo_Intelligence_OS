"""TypeScript Tree-sitter parser implementation.

This module provides concrete implementation of TypeScript source code parsing
using tree-sitter and tree-sitter-typescript.
"""

from pathlib import Path
from typing import Any

from tree_sitter import Language, Node, Parser, Tree
from tree_sitter_typescript import language_typescript

from app.services.parser.parser_interface import ParseResult, ParserInterface


class TypeScriptTreeSitterParser(ParserInterface):
    """Parser for TypeScript source files using tree-sitter.

    This parser uses tree-sitter-typescript to parse TypeScript code and extract:
    - Functions (regular functions, async functions, arrow functions)
    - Classes (with methods and static methods)
    - Interfaces (interface definitions)
    - Types (type aliases and type definitions)
    - Enums (enum declarations)
    - Imports (ES6 import statements)
    - Exports (ES6 export statements)
    """

    def __init__(self) -> None:
        """Initialize the TypeScript parser with tree-sitter language."""
        self._language = Language(language_typescript())
        self._parser = Parser(self._language)

    @property
    def language(self) -> str:
        """Return the language this parser handles."""
        return "TypeScript"

    @property
    def supported_extensions(self) -> list[str]:
        """Return list of file extensions this parser supports."""
        return [".ts", ".tsx"]

    def parse(self, file_path: Path) -> ParseResult:
        """Parse a TypeScript source file.

        Args:
            file_path: Path to the TypeScript source file

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
                    error_message="Syntax errors found in TypeScript code",
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
        """Extract symbols (interfaces, types, enums, functions, classes, imports, exports).

        Args:
            node: Root node of the parse tree
            source_code: Original source code as bytes

        Returns:
            List of symbol dictionaries
        """
        symbols: list[dict[str, Any]] = []

        # Extract imports
        symbols.extend(self._extract_imports(node, source_code))

        # Extract exports
        symbols.extend(self._extract_exports(node, source_code))

        # Extract interfaces
        symbols.extend(self._extract_interfaces(node, source_code))

        # Extract types
        symbols.extend(self._extract_types(node, source_code))

        # Extract enums
        symbols.extend(self._extract_enums(node, source_code))

        # Extract classes
        symbols.extend(self._extract_classes(node, source_code))

        # Extract top-level functions (including arrow functions)
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

        def find_imports(n: Node) -> None:
            if n.type == "import_statement":
                imports.append(
                    {
                        "type": "import",
                        "kind": "import",
                        "name": self._get_node_text(n, source_code),
                        "line": n.start_point[0] + 1,
                        "end_line": n.end_point[0] + 1,
                    }
                )
            # Recursively search children only for top-level imports
            for child in n.children:
                if child.type == "import_statement":
                    find_imports(child)

        find_imports(node)
        return imports

    def _extract_exports(self, node: Node, source_code: bytes) -> list[dict[str, Any]]:
        """Extract export statements from the AST.

        Args:
            node: Root node to search
            source_code: Original source code as bytes

        Returns:
            List of export symbol dictionaries
        """
        exports: list[dict[str, Any]] = []

        def find_exports(n: Node) -> None:
            if n.type == "export_statement":
                # Get export kind (named or default)
                export_text = self._get_node_text(n, source_code)
                kind = "default" if "export default" in export_text else "named"

                exports.append(
                    {
                        "type": "export",
                        "kind": kind,
                        "name": export_text,
                        "line": n.start_point[0] + 1,
                        "end_line": n.end_point[0] + 1,
                    }
                )

        # Only search top-level exports
        for child in node.children:
            find_exports(child)

        return exports

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
        name_node = None
        body_node = None

        for child in node.children:
            if child.type == "type_identifier":
                name_node = child
            elif child.type == "object_type":
                body_node = child

        interface_name = self._get_node_text(name_node, source_code) if name_node else "Unknown"

        # Extract members
        members: list[dict[str, Any]] = []
        if body_node:
            for member in body_node.children:
                if member.type == "property_signature":
                    member_info = self._parse_property_signature(member, source_code)
                    members.append(member_info)
                elif member.type == "method_signature":
                    member_info = self._parse_method_signature(member, source_code)
                    members.append(member_info)

        return {
            "type": "interface",
            "name": interface_name,
            "line": node.start_point[0] + 1,
            "end_line": node.end_point[0] + 1,
            "members": members,
        }

    def _parse_property_signature(self, node: Node, source_code: bytes) -> dict[str, Any]:
        """Parse a property signature in an interface.

        Args:
            node: Property signature node
            source_code: Original source code as bytes

        Returns:
            Dictionary with property information
        """
        name_node = None
        type_node = None
        is_optional = False

        for child in node.children:
            if child.type == "property_identifier":
                name_node = child
            elif child.type == "type_annotation":
                type_node = child
            elif child.type == "?":
                is_optional = True

        property_name = self._get_node_text(name_node, source_code) if name_node else "unknown"
        property_type = self._get_node_text(type_node, source_code) if type_node else "any"

        return {
            "type": "property",
            "name": property_name,
            "line": node.start_point[0] + 1,
            "end_line": node.end_point[0] + 1,
            "data_type": property_type,
            "is_optional": is_optional,
        }

    def _parse_method_signature(self, node: Node, source_code: bytes) -> dict[str, Any]:
        """Parse a method signature in an interface.

        Args:
            node: Method signature node
            source_code: Original source code as bytes

        Returns:
            Dictionary with method signature information
        """
        name_node = None
        parameters_node = None
        return_type_node = None
        is_optional = False

        for child in node.children:
            if child.type == "property_identifier":
                name_node = child
            elif child.type == "formal_parameters":
                parameters_node = child
            elif child.type == "type_annotation":
                return_type_node = child
            elif child.type == "?":
                is_optional = True

        method_name = self._get_node_text(name_node, source_code) if name_node else "unknown"
        parameters = self._extract_parameters(parameters_node, source_code) if parameters_node else []
        return_type = self._get_node_text(return_type_node, source_code) if return_type_node else "void"

        return {
            "type": "method_signature",
            "name": method_name,
            "line": node.start_point[0] + 1,
            "end_line": node.end_point[0] + 1,
            "parameters": parameters,
            "return_type": return_type,
            "is_optional": is_optional,
        }

    def _extract_types(self, node: Node, source_code: bytes) -> list[dict[str, Any]]:
        """Extract type aliases from the AST.

        Args:
            node: Root node to search
            source_code: Original source code as bytes

        Returns:
            List of type symbol dictionaries
        """
        types: list[dict[str, Any]] = []

        def find_types(n: Node) -> None:
            if n.type == "type_alias_declaration":
                type_info = self._parse_type_alias(n, source_code)
                types.append(type_info)
            # Recursively search children
            for child in n.children:
                find_types(child)

        find_types(node)
        return types

    def _parse_type_alias(self, node: Node, source_code: bytes) -> dict[str, Any]:
        """Parse a type alias declaration node.

        Args:
            node: Type alias declaration node
            source_code: Original source code as bytes

        Returns:
            Dictionary with type alias information
        """
        # Find type name and type annotation
        name_node = None
        type_node = None

        for child in node.children:
            if child.type == "type_identifier":
                name_node = child
            elif child.type == "object_type":
                type_node = child

        type_name = self._get_node_text(name_node, source_code) if name_node else "unknown"
        type_definition = self._get_node_text(type_node, source_code) if type_node else "any"

        return {
            "type": "type_alias",
            "name": type_name,
            "line": node.start_point[0] + 1,
            "end_line": node.end_point[0] + 1,
            "definition": type_definition,
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
        name_node = None
        body_node = None

        for child in node.children:
            if child.type == "identifier":
                name_node = child
            elif child.type == "enum_body":
                body_node = child

        enum_name = self._get_node_text(name_node, source_code) if name_node else "unknown"

        # Extract enum members
        members: list[dict[str, Any]] = []
        if body_node:
            for member in body_node.children:
                if member.type == "enum_assignment":
                    member_info = self._parse_enum_member(member, source_code)
                    members.append(member_info)

        return {
            "type": "enum",
            "name": enum_name,
            "line": node.start_point[0] + 1,
            "end_line": node.end_point[0] + 1,
            "members": members,
        }

    def _parse_enum_member(self, node: Node, source_code: bytes) -> dict[str, Any]:
        """Parse an enum member node.

        Args:
            node: Enum member node
            source_code: Original source code as bytes

        Returns:
            Dictionary with enum member information
        """
        name_node = None
        value_node = None

        for child in node.children:
            if child.type == "identifier":
                name_node = child
            elif child.type in ["string", "number"]:
                value_node = child

        member_name = self._get_node_text(name_node, source_code) if name_node else "unknown"
        member_value = self._get_node_text(value_node, source_code) if value_node else None

        return {
            "type": "enum_member",
            "name": member_name,
            "value": member_value,
            "line": node.start_point[0] + 1,
            "end_line": node.end_point[0] + 1,
        }

    def _extract_classes(self, node: Node, source_code: bytes) -> list[dict[str, Any]]:
        """Extract class definitions from the AST.

        Args:
            node: Root node to search
            source_code: Original source code as bytes

        Returns:
            List of class symbol dictionaries
        """
        classes: list[dict[str, Any]] = []

        # Maximum nesting depth for class extraction
        max_class_depth = 2

        def find_classes(n: Node, depth: int = 0) -> None:
            # Only extract top-level and first-level nested classes
            if n.type == "class_declaration" and depth < max_class_depth:
                class_info = self._parse_class(n, source_code)
                classes.append(class_info)
            elif depth < max_class_depth:
                # Continue searching in children
                for child in n.children:
                    find_classes(child, depth + 1)

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
        name_node = None
        body_node = None
        type_parameters_node = None

        for child in node.children:
            if child.type == "type_identifier":
                name_node = child
            elif child.type == "class_body":
                body_node = child
            elif child.type == "type_parameters":
                type_parameters_node = child

        class_name = self._get_node_text(name_node, source_code) if name_node else "Anonymous"
        type_parameters = self._get_node_text(type_parameters_node, source_code) if type_parameters_node else None

        # Extract methods from class body
        methods: list[dict[str, Any]] = []
        if body_node:
            for member in body_node.children:
                if member.type == "method_definition":
                    method_info = self._parse_method(member, source_code)
                    methods.append(method_info)
                elif member.type == "property_definition":
                    # Handle arrow function fields like: onClick = () => {}
                    field_info = self._parse_field(member, source_code)
                    if field_info:
                        methods.append(field_info)
                elif member.type == "accessor_property":
                    # Handle getters and setters
                    accessor_info = self._parse_accessor(member, source_code)
                    if accessor_info:
                        methods.append(accessor_info)

        return {
            "type": "class",
            "name": class_name,
            "line": node.start_point[0] + 1,
            "end_line": node.end_point[0] + 1,
            "type_parameters": type_parameters,
            "methods": methods,
        }

    def _parse_method(self, node: Node, source_code: bytes) -> dict[str, Any]:
        """Parse a method definition node.

        Args:
            node: Method definition node
            source_code: Original source code as bytes

        Returns:
            Dictionary with method information
        """
        name_node = None
        parameters_node = None
        return_type_node = None
        is_async = False
        is_static = False

        for child in node.children:
            if child.type == "property_identifier":
                name_node = child
            elif child.type == "formal_parameters":
                parameters_node = child
            elif child.type == "type_annotation":
                return_type_node = child
            elif child.type == "async":
                is_async = True
            elif child.type == "static":
                is_static = True

        method_name = self._get_node_text(name_node, source_code) if name_node else "unknown"
        parameters = self._extract_parameters(parameters_node, source_code) if parameters_node else []
        return_type = self._get_node_text(return_type_node, source_code) if return_type_node else "void"

        return {
            "type": "function",
            "name": method_name,
            "line": node.start_point[0] + 1,
            "end_line": node.end_point[0] + 1,
            "parameters": parameters,
            "return_type": return_type,
            "is_async": is_async,
            "is_method": True,
            "is_static": is_static,
            "is_arrow": False,
        }

    def _parse_field(self, node: Node, source_code: bytes) -> dict[str, Any] | None:
        """Parse a property definition that might contain an arrow function.

        Args:
            node: Property definition node
            source_code: Original source code as bytes

        Returns:
            Dictionary with field information if it's an arrow function, None otherwise
        """
        name_node = None
        arrow_node = None
        type_node = None

        for child in node.children:
            if child.type == "property_identifier":
                name_node = child
            elif child.type == "arrow_function":
                arrow_node = child
            elif child.type == "type_annotation":
                type_node = child

        # Only return info if it's an arrow function field
        if not arrow_node:
            return None

        field_name = self._get_node_text(name_node, source_code) if name_node else "unknown"
        return_type = self._get_node_text(type_node, source_code) if type_node else None

        # Extract parameters from arrow function
        parameters: list[str] = []
        is_async = False

        for child in arrow_node.children:
            if child.type == "formal_parameters":
                parameters = self._extract_parameters(child, source_code)
            elif child.type == "identifier":
                # Single parameter without parentheses
                parameters = [self._get_node_text(child, source_code)]
            elif child.type == "async":
                is_async = True

        return {
            "type": "function",
            "name": field_name,
            "line": node.start_point[0] + 1,
            "end_line": node.end_point[0] + 1,
            "parameters": parameters,
            "return_type": return_type,
            "is_async": is_async,
            "is_method": True,
            "is_static": False,
            "is_arrow": True,
        }

    def _parse_accessor(self, node: Node, source_code: bytes) -> dict[str, Any] | None:
        """Parse an accessor property (getter or setter).

        Args:
            node: Accessor property node
            source_code: Original source code as bytes

        Returns:
            Dictionary with accessor information, None if not a getter/setter
        """
        name_node = None
        body_node = None
        is_getter = False
        is_setter = False
        return_type_node = None

        for child in node.children:
            if child.type == "property_identifier":
                name_node = child
            elif child.type == "statement_block":
                body_node = child
            elif child.type == "get":
                is_getter = True
            elif child.type == "set":
                is_setter = True
            elif child.type == "type_annotation":
                return_type_node = child

        if not (is_getter or is_setter):
            return None

        accessor_name = self._get_node_text(name_node, source_code) if name_node else "unknown"
        return_type = self._get_node_text(return_type_node, source_code) if return_type_node else "any"

        accessor_type = "getter" if is_getter else "setter"

        # For setters, extract parameter
        parameters: list[str] = []
        if is_setter and body_node:
            # Look for parameter in setter
            for body_child in body_node.children:
                if body_child.type == "formal_parameters":
                    parameters = self._extract_parameters(body_child, source_code)

        return {
            "type": "function",
            "name": accessor_name,
            "line": node.start_point[0] + 1,
            "end_line": node.end_point[0] + 1,
            "parameters": parameters,
            "return_type": return_type if is_getter else "void",
            "is_async": False,
            "is_method": True,
            "is_static": False,
            "is_arrow": False,
            "method_type": accessor_type,
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
            if child.type == "function_declaration":
                func_info = self._parse_function_declaration(child, source_code)
                functions.append(func_info)
            elif child.type in {"lexical_declaration", "variable_declaration"}:
                # Check for arrow functions: const myFunc = () => {}
                arrow_funcs = self._extract_arrow_functions_from_declaration(child, source_code)
                functions.extend(arrow_funcs)
            elif child.type == "expression_statement":
                # Handle exported functions
                for expr_child in child.children:
                    if expr_child.type == "assignment_expression":
                        arrow_funcs = self._extract_arrow_functions_from_assignment(
                            expr_child, source_code
                        )
                        functions.extend(arrow_funcs)

        return functions

    def _parse_function_declaration(
        self, node: Node, source_code: bytes
    ) -> dict[str, Any]:
        """Parse a function declaration node.

        Args:
            node: Function declaration node
            source_code: Original source code as bytes

        Returns:
            Dictionary with function information
        """
        name_node = None
        parameters_node = None
        return_type_node = None
        is_async = False

        for child in node.children:
            if child.type == "identifier":
                name_node = child
            elif child.type == "formal_parameters":
                parameters_node = child
            elif child.type == "type_annotation":
                return_type_node = child
            elif child.type == "async":
                is_async = True

        func_name = self._get_node_text(name_node, source_code) if name_node else "anonymous"
        parameters = self._extract_parameters(parameters_node, source_code) if parameters_node else []
        return_type = self._get_node_text(return_type_node, source_code) if return_type_node else "void"

        return {
            "type": "function",
            "name": func_name,
            "line": node.start_point[0] + 1,
            "end_line": node.end_point[0] + 1,
            "parameters": parameters,
            "return_type": return_type,
            "is_async": is_async,
            "is_method": False,
            "is_arrow": False,
        }

    def _extract_arrow_functions_from_declaration(
        self, node: Node, source_code: bytes
    ) -> list[dict[str, Any]]:
        """Extract arrow functions from variable declarations.

        Args:
            node: Variable/lexical declaration node
            source_code: Original source code as bytes

        Returns:
            List of arrow function dictionaries
        """
        arrow_functions: list[dict[str, Any]] = []

        def find_arrow_in_declarator(declarator: Node) -> None:
            name_node = None
            arrow_node = None
            type_node = None
            is_async = False

            for child in declarator.children:
                if child.type == "identifier":
                    name_node = child
                elif child.type == "arrow_function":
                    arrow_node = child
                    # Check if arrow function is async
                    for arrow_child in child.children:
                        if arrow_child.type == "async":
                            is_async = True
                elif child.type == "type_annotation":
                    type_node = child

            if arrow_node and name_node:
                func_name = self._get_node_text(name_node, source_code)
                return_type = self._get_node_text(type_node, source_code) if type_node else None

                # Extract parameters
                parameters: list[str] = []
                for child in arrow_node.children:
                    if child.type == "formal_parameters":
                        parameters = self._extract_parameters(child, source_code)
                    elif child.type == "identifier":
                        # Single parameter without parentheses
                        parameters = [self._get_node_text(child, source_code)]

                arrow_functions.append(
                    {
                        "type": "function",
                        "name": func_name,
                        "line": declarator.start_point[0] + 1,
                        "end_line": declarator.end_point[0] + 1,
                        "parameters": parameters,
                        "return_type": return_type,
                        "is_async": is_async,
                        "is_method": False,
                        "is_arrow": True,
                    }
                )

        # Search through variable declarators
        for child in node.children:
            if child.type == "variable_declarator":
                find_arrow_in_declarator(child)

        return arrow_functions

    def _extract_arrow_functions_from_assignment(
        self, node: Node, source_code: bytes
    ) -> list[dict[str, Any]]:
        """Extract arrow functions from assignment expressions.

        Args:
            node: Assignment expression node
            source_code: Original source code as bytes

        Returns:
            List of arrow function dictionaries
        """
        arrow_functions: list[dict[str, Any]] = []

        name_node = None
        arrow_node = None
        is_async = False

        for child in node.children:
            if child.type in {"identifier", "member_expression"}:
                name_node = child
            elif child.type == "arrow_function":
                arrow_node = child
                for arrow_child in child.children:
                    if arrow_child.type == "async":
                        is_async = True

        if arrow_node and name_node:
            func_name = self._get_node_text(name_node, source_code)

            # Extract parameters
            parameters: list[str] = []
            for child in arrow_node.children:
                if child.type == "formal_parameters":
                    parameters = self._extract_parameters(child, source_code)
                elif child.type == "identifier":
                    parameters = [self._get_node_text(child, source_code)]

            arrow_functions.append(
                {
                    "type": "function",
                    "name": func_name,
                    "line": node.start_point[0] + 1,
                    "end_line": node.end_point[0] + 1,
                    "parameters": parameters,
                    "return_type": None,  # Assignment expressions don't have type annotations
                    "is_async": is_async,
                    "is_method": False,
                    "is_arrow": True,
                }
            )

        return arrow_functions

    def _extract_parameters(self, node: Node, source_code: bytes) -> list[str]:
        """Extract parameter names from a formal_parameters node.

        Args:
            node: Formal parameters node
            source_code: Original source code as bytes

        Returns:
            List of parameter names
        """
        parameters: list[str] = []

        for child in node.children:
            if child.type == "identifier":
                parameters.append(self._get_node_text(child, source_code))
            elif child.type == "required_parameter":
                # Required parameter with optional type annotation
                for param_child in child.children:
                    if param_child.type == "identifier":
                        parameters.append(self._get_node_text(param_child, source_code))
            elif child.type == "optional_parameter":
                # Optional parameter with default value
                for param_child in child.children:
                    if param_child.type == "identifier":
                        parameters.append(self._get_node_text(param_child, source_code))
            elif child.type == "rest_parameter":
                # Rest parameter (...args)
                for param_child in child.children:
                    if param_child.type == "identifier":
                        parameters.append(f"...{self._get_node_text(param_child, source_code)}")
            elif child.type in {"object_pattern", "array_pattern"}:
                # Destructured parameters
                parameters.append(self._get_node_text(child, source_code))

        return parameters

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
