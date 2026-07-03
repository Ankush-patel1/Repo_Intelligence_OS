"""Test Java parser integration with ParserFactory."""

from pathlib import Path

import pytest

from app.services.parser.parser_factory import ParserFactory


class TestJavaParserFactoryIntegration:
    """Test suite for Java parser factory integration."""

    @pytest.fixture
    def factory(self):
        """Create a ParserFactory instance."""
        return ParserFactory()

    def test_get_java_parser_by_language(self, factory):
        """Test retrieving Java parser by language name."""
        parser = factory.get_parser_by_language("Java")
        assert parser.language == "Java"
        assert parser.supported_extensions == [".java"]

    def test_get_java_parser_by_extension(self, factory):
        """Test retrieving Java parser by .java extension."""
        parser = factory.get_parser_by_extension(".java")
        assert parser.language == "Java"
        assert ".java" in parser.supported_extensions

    def test_get_java_parser_by_path(self, factory):
        """Test retrieving Java parser by file path."""
        path = Path("src/main/java/com/example/User.java")
        parser = factory.get_parser_by_path(path)
        assert parser.language == "Java"

    def test_java_in_supported_languages(self, factory):
        """Test that Java is in the list of supported languages."""
        supported = factory.get_supported_languages()
        assert "Java" in supported

    def test_java_extension_in_supported_extensions(self, factory):
        """Test that .java is in the list of supported extensions."""
        supported = factory.get_supported_extensions()
        assert ".java" in supported

    def test_java_parser_is_tree_sitter_implementation(self, factory):
        """Test that Java parser is the tree-sitter implementation."""
        parser = factory.get_parser_by_language("Java")
        # Should be JavaTreeSitterParser, not a placeholder
        assert parser.__class__.__name__ == "JavaTreeSitterParser"
        
    def test_java_parser_parse_method_exists(self, factory):
        """Test that Java parser has parse method."""
        parser = factory.get_parser_by_language("Java")
        assert hasattr(parser, "parse")
        assert callable(parser.parse)
