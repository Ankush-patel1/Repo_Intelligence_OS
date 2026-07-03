"""Tree-sitter parser infrastructure.

This module provides a pluggable parser system for extracting structured
information from source code files across multiple programming languages.
"""

from app.services.parser.parser_interface import ParseResult, ParserInterface
from app.services.parser.parser_manager import ParserManager

__all__ = ["ParseResult", "ParserInterface", "ParserManager"]
