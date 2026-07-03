"""C++ Tree-sitter parser implementation.

This module provides concrete implementation of C++ source code parsing
using tree-sitter and tree-sitter-cpp.
"""

from pathlib import Path
from typing import Any

from tree_sitter import Language, Node, Parser, Tree
from tree_sitter_cpp import language

from app.services.parser.parser_interface import ParseResult, ParserInterface


class CppTreeSitterParser(ParserInterface):
    """Parser for C++ source files using tree-sitter.

    This parser uses tree-sitter-cpp to parse C++ code and extract:
    - Namespaces
    - Classes (with methods, constructors, destructors)
    - Structs
    - Templates (class templates, function templates)
    - Enums (including enum classes)
    - Using statements (using declarations and directives)
    - Includes (#include directives)
    - Free functions (functions outside classes)
    """

    def __init__(self) -> None:
        """Initialize the C++ parser with tree-sitter language."""
        self._language = Language(language())
        self._parser = Parser(self._language)

    @property
    def language(self) -> str:
        """Return the language this parser handles."""
        return "C++"

    @property
    def supported_extensions(self) -> list[str]:
        """Return list of file extensions this parser supports."""
        return [".cpp", ".cc", ".cxx", ".c++", ".hpp", ".hh", ".hxx", ".h++", ".h"]

    def parse(self, file_path: Path) -> ParseResult:
        """Parse a C++ source file.

        Args:
            file_path: Path to the C++ source file

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
                    error_message="Syntax errors found in C++ code",
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

        # Extract using statements
        symbols.extend(self._extract_using_statements(node, source_code))

        # Extract namespaces
        symbols.extend(self._extract_namespaces(node, source_code))

        # Extract classes
        symbols.extend(self._extract_classes(node, source_code))

        # Extract structs
        symbols.extend(self._extract_structs(node, source_code))

        # Extract enums
        symbols.extend(self._extract_enums(node, source_code))

        # Extract templates
        symbols.extend(self._extract_templates(node, source_code))

        # Extract free functions
        symbols.extend(self._extract_free_functions(node, source_code))

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
                include_text = self._get_node_text(n, source_code)
                
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
            
            if n == node:
                for child in n.children:
                    find_includes(child)

        find_includes(node)
        return includes

    def _extract_using_statements(
        self, node: Node, source_code: bytes
    ) -> list[dict[str, Any]]:
        """Extract using statements from the AST.

        Args:
            node: Root node to search
            source_code: Original source code as bytes

        Returns:
            List of using statement symbol dictionaries
        """
        using_statements: list[dict[str, Any]] = []

        def find_using(n: Node) -> None:
            if n.type in ("using_declaration", "alias_declaration"):
                using_text = self._get_node_text(n, source_code)
                
                # Extract the name being used/aliased
                name = ""
                if n.type == "alias_declaration":
                    for child in n.children:
                        if child.type == "type_identifier":
                            name = self._get_node_text(child, source_code)
                            break
                else:
                    # For using declaration, get the qualified identifier
                    for child in n.children:
                        if child.type in ("qualified_identifier", "identifier"):
                            name = self._get_node_text(child, source_code)
                            break

                using_statements.append(
                    {
                        "type": "using",
                        "kind": n.type,
                        "name": name if name else using_text,
                        "declaration": using_text,
                        "line": n.start_point[0] + 1,
                        "end_line": n.end_point[0] + 1,
                    }
                )
            
            # Recursively search
            for child in n.children:
                find_using(child)

        find_using(node)
        return using_statements

    def _extract_namespaces(
        self, node: Node, source_code: bytes
    ) -> list[dict[str, Any]]:
        """Extract namespace definitions from the AST.

        Args:
            node: Root node to search
            source_code: Original source code as bytes

        Returns:
            List of namespace symbol dictionaries
        """
        namespaces: list[dict[str, Any]] = []

        def find_namespaces(n: Node) -> None:
            if n.type == "namespace_definition":
                namespace_name = "anonymous"
                
                # Find namespace name
                for child in n.children:
                    if child.type == "identifier":
                        namespace_name = self._get_node_text(child, source_code)
                        break

                namespaces.append(
                    {
                        "type": "namespace",
                        "name": namespace_name,
                        "line": n.start_point[0] + 1,
                        "end_line": n.end_point[0] + 1,
                    }
                )
            
            # Recursively search
            for child in n.children:
                find_namespaces(child)

        find_namespaces(node)
        return namespaces

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
            if n.type == "class_specifier":
                class_info = self._parse_class(n, source_code)
                classes.append(class_info)
            
            # Recursively search
            for child in n.children:
                find_classes(child)

        find_classes(node)
        return classes

    def _parse_class(self, node: Node, source_code: bytes) -> dict[str, Any]:
        """Parse a class definition node.

        Args:
            node: Class specifier node
            source_code: Original source code as bytes

        Returns:
            Dictionary with class information
        """
        class_name = "Unknown"
        
        # Find class name
        for child in node.children:
            if child.type == "type_identifier":
                class_name = self._get_node_text(child, source_code)
                break

        # Extract base classes
        base_classes: list[str] = []
        for child in node.children:
            if child.type == "base_class_clause":
                base_classes = self._extract_base_classes(child, source_code)
                break

        # Extract methods, constructors, destructors
        methods: list[dict[str, Any]] = []
        constructors: list[dict[str, Any]] = []
        destructors: list[dict[str, Any]] = []

        for child in node.children:
            if child.type == "field_declaration_list":
                for body_child in child.children:
                    if body_child.type == "function_definition":
                        method_info = self._parse_method(body_child, source_code, class_name)
                        
                        # Check if constructor, destructor, or regular method
                        if method_info["is_constructor"]:
                            constructors.append(method_info)
                        elif method_info["is_destructor"]:
                            destructors.append(method_info)
                        else:
                            methods.append(method_info)
                    elif body_child.type == "declaration":
                        # Method declaration (prototype)
                        method_decls = self._parse_method_declaration(
                            body_child, source_code, class_name
                        )
                        for method_decl in method_decls:
                            if method_decl["is_constructor"]:
                                constructors.append(method_decl)
                            elif method_decl["is_destructor"]:
                                destructors.append(method_decl)
                            else:
                                methods.append(method_decl)

        return {
            "type": "class",
            "name": class_name,
            "line": node.start_point[0] + 1,
            "end_line": node.end_point[0] + 1,
            "base_classes": base_classes,
            "methods": methods,
            "constructors": constructors,
            "destructors": destructors,
        }

    def _extract_base_classes(self, node: Node, source_code: bytes) -> list[str]:
        """Extract base class names from a base class clause.

        Args:
            node: Base class clause node
            source_code: Original source code as bytes

        Returns:
            List of base class names
        """
        base_classes: list[str] = []
        
        for child in node.children:
            if child.type in ("type_identifier", "qualified_identifier"):
                base_classes.append(self._get_node_text(child, source_code))

        return base_classes

    def _parse_method(
        self, node: Node, source_code: bytes, class_name: str
    ) -> dict[str, Any]:
        """Parse a method definition node.

        Args:
            node: Function definition node
            source_code: Original source code as bytes
            class_name: Name of the containing class

        Returns:
            Dictionary with method information
        """
        method_name = "Unknown"
        return_type = ""
        parameters: list[str] = []
        storage_class: list[str] = []
        is_virtual = False
        is_static = False
        is_const = False

        # Check for storage class specifiers
        for child in node.children:
            if child.type == "storage_class_specifier":
                spec = self._get_node_text(child, source_code)
                storage_class.append(spec)
                if spec == "static":
                    is_static = True
            elif child.type == "virtual_specifier":
                is_virtual = True
            elif child.type in ("primitive_type", "type_identifier"):
                return_type = self._get_node_text(child, source_code)
            elif child.type == "function_declarator":
                method_name, parameters, is_const = self._parse_function_declarator(
                    child, source_code
                )
            elif child.type == "qualified_identifier":
                # For out-of-class method definitions
                parts = self._get_node_text(child, source_code).split("::")
                if len(parts) > 1:
                    method_name = parts[-1]

        # Determine if constructor or destructor
        is_constructor = method_name == class_name
        is_destructor = method_name == f"~{class_name}" or method_name.startswith("~")

        # Build signature
        params_str = ", ".join(parameters) if parameters else ""
        const_str = " const" if is_const else ""
        return_str = f"{return_type} " if return_type and not is_constructor and not is_destructor else ""
        signature = f"{return_str}{method_name}({params_str}){const_str}"

        return {
            "type": "method",
            "name": method_name,
            "line": node.start_point[0] + 1,
            "end_line": node.end_point[0] + 1,
            "return_type": return_type,
            "parameters": parameters,
            "storage_class": storage_class,
            "is_virtual": is_virtual,
            "is_static": is_static,
            "is_const": is_const,
            "is_constructor": is_constructor,
            "is_destructor": is_destructor,
            "signature": signature,
        }

    def _parse_method_declaration(
        self, node: Node, source_code: bytes, class_name: str
    ) -> list[dict[str, Any]]:
        """Parse method declarations (prototypes) from a declaration node.

        Args:
            node: Declaration node
            source_code: Original source code as bytes
            class_name: Name of the containing class

        Returns:
            List of method declaration dictionaries
        """
        methods: list[dict[str, Any]] = []
        
        # Check if this is a function declaration
        has_function_declarator = False
        for child in node.children:
            if child.type in ("function_declarator", "pointer_declarator"):
                has_function_declarator = True
                break

        if not has_function_declarator:
            return methods

        method_name = "Unknown"
        return_type = ""
        parameters: list[str] = []
        storage_class: list[str] = []
        is_virtual = False
        is_static = False
        is_const = False

        for child in node.children:
            if child.type == "storage_class_specifier":
                spec = self._get_node_text(child, source_code)
                storage_class.append(spec)
                if spec == "static":
                    is_static = True
            elif child.type == "virtual_specifier":
                is_virtual = True
            elif child.type in ("primitive_type", "type_identifier", "qualified_identifier"):
                return_type = self._get_node_text(child, source_code)
            elif child.type == "function_declarator":
                method_name, parameters, is_const = self._parse_function_declarator(
                    child, source_code
                )

        # Determine if constructor or destructor
        is_constructor = method_name == class_name
        is_destructor = method_name == f"~{class_name}" or method_name.startswith("~")

        if method_name != "Unknown":
            params_str = ", ".join(parameters) if parameters else ""
            const_str = " const" if is_const else ""
            return_str = f"{return_type} " if return_type and not is_constructor and not is_destructor else ""
            signature = f"{return_str}{method_name}({params_str}){const_str}"

            methods.append(
                {
                    "type": "method",
                    "name": method_name,
                    "line": node.start_point[0] + 1,
                    "end_line": node.end_point[0] + 1,
                    "return_type": return_type,
                    "parameters": parameters,
                    "storage_class": storage_class,
                    "is_virtual": is_virtual,
                    "is_static": is_static,
                    "is_const": is_const,
                    "is_constructor": is_constructor,
                    "is_destructor": is_destructor,
                    "signature": signature,
                }
            )

        return methods

    def _parse_function_declarator(
        self, node: Node, source_code: bytes
    ) -> tuple[str, list[str], bool]:
        """Parse a function declarator to extract name, parameters, and const qualifier.

        Args:
            node: Function declarator node
            source_code: Original source code as bytes

        Returns:
            Tuple of (function_name, parameter_list, is_const)
        """
        func_name = "Unknown"
        parameters: list[str] = []
        is_const = False

        for child in node.children:
            if child.type in ("identifier", "field_identifier", "destructor_name"):
                func_name = self._get_node_text(child, source_code)
            elif child.type == "qualified_identifier":
                parts = self._get_node_text(child, source_code).split("::")
                func_name = parts[-1] if parts else "Unknown"
            elif child.type == "parameter_list":
                parameters = self._extract_parameters(child, source_code)
            elif child.type == "type_qualifier" and self._get_node_text(child, source_code) == "const":
                is_const = True

        return func_name, parameters, is_const

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
            elif child.type == "variadic_parameter_declaration":
                parameters.append("...")
            elif child.type == "optional_parameter_declaration":
                param_name = self._extract_parameter_name(child, source_code)
                if param_name:
                    parameters.append(param_name)

        return parameters

    def _extract_parameter_name(self, node: Node, source_code: bytes) -> str:
        """Extract parameter name from a parameter declaration.

        Args:
            node: Parameter declaration node
            source_code: Original source code as bytes

        Returns:
            Parameter name or empty string
        """
        for child in node.children:
            if child.type == "identifier":
                return self._get_node_text(child, source_code)
            elif child.type in ("pointer_declarator", "reference_declarator", "array_declarator"):
                for decl_child in child.children:
                    if decl_child.type == "identifier":
                        return self._get_node_text(decl_child, source_code)

        return ""

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
            if n.type == "struct_specifier":
                struct_name = None
                for child in n.children:
                    if child.type == "type_identifier":
                        struct_name = self._get_node_text(child, source_code)
                        break

                if struct_name:
                    structs.append(
                        {
                            "type": "struct",
                            "name": struct_name,
                            "line": n.start_point[0] + 1,
                            "end_line": n.end_point[0] + 1,
                        }
                    )
            
            for child in n.children:
                find_structs(child)

        find_structs(node)
        return structs

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
                enum_name = None
                is_class = False
                
                # Check for enum class
                for child in n.children:
                    if child.type == "class":
                        is_class = True
                    elif child.type == "type_identifier":
                        enum_name = self._get_node_text(child, source_code)

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
                        "is_class": is_class,
                        "line": n.start_point[0] + 1,
                        "end_line": n.end_point[0] + 1,
                        "constants": constants,
                    }
                )
            
            for child in n.children:
                find_enums(child)

        find_enums(node)
        return enums

    def _extract_templates(
        self, node: Node, source_code: bytes
    ) -> list[dict[str, Any]]:
        """Extract template definitions from the AST.

        Args:
            node: Root node to search
            source_code: Original source code as bytes

        Returns:
            List of template symbol dictionaries
        """
        templates: list[dict[str, Any]] = []

        def find_templates(n: Node) -> None:
            if n.type == "template_declaration":
                template_params: list[str] = []
                template_kind = "unknown"
                template_name = "Unknown"

                # Extract template parameters
                for child in n.children:
                    if child.type == "template_parameter_list":
                        template_params = self._extract_template_parameters(
                            child, source_code
                        )
                    elif child.type == "class_specifier":
                        template_kind = "class"
                        for class_child in child.children:
                            if class_child.type == "type_identifier":
                                template_name = self._get_node_text(
                                    class_child, source_code
                                )
                                break
                    elif child.type == "struct_specifier":
                        template_kind = "struct"
                        for struct_child in child.children:
                            if struct_child.type == "type_identifier":
                                template_name = self._get_node_text(
                                    struct_child, source_code
                                )
                                break
                    elif child.type == "function_definition":
                        template_kind = "function"
                        for func_child in child.children:
                            if func_child.type == "function_declarator":
                                template_name, _, _ = self._parse_function_declarator(
                                    func_child, source_code
                                )
                                break

                templates.append(
                    {
                        "type": "template",
                        "kind": template_kind,
                        "name": template_name,
                        "parameters": template_params,
                        "line": n.start_point[0] + 1,
                        "end_line": n.end_point[0] + 1,
                    }
                )
            
            for child in n.children:
                find_templates(child)

        find_templates(node)
        return templates

    def _extract_template_parameters(
        self, node: Node, source_code: bytes
    ) -> list[str]:
        """Extract template parameters from a template parameter list.

        Args:
            node: Template parameter list node
            source_code: Original source code as bytes

        Returns:
            List of template parameter names
        """
        params: list[str] = []

        for child in node.children:
            if child.type in ("type_parameter_declaration", "parameter_declaration"):
                for param_child in child.children:
                    if param_child.type == "type_identifier":
                        params.append(self._get_node_text(param_child, source_code))
                        break

        return params

    def _extract_free_functions(
        self, node: Node, source_code: bytes
    ) -> list[dict[str, Any]]:
        """Extract free function definitions from the AST.

        Args:
            node: Root node to search
            source_code: Original source code as bytes

        Returns:
            List of free function symbol dictionaries
        """
        functions: list[dict[str, Any]] = []

        # Only extract top-level functions (not inside classes)
        for child in node.children:
            if child.type == "function_definition":
                func_info = self._parse_free_function(child, source_code)
                functions.append(func_info)
            elif child.type == "template_declaration":
                # Skip templates as they're handled separately
                continue

        return functions

    def _parse_free_function(
        self, node: Node, source_code: bytes
    ) -> dict[str, Any]:
        """Parse a free function definition.

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
            if child.type == "storage_class_specifier":
                storage_class.append(self._get_node_text(child, source_code))
            elif child.type in ("primitive_type", "type_identifier"):
                return_type = self._get_node_text(child, source_code)
            elif child.type == "function_declarator":
                func_name, parameters, _ = self._parse_function_declarator(
                    child, source_code
                )

        # Build signature
        params_str = ", ".join(parameters) if parameters else ""
        signature = f"{return_type} {func_name}({params_str})"

        return {
            "type": "function",
            "name": func_name,
            "line": node.start_point[0] + 1,
            "end_line": node.end_point[0] + 1,
            "return_type": return_type,
            "parameters": parameters,
            "storage_class": storage_class,
            "signature": signature,
        }

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
