"""Test C++ parser integration with ParserFactory."""

from pathlib import Path

import pytest

from app.services.parser.parser_factory import ParserFactory


class TestCppParserFactoryIntegration:
    """Test suite for C++ parser factory integration."""

    @pytest.fixture
    def factory(self):
        """Create a ParserFactory instance."""
        return ParserFactory()

    def test_get_cpp_parser_by_language(self, factory):
        """Test retrieving C++ parser by language name."""
        parser = factory.get_parser_by_language("C++")
        assert parser.language == "C++"
        assert ".cpp" in parser.supported_extensions

    def test_get_cpp_parser_by_extension_cpp(self, factory):
        """Test retrieving C++ parser by .cpp extension."""
        parser = factory.get_parser_by_extension(".cpp")
        assert parser.language == "C++"

    def test_get_cpp_parser_by_extension_hpp(self, factory):
        """Test retrieving C++ parser by .hpp extension."""
        parser = factory.get_parser_by_extension(".hpp")
        assert parser.language == "C++"

    def test_get_cpp_parser_by_extension_cc(self, factory):
        """Test retrieving C++ parser by .cc extension."""
        parser = factory.get_parser_by_extension(".cc")
        assert parser.language == "C++"

    def test_get_cpp_parser_by_extension_hh(self, factory):
        """Test retrieving C++ parser by .hh extension."""
        parser = factory.get_parser_by_extension(".hh")
        assert parser.language == "C++"

    def test_get_cpp_parser_by_path(self, factory):
        """Test retrieving C++ parser by file path."""
        paths = [
            Path("src/main.cpp"),
            Path("include/header.hpp"),
            Path("src/utils.cc"),
            Path("include/types.hh"),
        ]
        for path in paths:
            parser = factory.get_parser_by_path(path)
            assert parser.language == "C++"

    def test_cpp_in_supported_languages(self, factory):
        """Test that C++ is in the list of supported languages."""
        supported = factory.get_supported_languages()
        assert "C++" in supported

    def test_cpp_extensions_in_supported_extensions(self, factory):
        """Test that C++ extensions are in the list of supported extensions."""
        supported = factory.get_supported_extensions()
        assert ".cpp" in supported
        assert ".hpp" in supported
        assert ".cc" in supported
        assert ".hh" in supported

    def test_cpp_parser_is_tree_sitter_implementation(self, factory):
        """Test that C++ parser is the tree-sitter implementation."""
        parser = factory.get_parser_by_language("C++")
        assert parser.__class__.__name__ == "CppTreeSitterParser"

    def test_cpp_parser_parse_method_exists(self, factory):
        """Test that C++ parser has parse method."""
        parser = factory.get_parser_by_language("C++")
        assert hasattr(parser, "parse")
        assert callable(parser.parse)

    def test_cpp_parser_supports_multiple_extensions(self, factory):
        """Test that C++ parser supports all C++ file extensions."""
        parser = factory.get_parser_by_language("C++")
        expected_extensions = [".cpp", ".cc", ".cxx", ".c++", ".hpp", ".hh", ".hxx", ".h++", ".h"]
        for ext in expected_extensions:
            assert ext in parser.supported_extensions
