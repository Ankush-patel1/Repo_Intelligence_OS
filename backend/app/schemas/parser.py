"""Parser schemas for storing parsed metadata.

These schemas define the structure for storing parsed information from source code
files. They store only metadata - no source code content.
"""

import uuid
from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class ImportReference(BaseModel):
    """Reference to an import statement."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    import_kind: Literal["import", "from_import", "namespace"] = Field(
        description="Type of import statement"
    )
    module_path: str = Field(description="Path of the imported module")
    imported_names: list[str] = Field(
        default_factory=list, description="Names imported from the module"
    )
    alias: str | None = Field(default=None, description="Alias for the import if any")
    line_number: int = Field(description="Line number where import appears")
    line_end: int = Field(description="Ending line number of import statement")


class FunctionParameter(BaseModel):
    """Parameter of a function or method."""

    model_config = ConfigDict(from_attributes=True)

    name: str = Field(description="Name of the parameter")
    type_annotation: str | None = Field(
        default=None, description="Type annotation if available"
    )
    default_value: str | None = Field(
        default=None, description="Default value if any"
    )
    is_optional: bool = Field(default=False, description="Whether parameter is optional")
    is_variadic: bool = Field(default=False, description="Whether parameter is variadic (...args)")


class FunctionReference(BaseModel):
    """Reference to a function or method."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    name: str = Field(description="Name of the function")
    function_kind: Literal[
        "function",
        "method",
        "static_method",
        "class_method",
        "arrow_function",
        "async_function",
        "generator",
        "property_getter",
        "property_setter",
        "constructor",
    ] = Field(default="function", description="Type of function")
    parameters: list[FunctionParameter] = Field(
        default_factory=list, description="Function parameters"
    )
    return_type: str | None = Field(
        default=None, description="Return type annotation if available"
    )
    is_async: bool = Field(default=False, description="Whether function is async")
    is_generator: bool = Field(default=False, description="Whether function is a generator")
    decorators: list[str] = Field(
        default_factory=list, description="Decorators applied to the function"
    )
    line_number: int = Field(description="Starting line number")
    line_end: int = Field(description="Ending line number")
    docstring: str | None = Field(default=None, description="Function docstring if available")


class ClassReference(BaseModel):
    """Reference to a class."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    name: str = Field(description="Name of the class")
    class_kind: Literal["class", "abstract_class", "interface", "enum", "mixin"] = Field(
        default="class", description="Type of class-like structure"
    )
    type_parameters: str | None = Field(
        default=None, description="Type parameters (generics) if any"
    )
    base_classes: list[str] = Field(
        default_factory=list, description="Base classes (inheritance)"
    )
    decorators: list[str] = Field(
        default_factory=list, description="Decorators applied to the class"
    )
    methods: list[FunctionReference] = Field(
        default_factory=list, description="Methods defined in the class"
    )
    class_fields: list[dict[str, Any]] = Field(
        default_factory=list, description="Class-level fields and properties"
    )
    line_number: int = Field(description="Starting line number")
    line_end: int = Field(description="Ending line number")
    docstring: str | None = Field(default=None, description="Class docstring if available")


class ParsedSymbol(BaseModel):
    """Parsed symbol from source code."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    symbol_type: Literal[
        "function",
        "class",
        "interface",
        "type_alias",
        "enum",
        "variable",
        "constant",
        "import",
        "export",
    ] = Field(description="Type of symbol")
    name: str = Field(description="Name of the symbol")
    language: str = Field(description="Programming language of the symbol")
    namespace: str | None = Field(
        default=None, description="Namespace/scope where symbol is defined"
    )
    data: dict[str, Any] = Field(
        default_factory=dict,
        description="Symbol-specific data (function details, class details, etc.)",
    )
    line_number: int = Field(description="Starting line number")
    line_end: int = Field(description="Ending line number")
    docstring: str | None = Field(default=None, description="Symbol docstring if available")
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata (access modifiers, visibility, etc.)",
    )


class ParsedFile(BaseModel):
    """Parsed metadata for a source code file."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    file_path: str = Field(description="Path to the source file")
    absolute_path: str = Field(description="Absolute path to the source file")
    language: str = Field(description="Programming language of the file")
    parse_success: bool = Field(description="Whether parsing was successful")
    error_message: str | None = Field(
        default=None, description="Error message if parsing failed"
    )

    # Parsed content metadata
    imports: list[ImportReference] = Field(
        default_factory=list, description="Import statements in the file"
    )
    exports: list[ParsedSymbol] = Field(
        default_factory=list, description="Export statements in the file"
    )
    functions: list[FunctionReference] = Field(
        default_factory=list, description="Functions defined in the file"
    )
    classes: list[ClassReference] = Field(
        default_factory=list, description="Classes defined in the file"
    )
    symbols: list[ParsedSymbol] = Field(
        default_factory=list, description="All symbols found in the file"
    )

    # File metadata (no source code)
    file_size_bytes: int = Field(description="Size of the file in bytes")
    line_count: int = Field(description="Number of lines in the file")
    sha256_hash: str = Field(description="SHA256 hash of the file content")
    is_binary: bool = Field(default=False, description="Whether file is binary")

    # Parse metadata
    parse_tree_summary: dict[str, Any] = Field(
        default_factory=dict, description="Summary of the parse tree structure"
    )
    parse_duration_ms: int | None = Field(
        default=None, description="Time taken to parse the file in milliseconds"
    )
    parser_version: str | None = Field(
        default=None, description="Version of the parser used"
    )

    # Timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    # Relationships
    repository_id: uuid.UUID | None = Field(
        default=None, description="ID of the repository this file belongs to"
    )
    repository_file_id: uuid.UUID | None = Field(
        default=None, description="ID of the RepositoryFile this parse belongs to"
    )


class ParseResultSummary(BaseModel):
    """Summary of parsing results for a file."""

    model_config = ConfigDict(from_attributes=True)

    file_path: str = Field(description="Path to the source file")
    language: str = Field(description="Programming language")
    parse_success: bool = Field(description="Whether parsing was successful")
    symbols_count: int = Field(description="Total number of symbols found")
    imports_count: int = Field(description="Number of import statements")
    exports_count: int = Field(description="Number of export statements")
    functions_count: int = Field(description="Number of functions")
    classes_count: int = Field(description="Number of classes")
    parse_duration_ms: int | None = Field(
        default=None, description="Time taken to parse in milliseconds"
    )


class BatchParseResult(BaseModel):
    """Results of parsing multiple files."""

    model_config = ConfigDict(from_attributes=True)

    total_files: int = Field(description="Total number of files attempted to parse")
    successful_parses: int = Field(description="Number of successful parses")
    failed_parses: int = Field(description="Number of failed parses")
    parse_results: list[ParseResultSummary] = Field(
        default_factory=list, description="Summary of each file parse"
    )
    total_duration_ms: int = Field(description="Total time taken for batch parse")


# Helper schemas for specific languages
class PythonParsedSymbol(BaseModel):
    """Python-specific symbol data."""

    model_config = ConfigDict(from_attributes=True)

    is_async: bool = Field(default=False, description="Whether symbol is async")
    decorators: list[str] = Field(
        default_factory=list, description="Decorators applied"
    )
    type_hints: dict[str, str] = Field(
        default_factory=dict, description="Type hints for parameters and return"
    )


class TypeScriptParsedSymbol(BaseModel):
    """TypeScript-specific symbol data."""

    model_config = ConfigDict(from_attributes=True)

    type_annotations: dict[str, str] = Field(
        default_factory=dict, description="Type annotations"
    )
    generic_parameters: list[str] = Field(
        default_factory=list, description="Generic type parameters"
    )
    access_modifier: Literal["public", "private", "protected", "default"] | None = Field(
        default=None, description="Access modifier"
    )
    is_optional: bool = Field(default=False, description="Whether symbol is optional")
    is_readonly: bool = Field(default=False, description="Whether symbol is readonly")


class JavaScriptParsedSymbol(BaseModel):
    """JavaScript-specific symbol data."""

    model_config = ConfigDict(from_attributes=True)

    is_arrow: bool = Field(default=False, description="Whether function is arrow function")
    is_exported: bool = Field(default=False, description="Whether symbol is exported")
    module_type: Literal["esm", "cjs", "umd", "iife"] | None = Field(
        default=None, description="Module type if applicable"
    )
    jsx_element: bool = Field(default=False, description="Whether symbol is a JSX element")


# Schema for storing parse results in database
class ParsedFileCreate(BaseModel):
    """Schema for creating a ParsedFile record."""

    file_path: str
    absolute_path: str
    language: str
    parse_success: bool
    error_message: str | None = None
    file_size_bytes: int
    line_count: int
    sha256_hash: str
    is_binary: bool = False
    repository_id: uuid.UUID | None = None
    repository_file_id: uuid.UUID | None = None
    parse_tree_summary: dict[str, Any] = Field(default_factory=dict)
    parse_duration_ms: int | None = None
    parser_version: str | None = None


class ParsedFileUpdate(BaseModel):
    """Schema for updating a ParsedFile record."""

    parse_success: bool | None = None
    error_message: str | None = None
    parse_tree_summary: dict[str, Any] | None = None
    parse_duration_ms: int | None = None
    parser_version: str | None = None
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ParsedFileResponse(BaseModel):
    """Response schema for ParsedFile API."""

    id: uuid.UUID
    file_path: str
    absolute_path: str
    language: str
    parse_success: bool
    error_message: str | None
    file_size_bytes: int
    line_count: int
    sha256_hash: str
    is_binary: bool
    symbols_count: int
    imports_count: int
    exports_count: int
    functions_count: int
    classes_count: int
    created_at: datetime
    updated_at: datetime
    repository_id: uuid.UUID | None
    repository_file_id: uuid.UUID | None


# Export all schemas
__all__ = [
    "ImportReference",
    "FunctionParameter",
    "FunctionReference",
    "ClassReference",
    "ParsedSymbol",
    "ParsedFile",
    "ParseResultSummary",
    "BatchParseResult",
    "PythonParsedSymbol",
    "TypeScriptParsedSymbol",
    "JavaScriptParsedSymbol",
    "ParsedFileCreate",
    "ParsedFileUpdate",
    "ParsedFileResponse",
]
