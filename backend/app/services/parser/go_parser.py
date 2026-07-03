"""Go Tree-sitter parser implementation.

This module provides concrete implementation of Go source code parsing
using tree-sitter and tree-sitter-go.
"""

from pathlib import Path
from typing import Any

from tree_sitter import Language, Node, Parser, Tree
from tree_sitter_go import language

from app.services.parser.parser_interface import ParseResult, ParserInterface


class GoTreeSitterParser(ParserInterface):
    """Parser for Go source files using tree-sitter.

    This parser uses tree-sitter-go to parse Go code and extract:
    - Package declarations
    - Import statements
    - Structs (struct types)
    - Interfaces
    - Functions (top-level functions)
    - Methods (functions with receivers)
    - Constants
    - Variables
    - Type declarations
    """

    def __init__(self) -> None:
        """Initialize the Go parser with tree-sitter language."""
        self._language = Language(language())
        self._parser = Parser(self._language)

    @property
    def language(self) -> str:
        """Return the language this parser handles."""
        return "Go"

    @property
    def supported_extensions(self) -> list[str]:
        """Return list of file extensions this parser supports."""
        return [".go"]

    def parse(self, file_path: Path) -> ParseResult:
        """Parse a Go source file.

        Args:
            file_path: Path to the Go source file

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
                    error_message="Syntax errors found in Go code",
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

        # Extract constants
        symbols.extend(self._extract_constants(node, source_code))

        # Extract variables
        symbols.extend(self._extract_variables(node, source_code))

        # Extract type declarations (including structs and interfaces)
        symbols.extend(self._extract_type_declarations(node, source_code))

        # Extract functions
        symbols.extend(self._extract_functions(node, source_code))

        # Extract methods
        symbols.extend(self._extract_methods(node, source_code))

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

        for child in node.children:
            if child.type == "package_clause":
                package_name = ""
                for pkg_child in child.children:
                    if pkg_child.type == "package_identifier":
                        package_name = self._get_node_text(pkg_child, source_code)
                        break

                packages.append(
                    {
                        "type": "package",
                        "name": package_name,
                        "line": child.start_point[0] + 1,
                        "end_line": child.end_point[0] + 1,
                    }
                )
                break  # Only one package declaration per file

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

        for child in node.children:
            if child.type == "import_declaration":
                # Single import or import group
                for import_child in child.children:
                    if import_child.type == "import_spec":
                        import_info = self._parse_import_spec(import_child, source_code)
                        if import_info:
                            imports.append(import_info)
                    elif import_child.type == "import_spec_list":
                        for spec in import_child.children:
                            if spec.type == "import_spec":
                                import_info = self._parse_import_spec(spec, source_code)
                                if import_info:
                                    imports.append(import_info)

        return imports

    def _parse_import_spec(self, node: Node, source_code: bytes) -> dict[str, Any] | None:
        """Parse an import specification.

        Args:
            node: Import spec node
            source_code: Original source code as bytes

        Returns:
            Dictionary with import information or None
        """
        path = ""
        alias = ""

        for child in node.children:
            if child.type == "interpreted_string_literal":
                path = self._get_node_text(child, source_code).strip('"')
            elif child.type in ("package_identifier", "identifier"):
                # Import alias
                alias = self._get_node_text(child, source_code)

        if path:
            return {
                "type": "import",
                "path": path,
                "alias": alias if alias else None,
                "line": node.start_point[0] + 1,
                "end_line": node.end_point[0] + 1,
            }
        return None

    def _extract_constants(self, node: Node, source_code: bytes) -> list[dict[str, Any]]:
        """Extract constant declarations from the AST.

        Args:
            node: Root node to search
            source_code: Original source code as bytes

        Returns:
            List of constant symbol dictionaries
        """
        constants: list[dict[str, Any]] = []

        for child in node.children:
            if child.type == "const_declaration":
                constants.extend(self._parse_const_declaration(child, source_code))

        return constants

    def _parse_const_declaration(
        self, node: Node, source_code: bytes
    ) -> list[dict[str, Any]]:
        """Parse a const declaration.

        Args:
            node: Const declaration node
            source_code: Original source code as bytes

        Returns:
            List of constant dictionaries
        """
        constants: list[dict[str, Any]] = []

        for child in node.children:
            if child.type == "const_spec":
                const_names: list[str] = []
                const_type = ""
                
                for spec_child in child.children:
                    if spec_child.type == "identifier":
                        const_names.append(self._get_node_text(spec_child, source_code))
                    elif spec_child.type in ("type_identifier", "qualified_type"):
                        const_type = self._get_node_text(spec_child, source_code)

                for const_name in const_names:
                    constants.append(
                        {
                            "type": "constant",
                            "name": const_name,
                            "const_type": const_type,
                            "line": child.start_point[0] + 1,
                            "end_line": child.end_point[0] + 1,
                        }
                    )

        return constants

    def _extract_variables(self, node: Node, source_code: bytes) -> list[dict[str, Any]]:
        """Extract variable declarations from the AST.

        Args:
            node: Root node to search
            source_code: Original source code as bytes

        Returns:
            List of variable symbol dictionaries
        """
        variables: list[dict[str, Any]] = []

        for child in node.children:
            if child.type == "var_declaration":
                variables.extend(self._parse_var_declaration(child, source_code))

        return variables

    def _parse_var_declaration(
        self, node: Node, source_code: bytes
    ) -> list[dict[str, Any]]:
        """Parse a var declaration.

        Args:
            node: Var declaration node
            source_code: Original source code as bytes

        Returns:
            List of variable dictionaries
        """
        variables: list[dict[str, Any]] = []

        for child in node.children:
            if child.type == "var_spec":
                var_names: list[str] = []
                var_type = ""
                
                for spec_child in child.children:
                    if spec_child.type == "identifier":
                        var_names.append(self._get_node_text(spec_child, source_code))
                    elif spec_child.type in ("type_identifier", "qualified_type", 
                                            "pointer_type", "slice_type", "array_type",
                                            "map_type", "struct_type", "interface_type"):
                        var_type = self._get_node_text(spec_child, source_code)

                for var_name in var_names:
                    variables.append(
                        {
                            "type": "variable",
                            "name": var_name,
                            "var_type": var_type,
                            "line": child.start_point[0] + 1,
                            "end_line": child.end_point[0] + 1,
                        }
                    )

        return variables

    def _extract_type_declarations(
        self, node: Node, source_code: bytes
    ) -> list[dict[str, Any]]:
        """Extract type declarations including structs and interfaces.

        Args:
            node: Root node to search
            source_code: Original source code as bytes

        Returns:
            List of type declaration symbol dictionaries
        """
        type_declarations: list[dict[str, Any]] = []

        for child in node.children:
            if child.type == "type_declaration":
                type_declarations.extend(
                    self._parse_type_declaration(child, source_code)
                )

        return type_declarations

    def _parse_type_declaration(
        self, node: Node, source_code: bytes
    ) -> list[dict[str, Any]]:
        """Parse a type declaration.

        Args:
            node: Type declaration node
            source_code: Original source code as bytes

        Returns:
            List of type declaration dictionaries
        """
        type_decls: list[dict[str, Any]] = []

        for child in node.children:
            if child.type == "type_spec":
                type_name = ""
                type_kind = "type"
                fields: list[dict[str, Any]] = []
                methods: list[dict[str, Any]] = []

                for spec_child in child.children:
                    if spec_child.type == "type_identifier":
                        type_name = self._get_node_text(spec_child, source_code)
                    elif spec_child.type == "struct_type":
                        type_kind = "struct"
                        fields = self._extract_struct_fields(spec_child, source_code)
                    elif spec_child.type == "interface_type":
                        type_kind = "interface"
                        methods = self._extract_interface_methods(spec_child, source_code)

                type_decl: dict[str, Any] = {
                    "type": type_kind,
                    "name": type_name,
                    "line": child.start_point[0] + 1,
                    "end_line": child.end_point[0] + 1,
                }

                if type_kind == "struct":
                    type_decl["fields"] = fields
                elif type_kind == "interface":
                    type_decl["methods"] = methods

                type_decls.append(type_decl)

        return type_decls

    def _extract_struct_fields(
        self, node: Node, source_code: bytes
    ) -> list[dict[str, Any]]:
        """Extract fields from a struct type.

        Args:
            node: Struct type node
            source_code: Original source code as bytes

        Returns:
            List of field dictionaries
        """
        fields: list[dict[str, Any]] = []

        for child in node.children:
            if child.type == "field_declaration_list":
                for field_child in child.children:
                    if field_child.type == "field_declaration":
                        field_names: list[str] = []
                        field_type = ""
                        field_tag = ""

                        for field_item in field_child.children:
                            if field_item.type == "field_identifier":
                                field_names.append(
                                    self._get_node_text(field_item, source_code)
                                )
                            elif field_item.type in (
                                "type_identifier",
                                "qualified_type",
                                "pointer_type",
                                "slice_type",
                                "array_type",
                                "map_type",
                            ):
                                field_type = self._get_node_text(field_item, source_code)
                            elif field_item.type == "raw_string_literal":
                                field_tag = self._get_node_text(field_item, source_code)

                        # Handle embedded fields (no name)
                        if not field_names and field_type:
                            field_names = [field_type]

                        for field_name in field_names:
                            fields.append(
                                {
                                    "name": field_name,
                                    "field_type": field_type,
                                    "tag": field_tag,
                                    "line": field_child.start_point[0] + 1,
                                }
                            )

        return fields

    def _extract_interface_methods(
        self, node: Node, source_code: bytes
    ) -> list[dict[str, Any]]:
        """Extract methods from an interface type.

        Args:
            node: Interface type node
            source_code: Original source code as bytes

        Returns:
            List of method dictionaries
        """
        methods: list[dict[str, Any]] = []

        for child in node.children:
            if child.type == "interface_type":
                # Nested interface type, skip
                continue
            elif child.type == "method_spec":
                method_name = ""
                parameters: list[str] = []
                return_types: list[str] = []

                for method_child in child.children:
                    if method_child.type == "field_identifier":
                        method_name = self._get_node_text(method_child, source_code)
                    elif method_child.type == "parameter_list":
                        parameters = self._extract_parameters(method_child, source_code)
                    elif method_child.type in ("type_identifier", "parameter_list"):
                        # Return type can be in various forms
                        pass

                methods.append(
                    {
                        "name": method_name,
                        "parameters": parameters,
                        "return_types": return_types,
                        "line": child.start_point[0] + 1,
                    }
                )

        return methods

    def _extract_functions(self, node: Node, source_code: bytes) -> list[dict[str, Any]]:
        """Extract function declarations from the AST.

        Args:
            node: Root node to search
            source_code: Original source code as bytes

        Returns:
            List of function symbol dictionaries
        """
        functions: list[dict[str, Any]] = []

        for child in node.children:
            if child.type == "function_declaration":
                func_info = self._parse_function(child, source_code)
                functions.append(func_info)

        return functions

    def _parse_function(self, node: Node, source_code: bytes) -> dict[str, Any]:
        """Parse a function declaration.

        Args:
            node: Function declaration node
            source_code: Original source code as bytes

        Returns:
            Dictionary with function information
        """
        func_name = ""
        parameters: list[str] = []
        return_types: list[str] = []

        for child in node.children:
            if child.type == "identifier":
                func_name = self._get_node_text(child, source_code)
            elif child.type == "parameter_list":
                parameters = self._extract_parameters(child, source_code)
            elif child.type in ("type_identifier", "parameter_list"):
                # Return types
                if child.type == "parameter_list":
                    return_types = self._extract_parameters(child, source_code)
                else:
                    return_types = [self._get_node_text(child, source_code)]

        # Build signature
        params_str = ", ".join(parameters) if parameters else ""
        return_str = " " + ", ".join(return_types) if return_types else ""
        signature = f"func {func_name}({params_str}){return_str}"

        return {
            "type": "function",
            "name": func_name,
            "line": node.start_point[0] + 1,
            "end_line": node.end_point[0] + 1,
            "parameters": parameters,
            "return_types": return_types,
            "signature": signature,
        }

    def _extract_methods(self, node: Node, source_code: bytes) -> list[dict[str, Any]]:
        """Extract method declarations from the AST.

        Args:
            node: Root node to search
            source_code: Original source code as bytes

        Returns:
            List of method symbol dictionaries
        """
        methods: list[dict[str, Any]] = []

        for child in node.children:
            if child.type == "method_declaration":
                method_info = self._parse_method(child, source_code)
                methods.append(method_info)

        return methods

    def _parse_method(self, node: Node, source_code: bytes) -> dict[str, Any]:
        """Parse a method declaration.

        Args:
            node: Method declaration node
            source_code: Original source code as bytes

        Returns:
            Dictionary with method information
        """
        method_name = ""
        receiver = ""
        parameters: list[str] = []
        return_types: list[str] = []

        for child in node.children:
            if child.type == "parameter_list" and not receiver:
                # First parameter list is the receiver
                receiver_params = self._extract_parameters(child, source_code)
                receiver = receiver_params[0] if receiver_params else ""
            elif child.type == "field_identifier":
                method_name = self._get_node_text(child, source_code)
            elif child.type == "parameter_list" and receiver:
                # Second parameter list is the actual parameters
                parameters = self._extract_parameters(child, source_code)
            elif child.type in ("type_identifier", "qualified_type"):
                # Return type
                return_types = [self._get_node_text(child, source_code)]

        # Build signature
        params_str = ", ".join(parameters) if parameters else ""
        return_str = " " + ", ".join(return_types) if return_types else ""
        signature = f"func ({receiver}) {method_name}({params_str}){return_str}"

        return {
            "type": "method",
            "name": method_name,
            "receiver": receiver,
            "line": node.start_point[0] + 1,
            "end_line": node.end_point[0] + 1,
            "parameters": parameters,
            "return_types": return_types,
            "signature": signature,
        }

    def _extract_parameters(self, node: Node, source_code: bytes) -> list[str]:
        """Extract parameters from a parameter list.

        Args:
            node: Parameter list node
            source_code: Original source code as bytes

        Returns:
            List of parameter names or types
        """
        parameters: list[str] = []

        for child in node.children:
            if child.type == "parameter_declaration":
                param_names: list[str] = []
                param_type = ""

                for param_child in child.children:
                    if param_child.type == "identifier":
                        param_names.append(self._get_node_text(param_child, source_code))
                    elif param_child.type in (
                        "type_identifier",
                        "qualified_type",
                        "pointer_type",
                        "slice_type",
                        "array_type",
                        "map_type",
                        "variadic_parameter_declaration",
                    ):
                        param_type = self._get_node_text(param_child, source_code)

                if param_names:
                    for param_name in param_names:
                        parameters.append(f"{param_name} {param_type}" if param_type else param_name)
                elif param_type:
                    parameters.append(param_type)
            elif child.type == "variadic_parameter_declaration":
                # Handle variadic parameters
                param_text = self._get_node_text(child, source_code)
                parameters.append(param_text)

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
