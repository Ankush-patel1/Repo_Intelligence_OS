"""Test Rust parser integration with ParserFactory."""

from pathlib import Path

import pytest

from app.services.parser.parser_factory import ParserFactory


class TestRustParserFactoryIntegration:
    """Test suite for Rust parser factory integration."""

    @pytest.fixture
    def factory(self):
        """Create a ParserFactory instance."""
        return ParserFactory()

    def test_get_rust_parser_by_language(self, factory):
        """Test retrieving Rust parser by language name."""
        parser = factory.get_parser_by_language("Rust")
        assert parser.language == "Rust"
        assert ".rs" in parser.supported_extensions

    def test_get_rust_parser_by_extension(self, factory):
        """Test retrieving Rust parser by .rs extension."""
        parser = factory.get_parser_by_extension(".rs")
        assert parser.language == "Rust"

    def test_get_rust_parser_by_path(self, factory):
        """Test retrieving Rust parser by file path."""
        path = Path("main.rs")
        parser = factory.get_parser_by_path(path)
        assert parser.language == "Rust"

    def test_rust_in_supported_languages(self, factory):
        """Test that Rust is in the list of supported languages."""
        supported = factory.get_supported_languages()
        assert "Rust" in supported

    def test_rust_extension_in_supported_extensions(self, factory):
        """Test that .rs is in the list of supported extensions."""
        supported = factory.get_supported_extensions()
        assert ".rs" in supported

    def test_rust_parser_is_tree_sitter_implementation(self, factory):
        """Test that Rust parser is the tree-sitter implementation."""
        parser = factory.get_parser_by_language("Rust")
        assert parser.__class__.__name__ == "RustTreeSitterParser"

    def test_rust_parser_parse_method_exists(self, factory):
        """Test that Rust parser has parse method."""
        parser = factory.get_parser_by_language("Rust")
        assert hasattr(parser, "parse")
        assert callable(parser.parse)
