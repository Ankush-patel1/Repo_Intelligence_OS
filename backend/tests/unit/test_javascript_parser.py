"""Unit tests for JavaScript parser."""

from pathlib import Path

import pytest

from app.services.parser.javascript_parser import JavaScriptTreeSitterParser


class TestJavaScriptParser:
    """Test suite for JavaScriptTreeSitterParser."""

    @pytest.fixture
    def parser(self) -> JavaScriptTreeSitterParser:
        """Create a JavaScriptTreeSitterParser instance."""
        return JavaScriptTreeSitterParser()

    @pytest.fixture
    def sample_file(self) -> Path:
        """Get path to sample JavaScript file."""
        return Path("tests/fixtures/samples/sample.js")

    def test_parser_language(self, parser: JavaScriptTreeSitterParser) -> None:
        """Test that parser reports correct language."""
        assert parser.language == "JavaScript"

    def test_parser_supported_extensions(self, parser: JavaScriptTreeSitterParser) -> None:
        """Test that parser supports JavaScript extensions."""
        supported = parser.supported_extensions
        assert ".js" in supported
        assert ".jsx" in supported
        assert ".mjs" in supported
        assert ".cjs" in supported

    def test_can_parse_javascript_files(self, parser: JavaScriptTreeSitterParser) -> None:
        """Test can_parse returns True for JavaScript files."""
        assert parser.can_parse(Path("test.js"))
        assert parser.can_parse(Path("Component.jsx"))
        assert parser.can_parse(Path("module.mjs"))
        assert parser.can_parse(Path("config.cjs"))

    def test_can_parse_rejects_non_javascript(self, parser: JavaScriptTreeSitterParser) -> None:
        """Test can_parse returns False for non-JavaScript files."""
        assert not parser.can_parse(Path("test.py"))
        assert not parser.can_parse(Path("test.ts"))

    def test_parse_sample_file_success(self, parser: JavaScriptTreeSitterParser, sample_file: Path) -> None:
        """Test parsing sample JavaScript file succeeds."""
        result = parser.parse(sample_file)

        assert result.success is True
        assert result.language == "JavaScript"
        assert result.error_message is None
        assert result.parse_tree is not None
        assert result.symbols is not None

    def test_parse_extracts_imports(self, parser: JavaScriptTreeSitterParser, sample_file: Path) -> None:
        """Test that imports are extracted."""
        result = parser.parse(sample_file)

        imports = [s for s in result.symbols if s["type"] == "import"]
        assert len(imports) >= 2  # import { useState }, import axios

        import_names = [imp["name"] for imp in imports]
        assert any("useState" in name or "react" in name for name in import_names)
        assert any("axios" in name for name in import_names)

    def test_parse_extracts_exports(self, parser: JavaScriptTreeSitterParser, sample_file: Path) -> None:
        """Test that exports are extracted."""
        result = parser.parse(sample_file)

        exports = [s for s in result.symbols if s["type"] == "export"]
        assert len(exports) >= 1

    def test_parse_extracts_regular_function(self, parser: JavaScriptTreeSitterParser, sample_file: Path) -> None:
        """Test that regular functions are extracted."""
        result = parser.parse(sample_file)

        functions = [s for s in result.symbols if s["type"] == "function"]
        func_names = [f["name"] for f in functions]

        assert "regularFunction" in func_names
        assert "asyncFunction" in func_names

    def test_parse_extracts_async_function(self, parser: JavaScriptTreeSitterParser, sample_file: Path) -> None:
        """Test that async functions are marked correctly."""
        result = parser.parse(sample_file)

        functions = [s for s in result.symbols if s["type"] == "function"]
        async_func = next((f for f in functions if f["name"] == "asyncFunction"), None)

        assert async_func is not None
        assert async_func.get("is_async") is True

    def test_parse_extracts_arrow_functions(self, parser: JavaScriptTreeSitterParser, sample_file: Path) -> None:
        """Test that arrow functions are extracted."""
        result = parser.parse(sample_file)

        functions = [s for s in result.symbols if s["type"] == "function"]
        func_names = [f["name"] for f in functions]

        assert "arrowFunction" in func_names
        assert "asyncArrowFunction" in func_names

    def test_parse_extracts_function_parameters(self, parser: JavaScriptTreeSitterParser, sample_file: Path) -> None:
        """Test that function parameters are extracted."""
        result = parser.parse(sample_file)

        functions = [s for s in result.symbols if s["type"] == "function"]
        regular_func = next((f for f in functions if f["name"] == "regularFunction"), None)

        assert regular_func is not None
        assert "parameters" in regular_func
        assert "x" in regular_func["parameters"]
        assert "y" in regular_func["parameters"]

    def test_parse_extracts_class(self, parser: JavaScriptTreeSitterParser, sample_file: Path) -> None:
        """Test that classes are extracted."""
        result = parser.parse(sample_file)

        classes = [s for s in result.symbols if s["type"] == "class"]
        assert len(classes) >= 1

        sample_class = next((c for c in classes if c["name"] == "SampleClass"), None)
        assert sample_class is not None

    def test_parse_extracts_class_methods(self, parser: JavaScriptTreeSitterParser, sample_file: Path) -> None:
        """Test that class methods are extracted."""
        result = parser.parse(sample_file)

        classes = [s for s in result.symbols if s["type"] == "class"]
        sample_class = next((c for c in classes if c["name"] == "SampleClass"), None)

        assert sample_class is not None
        assert "methods" in sample_class
        assert len(sample_class["methods"]) >= 3

        method_names = [m["name"] for m in sample_class["methods"]]
        assert "instanceMethod" in method_names
        assert "asyncMethod" in method_names
        assert "staticMethod" in method_names

    def test_parse_extracts_line_numbers(self, parser: JavaScriptTreeSitterParser, sample_file: Path) -> None:
        """Test that line numbers are extracted."""
        result = parser.parse(sample_file)

        functions = [s for s in result.symbols if s["type"] == "function"]
        regular_func = next((f for f in functions if f["name"] == "regularFunction"), None)

        assert regular_func is not None
        assert "line" in regular_func
        assert "end_line" in regular_func
        assert regular_func["line"] > 0
        assert regular_func["end_line"] >= regular_func["line"]

    def test_parse_nonexistent_file(self, parser: JavaScriptTreeSitterParser) -> None:
        """Test parsing nonexistent file returns error."""
        result = parser.parse(Path("nonexistent.js"))

        assert result.success is False
        assert result.error_message is not None
        assert "not found" in result.error_message.lower()

    def test_parse_empty_file(self, parser: JavaScriptTreeSitterParser, tmp_path: Path) -> None:
        """Test parsing empty file."""
        empty_file = tmp_path / "empty.js"
        empty_file.write_text("")

        result = parser.parse(empty_file)

        assert result.success is True
        assert result.symbols == []

    def test_parse_minimal_file(self, parser: JavaScriptTreeSitterParser, tmp_path: Path) -> None:
        """Test parsing minimal valid file."""
        minimal_file = tmp_path / "minimal.js"
        minimal_file.write_text("const x = 1;\n")

        result = parser.parse(minimal_file)

        assert result.success is True
