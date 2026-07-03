"""Test C parser integration with ParserFactory."""

from pathlib import Path

import pytest

from app.services.parser.parser_factory import ParserFactory


class TestCParserFactoryIntegration:
    """Test suite for C parser factory integration."""

    @pytest.fixture
    def factory(self):
        """Create a ParserFactory instance."""
        return ParserFactory()

    def test_get_c_parser_by_language(self, factory):
        """Test retrieving C parser by language name."""
        parser = factory.get_parser_by_language("C")
        assert parser.language == "C"
        assert ".c" in parser.supported_extensions
        assert ".h" in parser.supported_extensions

    def test_get_c_parser_by_extension_c(self, factory):
        """Test retrieving C parser by .c extension."""
        parser = factory.get_parser_by_extension(".c")
        assert parser.language == "C"

    def test_get_c_parser_by_extension_h(self, factory):
        """Test retrieving C parser by .h extension."""
        parser = factory.get_parser_by_extension(".h")
        assert parser.language == "C"

    def test_get_c_parser_by_path_c(self, factory):
        """Test retrieving C parser by .c file path."""
        path = Path("src/main.c")
        parser = factory.get_parser_by_path(path)
        assert parser.language == "C"

    def test_get_c_parser_by_path_h(self, factory):
        """Test retrieving C parser by .h file path."""
        path = Path("include/header.h")
        parser = factory.get_parser_by_path(path)
        assert parser.language == "C"

    def test_c_in_supported_languages(self, factory):
        """Test that C is in the list of supported languages."""
        supported = factory.get_supported_languages()
        assert "C" in supported

    def test_c_extensions_in_supported_extensions(self, factory):
        """Test that .c and .h are in the list of supported extensions."""
        supported = factory.get_supported_extensions()
        assert ".c" in supported
        assert ".h" in supported

    def test_c_parser_is_tree_sitter_implementation(self, factory):
        """Test that C parser is the tree-sitter implementation."""
        parser = factory.get_parser_by_language("C")
        assert parser.__class__.__name__ == "CTreeSitterParser"

    def test_c_parser_parse_method_exists(self, factory):
        """Test that C parser has parse method."""
        parser = factory.get_parser_by_language("C")
        assert hasattr(parser, "parse")
        assert callable(parser.parse)
