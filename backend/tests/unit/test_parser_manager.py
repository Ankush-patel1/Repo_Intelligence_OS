"""Unit tests for ParserManager."""

from pathlib import Path

import pytest

from app.services.parser.parser_manager import ParserManager


class TestParserManager:
    """Test suite for ParserManager."""

    @pytest.fixture
    def manager(self) -> ParserManager:
        """Create a ParserManager instance."""
        return ParserManager()

    @pytest.fixture
    def sample_python_file(self) -> Path:
        """Get path to sample Python file."""
        return Path("tests/fixtures/samples/sample.py")

    @pytest.fixture
    def sample_js_file(self) -> Path:
        """Get path to sample JavaScript file."""
        return Path("tests/fixtures/samples/sample.js")

    @pytest.fixture
    def sample_ts_file(self) -> Path:
        """Get path to sample TypeScript file."""
        return Path("tests/fixtures/samples/sample.ts")

    def test_parse_python_file(self, manager: ParserManager, sample_python_file: Path) -> None:
        """Test parsing Python file through manager."""
        result = manager.parse_file(sample_python_file)

        assert result.success is True
        assert result.language == "Python"
        assert result.symbols is not None
        assert len(result.symbols) > 0

    def test_parse_javascript_file(self, manager: ParserManager, sample_js_file: Path) -> None:
        """Test parsing JavaScript file through manager."""
        result = manager.parse_file(sample_js_file)

        assert result.success is True
        assert result.language == "JavaScript"
        assert result.symbols is not None
        assert len(result.symbols) > 0

    def test_parse_typescript_file(self, manager: ParserManager, sample_ts_file: Path) -> None:
        """Test parsing TypeScript file through manager."""
        result = manager.parse_file(sample_ts_file)

        assert result.success is True
        assert result.language == "TypeScript"
        assert result.symbols is not None
        assert len(result.symbols) > 0

    def test_parse_file_with_string_path(self, manager: ParserManager, sample_python_file: Path) -> None:
        """Test parsing file with string path."""
        result = manager.parse_file(str(sample_python_file))

        assert result.success is True
        assert result.language == "Python"

    def test_parse_files_multiple(self, manager: ParserManager, sample_python_file: Path, sample_js_file: Path) -> None:
        """Test parsing multiple files."""
        results = manager.parse_files([sample_python_file, sample_js_file])

        assert len(results) == 2
        assert all(r.success for r in results)
        assert results[0].language == "Python"
        assert results[1].language == "JavaScript"

    def test_parse_files_empty_list(self, manager: ParserManager) -> None:
        """Test parsing empty list of files."""
        results = manager.parse_files([])

        assert results == []

    def test_can_parse_python_file(self, manager: ParserManager) -> None:
        """Test can_parse returns True for Python files."""
        assert manager.can_parse("test.py")
        assert manager.can_parse(Path("script.py"))

    def test_can_parse_javascript_file(self, manager: ParserManager) -> None:
        """Test can_parse returns True for JavaScript files."""
        assert manager.can_parse("app.js")
        assert manager.can_parse("Component.jsx")
        assert manager.can_parse(Path("module.mjs"))

    def test_can_parse_typescript_file(self, manager: ParserManager) -> None:
        """Test can_parse returns True for TypeScript files."""
        assert manager.can_parse("app.ts")
        assert manager.can_parse(Path("Component.tsx"))

    def test_can_parse_unsupported_file(self, manager: ParserManager) -> None:
        """Test can_parse returns False for unsupported files."""
        assert not manager.can_parse("test.txt")
        assert not manager.can_parse("data.csv")
        assert not manager.can_parse(Path("image.png"))

    def test_get_supported_languages(self, manager: ParserManager) -> None:
        """Test getting list of supported languages."""
        languages = manager.get_supported_languages()

        assert isinstance(languages, list)
        assert "Python" in languages
        assert "JavaScript" in languages
        assert "TypeScript" in languages
        assert len(languages) >= 3

    def test_get_supported_extensions(self, manager: ParserManager) -> None:
        """Test getting list of supported extensions."""
        extensions = manager.get_supported_extensions()

        assert isinstance(extensions, list)
        assert ".py" in extensions
        assert ".js" in extensions
        assert ".ts" in extensions
        assert len(extensions) >= 5

    def test_parse_nonexistent_file(self, manager: ParserManager) -> None:
        """Test parsing nonexistent file."""
        result = manager.parse_file("nonexistent_file.py")

        assert result.success is False
        assert result.error_message is not None

    def test_parse_file_automatic_language_detection(self, manager: ParserManager, sample_python_file: Path) -> None:
        """Test that manager automatically detects language."""
        result = manager.parse_file(sample_python_file)

        # Manager should detect it's Python based on extension
        assert result.language == "Python"
        # Should extract Python-specific symbols
        functions = [s for s in result.symbols if s["type"] == "function"]
        assert len(functions) > 0

    def test_parse_file_selects_correct_parser(self, manager: ParserManager, sample_js_file: Path, sample_ts_file: Path) -> None:
        """Test that manager selects correct parser for each language."""
        js_result = manager.parse_file(sample_js_file)
        ts_result = manager.parse_file(sample_ts_file)

        assert js_result.language == "JavaScript"
        assert ts_result.language == "TypeScript"

        # TypeScript should have interfaces/types that JavaScript doesn't
        ts_interfaces = [s for s in ts_result.symbols if s["type"] == "interface"]
        assert len(ts_interfaces) > 0

    def test_manager_integration_with_factory(self, manager: ParserManager) -> None:
        """Test that manager properly integrates with factory."""
        # Manager should use factory internally
        assert hasattr(manager, "_parser_factory")
        assert hasattr(manager, "_language_detector")

    def test_parse_empty_file(self, manager: ParserManager, tmp_path: Path) -> None:
        """Test parsing empty file."""
        empty_file = tmp_path / "empty.py"
        empty_file.write_text("")

        result = manager.parse_file(empty_file)

        assert result.success is True
        assert result.symbols == []

    def test_parse_file_consistency(self, manager: ParserManager, sample_python_file: Path) -> None:
        """Test that parsing same file multiple times gives consistent results."""
        result1 = manager.parse_file(sample_python_file)
        result2 = manager.parse_file(sample_python_file)

        assert result1.success == result2.success
        assert result1.language == result2.language
        assert len(result1.symbols) == len(result2.symbols)
