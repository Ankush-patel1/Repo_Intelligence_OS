"""Factory for creating language-specific parsers."""

from pathlib import Path

from app.services.parser.javascript_parser import JavaScriptTreeSitterParser
from app.services.parser.parser_interface import ParseResult, ParserInterface
from app.services.parser.python_parser import PythonTreeSitterParser
from app.services.parser.typescript_parser import TypeScriptTreeSitterParser

# Aliases for backward compatibility
PythonParser = PythonTreeSitterParser
JavaScriptParser = JavaScriptTreeSitterParser
TypeScriptParser = TypeScriptTreeSitterParser


class JavaParser(ParserInterface):
    """Parser for Java source files."""

    @property
    def language(self) -> str:
        return "Java"

    @property
    def supported_extensions(self) -> list[str]:
        return [".java"]

    def parse(self, file_path: Path) -> ParseResult:
        """Parse a Java file (placeholder implementation).

        Args:
            file_path: Path to Java file

        Returns:
            ParseResult with placeholder data
        """
        return ParseResult(
            file_path=str(file_path),
            language=self.language,
            success=True,
            error_message=None,
            parse_tree={"type": "compilation_unit", "placeholder": True},
            symbols=[],
        )


class GoParser(ParserInterface):
    """Parser for Go source files."""

    @property
    def language(self) -> str:
        return "Go"

    @property
    def supported_extensions(self) -> list[str]:
        return [".go"]

    def parse(self, file_path: Path) -> ParseResult:
        """Parse a Go file (placeholder implementation).

        Args:
            file_path: Path to Go file

        Returns:
            ParseResult with placeholder data
        """
        return ParseResult(
            file_path=str(file_path),
            language=self.language,
            success=True,
            error_message=None,
            parse_tree={"type": "source_file", "placeholder": True},
            symbols=[],
        )


class RustParser(ParserInterface):
    """Parser for Rust source files."""

    @property
    def language(self) -> str:
        return "Rust"

    @property
    def supported_extensions(self) -> list[str]:
        return [".rs"]

    def parse(self, file_path: Path) -> ParseResult:
        """Parse a Rust file (placeholder implementation).

        Args:
            file_path: Path to Rust file

        Returns:
            ParseResult with placeholder data
        """
        return ParseResult(
            file_path=str(file_path),
            language=self.language,
            success=True,
            error_message=None,
            parse_tree={"type": "source_file", "placeholder": True},
            symbols=[],
        )


class GenericParser(ParserInterface):
    """Generic parser for unsupported languages.

    Returns a failed parse result for languages without specific parsers.
    """

    @property
    def language(self) -> str:
        return "Unknown"

    @property
    def supported_extensions(self) -> list[str]:
        return []

    def parse(self, file_path: Path) -> ParseResult:
        """Return a failed parse result.

        Args:
            file_path: Path to file

        Returns:
            ParseResult indicating parsing is not supported
        """
        return ParseResult(
            file_path=str(file_path),
            language=self.language,
            success=False,
            error_message=f"No parser available for {file_path.suffix}",
            parse_tree=None,
            symbols=None,
        )


class ParserFactory:
    """Factory for creating language-specific parsers.

    Maintains a registry of available parsers and returns the appropriate
    parser based on file extension or language name.
    """

    def __init__(self) -> None:
        """Initialize the parser factory with available parsers."""
        self._parsers: dict[str, ParserInterface] = {
            "Python": PythonParser(),
            "JavaScript": JavaScriptParser(),
            "TypeScript": TypeScriptParser(),
            "Java": JavaParser(),
            "Go": GoParser(),
            "Rust": RustParser(),
        }

        # Build extension-to-parser mapping
        self._extension_map: dict[str, ParserInterface] = {}
        for parser in self._parsers.values():
            for ext in parser.supported_extensions:
                self._extension_map[ext] = parser

    def get_parser_by_language(self, language: str) -> ParserInterface:
        """Get a parser for a specific language.

        Args:
            language: Programming language name (e.g., "Python", "JavaScript")

        Returns:
            Parser instance for the language, or GenericParser if not found
        """
        return self._parsers.get(language, GenericParser())

    def get_parser_by_extension(self, extension: str) -> ParserInterface:
        """Get a parser based on file extension.

        Args:
            extension: File extension including the dot (e.g., ".py", ".js")

        Returns:
            Parser instance for the extension, or GenericParser if not found
        """
        extension_lower = extension.lower()
        return self._extension_map.get(extension_lower, GenericParser())

    def get_parser_by_path(self, file_path: Path) -> ParserInterface:
        """Get a parser based on file path.

        Args:
            file_path: Path to the file

        Returns:
            Parser instance for the file's extension
        """
        return self.get_parser_by_extension(file_path.suffix)

    def get_supported_languages(self) -> list[str]:
        """Get list of supported programming languages.

        Returns:
            List of language names that have parsers
        """
        return list(self._parsers.keys())

    def get_supported_extensions(self) -> list[str]:
        """Get list of supported file extensions.

        Returns:
            List of file extensions that can be parsed
        """
        return list(self._extension_map.keys())
