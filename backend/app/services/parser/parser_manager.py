"""Manager for coordinating parsing operations.

This module provides a high-level interface for parsing source code files,
handling parser selection and execution.
"""

from pathlib import Path

from app.services.indexing.language_detector import LanguageDetector
from app.services.parser.parser_factory import ParserFactory
from app.services.parser.parser_interface import ParseResult


class ParserManager:
    """Manages parsing operations across multiple languages.

    The ParserManager provides a unified interface for parsing source code files.
    It uses LanguageDetector to identify the file's language and ParserFactory
    to select the appropriate parser.
    """

    def __init__(self) -> None:
        """Initialize the parser manager with required dependencies."""
        self._language_detector = LanguageDetector()
        self._parser_factory = ParserFactory()

    def parse_file(self, file_path: str | Path) -> ParseResult:
        """Parse a source code file.

        This is the main entry point for parsing operations. It:
        1. Converts the path to a Path object
        2. Detects the file's programming language
        3. Selects the appropriate parser
        4. Parses the file and returns the result

        Args:
            file_path: Path to the source file (string or Path object)

        Returns:
            ParseResult containing parsed information or error details

        Example:
            >>> manager = ParserManager()
            >>> result = manager.parse_file("src/main.py")
            >>> if result.success:
            ...     print(f"Parsed {result.language} file successfully")
        """
        # Convert to Path object if necessary
        path = Path(file_path) if isinstance(file_path, str) else file_path

        # Detect the programming language
        language = self._language_detector.detect(path)

        # Get the appropriate parser
        parser = self._parser_factory.get_parser_by_language(language)

        # Parse the file
        return parser.parse(path)

    def parse_files(self, file_paths: list[str | Path]) -> list[ParseResult]:
        """Parse multiple source code files.

        Convenience method for parsing multiple files in sequence.

        Args:
            file_paths: List of file paths to parse

        Returns:
            List of ParseResult objects, one for each file

        Example:
            >>> manager = ParserManager()
            >>> results = manager.parse_files(["main.py", "utils.py"])
            >>> successful = [r for r in results if r.success]
        """
        return [self.parse_file(path) for path in file_paths]

    def get_supported_languages(self) -> list[str]:
        """Get list of languages that have parser support.

        Returns:
            List of programming language names with available parsers

        Example:
            >>> manager = ParserManager()
            >>> languages = manager.get_supported_languages()
            >>> print(f"Supported: {', '.join(languages)}")
        """
        return self._parser_factory.get_supported_languages()

    def get_supported_extensions(self) -> list[str]:
        """Get list of file extensions that can be parsed.

        Returns:
            List of file extensions (including the dot) that have parser support

        Example:
            >>> manager = ParserManager()
            >>> extensions = manager.get_supported_extensions()
            >>> print(f"Can parse: {', '.join(extensions)}")
        """
        return self._parser_factory.get_supported_extensions()

    def can_parse(self, file_path: str | Path) -> bool:
        """Check if a file can be parsed.

        Args:
            file_path: Path to check

        Returns:
            True if a parser is available for this file type

        Example:
            >>> manager = ParserManager()
            >>> if manager.can_parse("script.py"):
            ...     result = manager.parse_file("script.py")
        """
        path = Path(file_path) if isinstance(file_path, str) else file_path
        language = self._language_detector.detect(path)
        return language in self._parser_factory.get_supported_languages()
