"""Test Go parser integration with ParserFactory."""

from pathlib import Path

import pytest

from app.services.parser.parser_factory import ParserFactory


class TestGoParserFactoryIntegration:
    """Test suite for Go parser factory integration."""

    @pytest.fixture
    def factory(self):
        """Create a ParserFactory instance."""
        return ParserFactory()

    def test_get_go_parser_by_language(self, factory):
        """Test retrieving Go parser by language name."""
        parser = factory.get_parser_by_language("Go")
        assert parser.language == "Go"
        assert ".go" in parser.supported_extensions

    def test_get_go_parser_by_extension(self, factory):
        """Test retrieving Go parser by .go extension."""
        parser = factory.get_parser_by_extension(".go")
        assert parser.language == "Go"

    def test_get_go_parser_by_path(self, factory):
        """Test retrieving Go parser by file path."""
        path = Path("main.go")
        parser = factory.get_parser_by_path(path)
        assert parser.language == "Go"

    def test_go_in_supported_languages(self, factory):
        """Test that Go is in the list of supported languages."""
        supported = factory.get_supported_languages()
        assert "Go" in supported

    def test_go_extension_in_supported_extensions(self, factory):
        """Test that .go is in the list of supported extensions."""
        supported = factory.get_supported_extensions()
        assert ".go" in supported

    def test_go_parser_is_tree_sitter_implementation(self, factory):
        """Test that Go parser is the tree-sitter implementation."""
        parser = factory.get_parser_by_language("Go")
        assert parser.__class__.__name__ == "GoTreeSitterParser"

    def test_go_parser_parse_method_exists(self, factory):
        """Test that Go parser has parse method."""
        parser = factory.get_parser_by_language("Go")
        assert hasattr(parser, "parse")
        assert callable(parser.parse)
