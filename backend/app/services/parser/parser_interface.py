"""Abstract parser interface and data structures."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ParseResult:
    """Result of parsing a source code file.

    Attributes:
        file_path: Path to the file that was parsed
        language: Programming language of the file
        success: Whether parsing completed successfully
        error_message: Error message if parsing failed
        parse_tree: Abstract syntax tree (placeholder for now)
        symbols: Extracted symbols (placeholder for now)
    """

    file_path: str
    language: str
    success: bool
    error_message: str | None = None
    parse_tree: dict | None = None
    symbols: list[dict] | None = None


class ParserInterface(ABC):
    """Abstract base class for language-specific parsers.

    Each parser implementation should handle a specific programming language
    and extract structured information from source code files.
    """

    @property
    @abstractmethod
    def language(self) -> str:
        """Return the language this parser handles."""
        pass

    @property
    @abstractmethod
    def supported_extensions(self) -> list[str]:
        """Return list of file extensions this parser supports."""
        pass

    @abstractmethod
    def parse(self, file_path: Path) -> ParseResult:
        """Parse a source code file.

        Args:
            file_path: Path to the source file to parse

        Returns:
            ParseResult containing parsed information or error details
        """
        pass

    def can_parse(self, file_path: Path) -> bool:
        """Check if this parser can handle the given file.

        Args:
            file_path: Path to check

        Returns:
            True if this parser supports the file's extension
        """
        extension = file_path.suffix.lower()
        return extension in self.supported_extensions
