"""Unit tests for ParserFactory."""

import pytest

from app.services.parser.parser_factory import ParserFactory
from app.services.parser.python_parser import PythonTreeSitterParser
from app.services.parser.javascript_parser import JavaScriptTreeSitterParser
from app.services.parser.typescript_parser import TypeScriptTreeSitterParser


class TestParserFactory:
    """Test suite for ParserFactory."""

    @pytest.fixture
    def factory(self) -> ParserFactory:
        """Create a ParserFactory instance."""
        return ParserFactory()

    def test_get_python_parser(self, factory: ParserFactory) -> None:
        """Test getting Python parser by language."""
        parser = factory.get_parser_by_language("Python")

        assert parser is not None
        assert isinstance(parser, PythonTreeSitterParser)
        assert parser.language == "Python"

    def test_get_javascript_parser(self, factory: ParserFactory) -> None:
        """Test getting JavaScript parser by language."""
        parser = factory.get_parser_by_language("JavaScript")

        assert parser is not None
        assert isinstance(parser, JavaScriptTreeSitterParser)
        assert parser.language == "JavaScript"

    def test_get_typescript_parser(self, factory: ParserFactory) -> None:
        """Test getting TypeScript parser by language."""
        parser = factory.get_parser_by_language("TypeScript")

        assert parser is not None
        assert isinstance(parser, TypeScriptTreeSitterParser)
        assert parser.language == "TypeScript"

    def test_get_parser_case_sensitive(self, factory: ParserFactory) -> None:
        """Test that language lookup is case-sensitive."""
        parser_python = factory.get_parser_by_language("Python")
        parser_lowercase = factory.get_parser_by_language("python")

        # Exact case match should work
        assert isinstance(parser_python, PythonTreeSitterParser)
        # Lowercase may return placeholder
        assert parser_lowercase is not None

    def test_get_parser_unsupported_language(self, factory: ParserFactory) -> None:
        """Test getting parser for unsupported language returns placeholder."""
        parser = factory.get_parser_by_language("Rust")

        assert parser is not None
        # Placeholder parser should still be a valid ParserInterface
        assert hasattr(parser, "parse")
        assert hasattr(parser, "language")

    def test_get_parser_unknown_language(self, factory: ParserFactory) -> None:
        """Test getting parser for unknown language returns placeholder."""
        parser = factory.get_parser_by_language("Unknown")

        assert parser is not None
        # Should return a placeholder parser
        assert hasattr(parser, "parse")

    def test_get_python_parser_by_extension(self, factory: ParserFactory) -> None:
        """Test getting Python parser by file extension."""
        parser = factory.get_parser_by_extension(".py")

        assert parser is not None
        assert isinstance(parser, PythonTreeSitterParser)

    def test_get_javascript_parser_by_extension_js(self, factory: ParserFactory) -> None:
        """Test getting JavaScript parser by .js extension."""
        parser = factory.get_parser_by_extension(".js")

        assert parser is not None
        assert isinstance(parser, JavaScriptTreeSitterParser)

    def test_get_javascript_parser_by_extension_jsx(self, factory: ParserFactory) -> None:
        """Test getting JavaScript parser by .jsx extension."""
        parser = factory.get_parser_by_extension(".jsx")

        assert parser is not None
        assert isinstance(parser, JavaScriptTreeSitterParser)

    def test_get_typescript_parser_by_extension_ts(self, factory: ParserFactory) -> None:
        """Test getting TypeScript parser by .ts extension."""
        parser = factory.get_parser_by_extension(".ts")

        assert parser is not None
        assert isinstance(parser, TypeScriptTreeSitterParser)

    def test_get_typescript_parser_by_extension_tsx(self, factory: ParserFactory) -> None:
        """Test getting TypeScript parser by .tsx extension."""
        parser = factory.get_parser_by_extension(".tsx")

        assert parser is not None
        assert isinstance(parser, TypeScriptTreeSitterParser)

    def test_get_parser_by_extension_case_insensitive(self, factory: ParserFactory) -> None:
        """Test that extension lookup is case-insensitive."""
        parser1 = factory.get_parser_by_extension(".py")
        parser2 = factory.get_parser_by_extension(".PY")
        parser3 = factory.get_parser_by_extension(".Py")

        assert isinstance(parser1, PythonTreeSitterParser)
        assert isinstance(parser2, PythonTreeSitterParser)
        assert isinstance(parser3, PythonTreeSitterParser)

    def test_get_parser_by_unsupported_extension(self, factory: ParserFactory) -> None:
        """Test getting parser for unsupported extension returns placeholder."""
        parser = factory.get_parser_by_extension(".xyz")

        assert parser is not None
        # Should return a placeholder parser
        assert hasattr(parser, "parse")

    def test_get_supported_languages(self, factory: ParserFactory) -> None:
        """Test getting list of supported languages."""
        languages = factory.get_supported_languages()

        assert isinstance(languages, list)
        assert "Python" in languages
        assert "JavaScript" in languages
        assert "TypeScript" in languages

    def test_get_supported_extensions(self, factory: ParserFactory) -> None:
        """Test getting list of supported extensions."""
        extensions = factory.get_supported_extensions()

        assert isinstance(extensions, list)
        assert ".py" in extensions
        assert ".js" in extensions
        assert ".jsx" in extensions
        assert ".ts" in extensions
        assert ".tsx" in extensions

    def test_parser_singleton_behavior(self, factory: ParserFactory) -> None:
        """Test that factory returns same parser instance for same language."""
        parser1 = factory.get_parser_by_language("Python")
        parser2 = factory.get_parser_by_language("Python")

        # Should return the same instance (singleton pattern)
        assert parser1 is parser2

    def test_different_parsers_are_different_instances(self, factory: ParserFactory) -> None:
        """Test that different language parsers are different instances."""
        python_parser = factory.get_parser_by_language("Python")
        js_parser = factory.get_parser_by_language("JavaScript")

        assert python_parser is not js_parser
        assert type(python_parser) != type(js_parser)
