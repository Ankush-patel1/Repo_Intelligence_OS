"""C Tree-sitter parser implementation.

This module provides concrete implementation of C source code parsing
using tree-sitter and tree-sitter-c.
"""

from pathlib import Path
from typing import Any

from tree_sitter import Language, Node, Parser, Tree
from tree_sitter_c import language

from app.services.parser.parser_interface import ParseResult, ParserInterface


class CTreeSitterParser(ParserInterface):
    """Parser for C source files using tree-sitter.

    This parser uses tree-sitter-c to parse C code and extract:
    - Includes (#include directives)
    - Functions (function definitions and declarations)
    - Structs (structure definitions)
    - Enums (enumeration definitions)
    - Typedefs (type definitions)
    - Global variables
    - Macros (#define directives)
    """

    def __init__(self) -> None:
        """Initialize the C parser with tree-sitter language."""
        self._language = Language(language())
        self._parser = Parser(self._language)

    @property
    def language(self) -> str:
        """Return the language this parser handles."""
        return "C"

    @property
    def supported_extensions(self) -> list[str]:
        """Return list of file extensions this parser supports."""
        return [".c", ".h"]

    def parse(self, file_path: Path) -> ParseResult:
        """Parse a C source file.

        Args:
            file_path: Path to the C source file

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
                    error_message="Syntax errors found in C code",
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

        # Extract includes
        symbols.extend(self._extract_includes(node, source_code))

        # Extract macros
        symbols.extend(self._extract_macros(node, source_code))

        # Extract typedefs
        symbols.extend(self._extract_typedefs(node, source_code))

        # Extract structs
        symbols.extend(self._extract_structs(node, source_code))

        # Extract enums
        symbols.extend(self._extract_enums(node, source_code))

        # Extract functions
        symbols.extend(self._extract_functions(node, source_code))

        # Extract global variables
        symbols.extend(self._extract_global_variables(node, source_code))

        return symbols

    def _extract_includes(self, node: Node, source_code: bytes) -> list[dict[str, Any]]:
        """Extract #include directives from the AST.

        Args:
            node: Root node to search
            source_code: Original source code as bytes

        Returns:
            List of include symbol dictionaries
        """
        includes: list[dict[str, Any]] = []

        def find_includes(n: Node) -> None:
            if n.type == "preproc_include":
                # Get the full include text
                include_text = self._get_node_text(n, source_code)
                
                # Extract the path (between "" or <>)
                path = ""
                for child in n.children:
                    if child.type in ("string_literal", "system_lib_string"):
                        path = self._get_node_text(child, source_code)
                        break

                includes.append(
                    {
                        "type": "include",
                        "name": include_text,
                        "path": path,
                        "line": n.start_point[0] + 1,
                        "end_line": n.end_point[0] + 1,
                    }
                )
            
            # Only search top-level children for includes
            if n == node:
                for child in n.children:
                    find_includes(child)

        find_includes(node)
        return includes

    def _extract_macros(self, node: Node, source_code: bytes) -> list[dict[str, Any]]:
        """Extract #define macros from the AST.

        Args:
            node: Root node to search
            source_code: Original source code as bytes

        Returns:
            List of macro symbol dictionaries
        """
        macros: list[dict[str, Any]] = []

        def find_macros(n: Node) -> None:
            if n.type in ("preproc_def", "preproc_function_def"):
                # Find macro name
                macro_name = "Unknown"
                for child in n.children:
                    if child.type == "identifier":
                        macro_name = self._get_node_text(child, source_code)
                        break

                # Get the full macro text
                macro_text = self._get_node_text(n, source_code)

                # Extract parameters for function-like macros
                parameters: list[str] = []
                if n.type == "preproc_function_def":
                    for child in n.children:
                        if child.type == "preproc_params":
                            for param_child in child.children:
                                if param_child.type == "identifier":
                                    parameters.append(
                                        self._get_node_text(param_child, source_code)
                                    )

                macros.append(
                    {
                        "type": "macro",
                        "name": macro_name,
                        "definition": macro_text,
                        "parameters": parameters,
                        "is_function_like": n.type == "preproc_function_def",
                        "line": n.start_point[0] + 1,
                        "end_line": n.end_point[0] + 1,
                    }
                )
            
            # Only search top-level children for macros
            if n == node:
                for child in n.children:
                    find_macros(child)

        find_macros(node)
        return macros

    def _extract_typedefs(self, node: Node, source_code: bytes) -> list[dict[str, Any]]:
        """Extract typedef declarations from the AST.

        Args:
            node: Root node to search
            source_code: Original source code as bytes

        Returns:
            List of typedef symbol dictionaries
        """
        typedefs: list[dict[str, Any]] = []

        def find_typedefs(n: Node) -> None:
            if n.type == "type_definition":
                # Find the typedef name (usually the last identifier)
                typedef_name = "Unknown"
                base_type = ""
                
                for child in n.children:
                    if child.type == "type_identifier":
                        typedef_name = self._get_node_text(child, source_code)
                    elif child.type in ("struct_specifier", "enum_specifier", "union_specifier"):
                        base_type = self._get_node_text(child, source_code)
                    elif child.type == "primitive_type":
                        base_type = self._get_node_text(child, source_code)

                typedefs.append(
                    {
                        "type": "typedef",
                        "name": typedef_name,
                        "base_type": base_type,
                        "line": n.start_point[0] + 1,
                        "end_line": n.end_point[0] + 1,
                    }
                )
            
            # Recursively search children
            for child in n.children:
                find_typedefs(child)

        find_typedefs(node)
        return typedefs

    def _extract_structs(self, node: Node, source_code: bytes) -> list[dict[str, Any]]:
        """Extract struct definitions from the AST.

        Args:
            node: Root node to search
            source_code: Original source code as bytes

        Returns:
            List of struct symbol dictionaries
        """
        structs: list[dict[str, Any]] = []

        def find_structs(n: Node) -> None:
            # Look for struct_specifier at declaration level
            if n.type == "struct_specifier":
                # Only extract if it has a name (not anonymous)
                struct_name = None
                for child in n.children:
                    if child.type == "type_identifier":
                        struct_name = self._get_node_text(child, source_code)
                        break

                if struct_name:
                    # Extract fields
                    fields: list[dict[str, Any]] = []
                    for child in n.children:
                        if child.type == "field_declaration_list":
                            fields = self._extract_struct_fields(child, source_code)
                            break

                    structs.append(
                        {
                            "type": "struct",
                            "name": struct_name,
                            "line": n.start_point[0] + 1,
                            "end_line": n.end_point[0] + 1,
                            "fields": fields,
                        }
                    )
            
            # Recursively search children
            for child in n.children:
                find_structs(child)

        find_structs(node)
        return structs

    def _extract_struct_fields(
        self, node: Node, source_code: bytes
    ) -> list[dict[str, Any]]:
        """Extract fields from a struct field declaration list.

        Args:
            node: Field declaration list node
            source_code: Original source code as bytes

        Returns:
            List of field dictionaries
        """
        fields: list[dict[str, Any]] = []

        for child in node.children:
            if child.type == "field_declaration":
                # Extract field type
                field_type = ""
                field_names: list[str] = []

                for field_child in child.children:
                    if field_child.type in (
                        "primitive_type",
                        "type_identifier",
                        "sized_type_specifier",
                    ):
                        field_type = self._get_node_text(field_child, source_code)
                    elif field_child.type == "field_identifier":
                        field_names.append(self._get_node_text(field_child, source_code))
                    elif field_child.type in ("pointer_declarator", "array_declarator"):
                        # Handle pointer and array fields
                        for decl_child in field_child.children:
                            if decl_child.type == "field_identifier":
                                field_names.append(
                                    self._get_node_text(decl_child, source_code)
                                )

                # Create a field entry for each field name
                for field_name in field_names:
                    fields.append(
                        {
                            "name": field_name,
                            "field_type": field_type,
                            "line": child.start_point[0] + 1,
                        }
                    )

        return fields

    def _extract_enums(self, node: Node, source_code: bytes) -> list[dict[str, Any]]:
        """Extract enum definitions from the AST.

        Args:
            node: Root node to search
            source_code: Original source code as bytes

        Returns:
            List of enum symbol dictionaries
        """
        enums: list[dict[str, Any]] = []

        def find_enums(n: Node) -> None:
            if n.type == "enum_specifier":
                # Find enum name (may be anonymous)
                enum_name = None
                for child in n.children:
                    if child.type == "type_identifier":
                        enum_name = self._get_node_text(child, source_code)
                        break

                # Extract enum constants
                constants: list[str] = []
                for child in n.children:
                    if child.type == "enumerator_list":
                        for enum_child in child.children:
                            if enum_child.type == "enumerator":
                                for const_child in enum_child.children:
                                    if const_child.type == "identifier":
                                        constants.append(
                                            self._get_node_text(const_child, source_code)
                                        )
                                        break

                enums.append(
                    {
                        "type": "enum",
                        "name": enum_name if enum_name else "anonymous",
                        "line": n.start_point[0] + 1,
                        "end_line": n.end_point[0] + 1,
                        "constants": constants,
                    }
                )
            
            # Recursively search children
            for child in n.children:
                find_enums(child)

        find_enums(node)
        return enums

    def _extract_functions(self, node: Node, source_code: bytes) -> list[dict[str, Any]]:
        """Extract function definitions and declarations from the AST.

        Args:
            node: Root node to search
            source_code: Original source code as bytes

        Returns:
            List of function symbol dictionaries
        """
        functions: list[dict[str, Any]] = []

        def find_functions(n: Node) -> None:
            if n.type == "function_definition":
                func_info = self._parse_function_definition(n, source_code)
                functions.append(func_info)
            elif n.type == "declaration":
                # Check if this is a function declaration (prototype)
                func_decls = self._parse_function_declaration(n, source_code)
                functions.extend(func_decls)
            
            # Only search top-level for functions (not nested)
            if n == node:
                for child in n.children:
                    find_functions(child)

        find_functions(node)
        return functions

    def _parse_function_definition(
        self, node: Node, source_code: bytes
    ) -> dict[str, Any]:
        """Parse a function definition node.

        Args:
            node: Function definition node
            source_code: Original source code as bytes

        Returns:
            Dictionary with function information
        """
        func_name = "Unknown"
        return_type = ""
        parameters: list[str] = []
        storage_class: list[str] = []

        for child in node.children:
            # Extract storage class specifiers (static, extern, inline)
            if child.type == "storage_class_specifier":
                storage_class.append(self._get_node_text(child, source_code))
            # Extract return type
            elif child.type in ("primitive_type", "type_identifier", "sized_type_specifier"):
                return_type = self._get_node_text(child, source_code)
            # Extract function declarator
            elif child.type == "function_declarator":
                func_name, parameters = self._parse_function_declarator(
                    child, source_code
                )
            elif child.type == "pointer_declarator":
                # Handle pointer return types
                for ptr_child in child.children:
                    if ptr_child.type == "function_declarator":
                        func_name, parameters = self._parse_function_declarator(
                            ptr_child, source_code
                        )

        # Build signature
        params_str = ", ".join(parameters) if parameters else "void"
        storage_str = " ".join(storage_class) + " " if storage_class else ""
        signature = f"{storage_str}{return_type} {func_name}({params_str})"

        return {
            "type": "function",
            "name": func_name,
            "line": node.start_point[0] + 1,
            "end_line": node.end_point[0] + 1,
            "return_type": return_type,
            "parameters": parameters,
            "storage_class": storage_class,
            "signature": signature,
            "is_definition": True,
        }

    def _parse_function_declaration(
        self, node: Node, source_code: bytes
    ) -> list[dict[str, Any]]:
        """Parse function declarations (prototypes) from a declaration node.

        Args:
            node: Declaration node
            source_code: Original source code as bytes

        Returns:
            List of function declaration dictionaries
        """
        functions: list[dict[str, Any]] = []
        
        # Check if this declaration contains a function declarator
        has_function_declarator = False
        for child in node.children:
            if child.type in ("function_declarator", "pointer_declarator"):
                has_function_declarator = True
                break

        if not has_function_declarator:
            return functions

        func_name = "Unknown"
        return_type = ""
        parameters: list[str] = []
        storage_class: list[str] = []

        for child in node.children:
            if child.type == "storage_class_specifier":
                storage_class.append(self._get_node_text(child, source_code))
            elif child.type in ("primitive_type", "type_identifier", "sized_type_specifier"):
                return_type = self._get_node_text(child, source_code)
            elif child.type == "function_declarator":
                func_name, parameters = self._parse_function_declarator(
                    child, source_code
                )
            elif child.type == "pointer_declarator":
                for ptr_child in child.children:
                    if ptr_child.type == "function_declarator":
                        func_name, parameters = self._parse_function_declarator(
                            ptr_child, source_code
                        )

        if func_name != "Unknown":
            params_str = ", ".join(parameters) if parameters else "void"
            storage_str = " ".join(storage_class) + " " if storage_class else ""
            signature = f"{storage_str}{return_type} {func_name}({params_str})"

            functions.append(
                {
                    "type": "function",
                    "name": func_name,
                    "line": node.start_point[0] + 1,
                    "end_line": node.end_point[0] + 1,
                    "return_type": return_type,
                    "parameters": parameters,
                    "storage_class": storage_class,
                    "signature": signature,
                    "is_definition": False,
                }
            )

        return functions

    def _parse_function_declarator(
        self, node: Node, source_code: bytes
    ) -> tuple[str, list[str]]:
        """Parse a function declarator to extract name and parameters.

        Args:
            node: Function declarator node
            source_code: Original source code as bytes

        Returns:
            Tuple of (function_name, parameter_list)
        """
        func_name = "Unknown"
        parameters: list[str] = []

        for child in node.children:
            if child.type == "identifier":
                func_name = self._get_node_text(child, source_code)
            elif child.type == "parameter_list":
                parameters = self._extract_parameters(child, source_code)

        return func_name, parameters

    def _extract_parameters(self, node: Node, source_code: bytes) -> list[str]:
        """Extract parameters from a parameter list.

        Args:
            node: Parameter list node
            source_code: Original source code as bytes

        Returns:
            List of parameter names
        """
        parameters: list[str] = []

        for child in node.children:
            if child.type == "parameter_declaration":
                param_name = self._extract_parameter_name(child, source_code)
                if param_name:
                    parameters.append(param_name)
            elif child.type == "variadic_parameter":
                parameters.append("...")

        return parameters

    def _extract_parameter_name(self, node: Node, source_code: bytes) -> str:
        """Extract parameter name from a parameter declaration.

        Args:
            node: Parameter declaration node
            source_code: Original source code as bytes

        Returns:
            Parameter name or empty string
        """
        # Look for identifier in various declarator types
        for child in node.children:
            if child.type == "identifier":
                return self._get_node_text(child, source_code)
            elif child.type in ("pointer_declarator", "array_declarator"):
                for decl_child in child.children:
                    if decl_child.type == "identifier":
                        return self._get_node_text(decl_child, source_code)

        return ""

    def _extract_global_variables(
        self, node: Node, source_code: bytes
    ) -> list[dict[str, Any]]:
        """Extract global variable declarations from the AST.

        Args:
            node: Root node to search
            source_code: Original source code as bytes

        Returns:
            List of global variable symbol dictionaries
        """
        variables: list[dict[str, Any]] = []

        for child in node.children:
            if child.type == "declaration":
                # Check if it's a variable declaration (not a function)
                has_function_declarator = False
                for decl_child in child.children:
                    if decl_child.type in ("function_declarator", "pointer_declarator"):
                        # Check if pointer_declarator contains function_declarator
                        if decl_child.type == "pointer_declarator":
                            for ptr_child in decl_child.children:
                                if ptr_child.type == "function_declarator":
                                    has_function_declarator = True
                                    break
                        else:
                            has_function_declarator = True
                        break

                if has_function_declarator:
                    continue

                # Extract variable declarations
                var_type = ""
                storage_class: list[str] = []
                var_names: list[str] = []

                for decl_child in child.children:
                    if decl_child.type == "storage_class_specifier":
                        storage_class.append(self._get_node_text(decl_child, source_code))
                    elif decl_child.type in (
                        "primitive_type",
                        "type_identifier",
                        "sized_type_specifier",
                        "struct_specifier",
                        "enum_specifier",
                    ):
                        var_type = self._get_node_text(decl_child, source_code)
                    elif decl_child.type == "init_declarator":
                        var_name = self._extract_variable_name(decl_child, source_code)
                        if var_name:
                            var_names.append(var_name)
                    elif decl_child.type == "identifier":
                        var_names.append(self._get_node_text(decl_child, source_code))
                    elif decl_child.type in ("pointer_declarator", "array_declarator"):
                        var_name = self._extract_variable_name(decl_child, source_code)
                        if var_name:
                            var_names.append(var_name)

                # Create variable entries
                for var_name in var_names:
                    variables.append(
                        {
                            "type": "variable",
                            "name": var_name,
                            "line": child.start_point[0] + 1,
                            "end_line": child.end_point[0] + 1,
                            "var_type": var_type,
                            "storage_class": storage_class,
                        }
                    )

        return variables

    def _extract_variable_name(self, node: Node, source_code: bytes) -> str:
        """Extract variable name from a declarator.

        Args:
            node: Declarator node
            source_code: Original source code as bytes

        Returns:
            Variable name or empty string
        """
        for child in node.children:
            if child.type == "identifier":
                return self._get_node_text(child, source_code)
            elif child.type in ("pointer_declarator", "array_declarator"):
                return self._extract_variable_name(child, source_code)

        return ""

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
