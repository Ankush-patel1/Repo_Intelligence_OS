"""Rust Tree-sitter parser implementation.

This module provides concrete implementation of Rust source code parsing
using tree-sitter and tree-sitter-rust.
"""

from pathlib import Path
from typing import Any

from tree_sitter import Language, Node, Parser, Tree
from tree_sitter_rust import language

from app.services.parser.parser_interface import ParseResult, ParserInterface


class RustTreeSitterParser(ParserInterface):
    """Parser for Rust source files using tree-sitter.

    This parser uses tree-sitter-rust to parse Rust code and extract:
    - Modules (mod declarations)
    - Use statements (imports)
    - Structs (struct definitions)
    - Enums (enum definitions)
    - Traits (trait definitions)
    - Impl blocks (trait implementations and inherent implementations)
    - Functions (free functions and associated functions)
    - Constants (const declarations)
    - Macros (macro definitions and invocations)
    """

    def __init__(self) -> None:
        """Initialize the Rust parser with tree-sitter language."""
        self._language = Language(language())
        self._parser = Parser(self._language)

    @property
    def language(self) -> str:
        """Return the language this parser handles."""
        return "Rust"

    @property
    def supported_extensions(self) -> list[str]:
        """Return list of file extensions this parser supports."""
        return [".rs"]

    def parse(self, file_path: Path) -> ParseResult:
        """Parse a Rust source file.

        Args:
            file_path: Path to the Rust source file

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
                    error_message="Syntax errors found in Rust code",
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

        # Extract modules
        symbols.extend(self._extract_modules(node, source_code))

        # Extract use statements
        symbols.extend(self._extract_use_statements(node, source_code))

        # Extract constants
        symbols.extend(self._extract_constants(node, source_code))

        # Extract structs
        symbols.extend(self._extract_structs(node, source_code))

        # Extract enums
        symbols.extend(self._extract_enums(node, source_code))

        # Extract traits
        symbols.extend(self._extract_traits(node, source_code))

        # Extract impl blocks
        symbols.extend(self._extract_impl_blocks(node, source_code))

        # Extract functions
        symbols.extend(self._extract_functions(node, source_code))

        # Extract macros
        symbols.extend(self._extract_macros(node, source_code))

        return symbols

    def _extract_modules(self, node: Node, source_code: bytes) -> list[dict[str, Any]]:
        """Extract module declarations from the AST.

        Args:
            node: Root node to search
            source_code: Original source code as bytes

        Returns:
            List of module symbol dictionaries
        """
        modules: list[dict[str, Any]] = []

        def find_modules(n: Node) -> None:
            if n.type == "mod_item":
                mod_name = ""
                is_inline = False

                for child in n.children:
                    if child.type == "identifier":
                        mod_name = self._get_node_text(child, source_code)
                    elif child.type == "declaration_list":
                        is_inline = True

                modules.append(
                    {
                        "type": "module",
                        "name": mod_name,
                        "is_inline": is_inline,
                        "line": n.start_point[0] + 1,
                        "end_line": n.end_point[0] + 1,
                    }
                )

            # Recursively search children
            for child in n.children:
                find_modules(child)

        find_modules(node)
        return modules

    def _extract_use_statements(
        self, node: Node, source_code: bytes
    ) -> list[dict[str, Any]]:
        """Extract use statements from the AST.

        Args:
            node: Root node to search
            source_code: Original source code as bytes

        Returns:
            List of use statement symbol dictionaries
        """
        use_statements: list[dict[str, Any]] = []

        def find_use(n: Node) -> None:
            if n.type == "use_declaration":
                use_path = ""
                
                for child in n.children:
                    if child.type in ("use_clause", "scoped_use_list", "use_as_clause",
                                     "use_list", "use_wildcard", "scoped_identifier", "identifier"):
                        use_path = self._get_node_text(child, source_code)
                        break

                use_statements.append(
                    {
                        "type": "use",
                        "path": use_path,
                        "line": n.start_point[0] + 1,
                        "end_line": n.end_point[0] + 1,
                    }
                )

            # Recursively search children
            for child in n.children:
                find_use(child)

        find_use(node)
        return use_statements

    def _extract_constants(self, node: Node, source_code: bytes) -> list[dict[str, Any]]:
        """Extract constant declarations from the AST.

        Args:
            node: Root node to search
            source_code: Original source code as bytes

        Returns:
            List of constant symbol dictionaries
        """
        constants: list[dict[str, Any]] = []

        def find_constants(n: Node) -> None:
            if n.type == "const_item":
                const_name = ""
                const_type = ""

                for child in n.children:
                    if child.type == "identifier":
                        const_name = self._get_node_text(child, source_code)
                    elif child.type in ("type_identifier", "primitive_type", "generic_type",
                                       "reference_type", "array_type"):
                        const_type = self._get_node_text(child, source_code)

                constants.append(
                    {
                        "type": "constant",
                        "name": const_name,
                        "const_type": const_type,
                        "line": n.start_point[0] + 1,
                        "end_line": n.end_point[0] + 1,
                    }
                )

            # Recursively search children
            for child in n.children:
                find_constants(child)

        find_constants(node)
        return constants

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
            if n.type == "struct_item":
                struct_info = self._parse_struct(n, source_code)
                structs.append(struct_info)

            # Recursively search children
            for child in n.children:
                find_structs(child)

        find_structs(node)
        return structs

    def _parse_struct(self, node: Node, source_code: bytes) -> dict[str, Any]:
        """Parse a struct definition.

        Args:
            node: Struct item node
            source_code: Original source code as bytes

        Returns:
            Dictionary with struct information
        """
        struct_name = ""
        fields: list[dict[str, Any]] = []
        is_tuple_struct = False

        for child in node.children:
            if child.type == "type_identifier":
                struct_name = self._get_node_text(child, source_code)
            elif child.type == "field_declaration_list":
                fields = self._extract_struct_fields(child, source_code)
            elif child.type == "ordered_field_declaration_list":
                is_tuple_struct = True
                fields = self._extract_tuple_struct_fields(child, source_code)

        return {
            "type": "struct",
            "name": struct_name,
            "is_tuple_struct": is_tuple_struct,
            "fields": fields,
            "line": node.start_point[0] + 1,
            "end_line": node.end_point[0] + 1,
        }

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
                field_name = ""
                field_type = ""

                for field_child in child.children:
                    if field_child.type == "field_identifier":
                        field_name = self._get_node_text(field_child, source_code)
                    elif field_child.type in ("type_identifier", "primitive_type",
                                             "generic_type", "reference_type", "array_type"):
                        field_type = self._get_node_text(field_child, source_code)

                fields.append(
                    {
                        "name": field_name,
                        "field_type": field_type,
                        "line": child.start_point[0] + 1,
                    }
                )

        return fields

    def _extract_tuple_struct_fields(
        self, node: Node, source_code: bytes
    ) -> list[dict[str, Any]]:
        """Extract fields from a tuple struct.

        Args:
            node: Ordered field declaration list node
            source_code: Original source code as bytes

        Returns:
            List of field dictionaries
        """
        fields: list[dict[str, Any]] = []
        field_index = 0

        for child in node.children:
            if child.type in ("type_identifier", "primitive_type", "generic_type",
                             "reference_type", "array_type"):
                field_type = self._get_node_text(child, source_code)
                fields.append(
                    {
                        "name": f"field_{field_index}",
                        "field_type": field_type,
                        "line": child.start_point[0] + 1,
                    }
                )
                field_index += 1

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
            if n.type == "enum_item":
                enum_info = self._parse_enum(n, source_code)
                enums.append(enum_info)

            # Recursively search children
            for child in n.children:
                find_enums(child)

        find_enums(node)
        return enums

    def _parse_enum(self, node: Node, source_code: bytes) -> dict[str, Any]:
        """Parse an enum definition.

        Args:
            node: Enum item node
            source_code: Original source code as bytes

        Returns:
            Dictionary with enum information
        """
        enum_name = ""
        variants: list[str] = []

        for child in node.children:
            if child.type == "type_identifier":
                enum_name = self._get_node_text(child, source_code)
            elif child.type == "enum_variant_list":
                for variant_child in child.children:
                    if variant_child.type == "enum_variant":
                        for variant_part in variant_child.children:
                            if variant_part.type == "identifier":
                                variants.append(
                                    self._get_node_text(variant_part, source_code)
                                )
                                break

        return {
            "type": "enum",
            "name": enum_name,
            "variants": variants,
            "line": node.start_point[0] + 1,
            "end_line": node.end_point[0] + 1,
        }

    def _extract_traits(self, node: Node, source_code: bytes) -> list[dict[str, Any]]:
        """Extract trait definitions from the AST.

        Args:
            node: Root node to search
            source_code: Original source code as bytes

        Returns:
            List of trait symbol dictionaries
        """
        traits: list[dict[str, Any]] = []

        def find_traits(n: Node) -> None:
            if n.type == "trait_item":
                trait_info = self._parse_trait(n, source_code)
                traits.append(trait_info)

            # Recursively search children
            for child in n.children:
                find_traits(child)

        find_traits(node)
        return traits

    def _parse_trait(self, node: Node, source_code: bytes) -> dict[str, Any]:
        """Parse a trait definition.

        Args:
            node: Trait item node
            source_code: Original source code as bytes

        Returns:
            Dictionary with trait information
        """
        trait_name = ""
        methods: list[str] = []

        for child in node.children:
            if child.type == "type_identifier":
                trait_name = self._get_node_text(child, source_code)
            elif child.type == "declaration_list":
                for method_child in child.children:
                    if method_child.type in ("function_signature_item", "function_item"):
                        for func_part in method_child.children:
                            if func_part.type == "identifier":
                                methods.append(self._get_node_text(func_part, source_code))
                                break

        return {
            "type": "trait",
            "name": trait_name,
            "methods": methods,
            "line": node.start_point[0] + 1,
            "end_line": node.end_point[0] + 1,
        }

    def _extract_impl_blocks(
        self, node: Node, source_code: bytes
    ) -> list[dict[str, Any]]:
        """Extract impl blocks from the AST.

        Args:
            node: Root node to search
            source_code: Original source code as bytes

        Returns:
            List of impl block symbol dictionaries
        """
        impl_blocks: list[dict[str, Any]] = []

        def find_impl(n: Node) -> None:
            if n.type == "impl_item":
                impl_info = self._parse_impl(n, source_code)
                impl_blocks.append(impl_info)

            # Recursively search children
            for child in n.children:
                find_impl(child)

        find_impl(node)
        return impl_blocks

    def _parse_impl(self, node: Node, source_code: bytes) -> dict[str, Any]:
        """Parse an impl block.

        Args:
            node: Impl item node
            source_code: Original source code as bytes

        Returns:
            Dictionary with impl block information
        """
        impl_type = ""
        impl_trait = ""
        methods: list[str] = []
        is_trait_impl = False

        # Check for trait implementation vs inherent implementation
        type_count = 0
        for child in node.children:
            if child.type == "type_identifier":
                type_count += 1
                if type_count == 1:
                    if is_trait_impl:
                        impl_trait = self._get_node_text(child, source_code)
                    else:
                        impl_type = self._get_node_text(child, source_code)
                elif type_count == 2:
                    impl_type = self._get_node_text(child, source_code)
            elif child.type == "for" or (child.type == "identifier" and self._get_node_text(child, source_code) == "for"):
                is_trait_impl = True
                # Previous type_identifier was the trait
                impl_trait = impl_type
                impl_type = ""
            elif child.type == "declaration_list":
                for method_child in child.children:
                    if method_child.type == "function_item":
                        for func_part in method_child.children:
                            if func_part.type == "identifier":
                                methods.append(self._get_node_text(func_part, source_code))
                                break

        return {
            "type": "impl",
            "impl_type": impl_type,
            "trait": impl_trait if is_trait_impl else None,
            "is_trait_impl": is_trait_impl,
            "methods": methods,
            "line": node.start_point[0] + 1,
            "end_line": node.end_point[0] + 1,
        }

    def _extract_functions(self, node: Node, source_code: bytes) -> list[dict[str, Any]]:
        """Extract function definitions from the AST.

        Args:
            node: Root node to search
            source_code: Original source code as bytes

        Returns:
            List of function symbol dictionaries
        """
        functions: list[dict[str, Any]] = []

        # Only extract top-level functions (not inside impl blocks)
        for child in node.children:
            if child.type == "function_item":
                func_info = self._parse_function(child, source_code)
                functions.append(func_info)

        return functions

    def _parse_function(self, node: Node, source_code: bytes) -> dict[str, Any]:
        """Parse a function definition.

        Args:
            node: Function item node
            source_code: Original source code as bytes

        Returns:
            Dictionary with function information
        """
        func_name = ""
        parameters: list[str] = []
        return_type = ""
        is_async = False
        is_unsafe = False
        is_pub = False

        for child in node.children:
            if child.type == "identifier":
                func_name = self._get_node_text(child, source_code)
            elif child.type == "parameters":
                parameters = self._extract_parameters(child, source_code)
            elif child.type in ("type_identifier", "primitive_type", "generic_type",
                               "reference_type", "tuple_type", "unit_type"):
                return_type = self._get_node_text(child, source_code)
            elif child.type == "async":
                is_async = True
            elif child.type == "unsafe":
                is_unsafe = True
            elif child.type == "visibility_modifier":
                is_pub = True

        # Build signature
        params_str = ", ".join(parameters) if parameters else ""
        return_str = f" -> {return_type}" if return_type else ""
        modifiers = []
        if is_pub:
            modifiers.append("pub")
        if is_async:
            modifiers.append("async")
        if is_unsafe:
            modifiers.append("unsafe")
        mod_str = " ".join(modifiers) + " " if modifiers else ""
        signature = f"{mod_str}fn {func_name}({params_str}){return_str}"

        return {
            "type": "function",
            "name": func_name,
            "parameters": parameters,
            "return_type": return_type,
            "is_async": is_async,
            "is_unsafe": is_unsafe,
            "is_pub": is_pub,
            "signature": signature,
            "line": node.start_point[0] + 1,
            "end_line": node.end_point[0] + 1,
        }

    def _extract_parameters(self, node: Node, source_code: bytes) -> list[str]:
        """Extract parameters from a parameter list.

        Args:
            node: Parameters node
            source_code: Original source code as bytes

        Returns:
            List of parameter strings
        """
        parameters: list[str] = []

        for child in node.children:
            if child.type == "parameter":
                param_name = ""
                param_type = ""

                for param_child in child.children:
                    if param_child.type == "identifier":
                        param_name = self._get_node_text(param_child, source_code)
                    elif param_child.type in ("type_identifier", "primitive_type",
                                             "generic_type", "reference_type", "tuple_type"):
                        param_type = self._get_node_text(param_child, source_code)

                if param_name and param_type:
                    parameters.append(f"{param_name}: {param_type}")
                elif param_type:
                    parameters.append(param_type)
            elif child.type == "self_parameter":
                parameters.append(self._get_node_text(child, source_code))

        return parameters

    def _extract_macros(self, node: Node, source_code: bytes) -> list[dict[str, Any]]:
        """Extract macro definitions from the AST.

        Args:
            node: Root node to search
            source_code: Original source code as bytes

        Returns:
            List of macro symbol dictionaries
        """
        macros: list[dict[str, Any]] = []

        def find_macros(n: Node) -> None:
            if n.type == "macro_definition":
                macro_name = ""

                for child in n.children:
                    if child.type == "identifier":
                        macro_name = self._get_node_text(child, source_code)
                        break

                macros.append(
                    {
                        "type": "macro",
                        "name": macro_name,
                        "line": n.start_point[0] + 1,
                        "end_line": n.end_point[0] + 1,
                    }
                )

            # Recursively search children
            for child in n.children:
                find_macros(child)

        find_macros(node)
        return macros

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
