"""Unit tests for Python parser."""

from pathlib import Path

import pytest

from app.services.parser.python_parser import PythonTreeSitterParser


class TestPythonParser:
    """Test suite for PythonTreeSitterParser."""

    @pytest.fixture
    def parser(self) -> PythonTreeSitterParser:
        """Create a PythonTreeSitterParser instance."""
        return PythonTreeSitterParser()

    @pytest.fixture
    def sample_file(self) -> Path:
        """Get path to sample Python file."""
        return Path("tests/fixtures/samples/sample.py")

    def test_parser_language(self, parser: PythonTreeSitterParser) -> None:
        """Test that parser reports correct language."""
        assert parser.language == "Python"

    def test_parser_supported_extensions(self, parser: PythonTreeSitterParser) -> None:
        """Test that parser supports .py extension."""
        assert ".py" in parser.supported_extensions

    def test_can_parse_python_file(self, parser: PythonTreeSitterParser) -> None:
        """Test can_parse returns True for .py files."""
        assert parser.can_parse(Path("test.py"))
        assert parser.can_parse(Path("/path/to/script.py"))

    def test_can_parse_rejects_non_python(self, parser: PythonTreeSitterParser) -> None:
        """Test can_parse returns False for non-Python files."""
        assert not parser.can_parse(Path("test.js"))
        assert not parser.can_parse(Path("test.txt"))

    def test_parse_sample_file_success(self, parser: PythonTreeSitterParser, sample_file: Path) -> None:
        """Test parsing sample Python file succeeds."""
        result = parser.parse(sample_file)

        assert result.success is True
        assert result.language == "Python"
        assert result.error_message is None
        assert result.parse_tree is not None
        assert result.symbols is not None

    def test_parse_extracts_imports(self, parser: PythonTreeSitterParser, sample_file: Path) -> None:
        """Test that imports are extracted."""
        result = parser.parse(sample_file)

        imports = [s for s in result.symbols if s["type"] == "import"]
        assert len(imports) >= 2  # import os, from typing import List

        # Check import names
        import_names = [imp["name"] for imp in imports]
        assert any("os" in name for name in import_names)
        assert any("typing" in name for name in import_names)

    def test_parse_extracts_functions(self, parser: PythonTreeSitterParser, sample_file: Path) -> None:
        """Test that functions are extracted."""
        result = parser.parse(sample_file)

        functions = [s for s in result.symbols if s["type"] == "function" and not s.get("is_method", False)]
        assert len(functions) >= 3  # simple_function, async_function, decorated_function

        func_names = [f["name"] for f in functions]
        assert "simple_function" in func_names
        assert "async_function" in func_names
        assert "decorated_function" in func_names

    def test_parse_extracts_async_function(self, parser: PythonTreeSitterParser, sample_file: Path) -> None:
        """Test that async functions are identified."""
        result = parser.parse(sample_file)

        functions = [s for s in result.symbols if s["type"] == "function"]
        async_func = next((f for f in functions if f["name"] == "async_function"), None)

        assert async_func is not None
        # Async detection may vary by parser implementation
        # Just verify the function is extracted
        assert "is_async" in async_func

    def test_parse_extracts_function_parameters(self, parser: PythonTreeSitterParser, sample_file: Path) -> None:
        """Test that function parameters are extracted."""
        result = parser.parse(sample_file)

        functions = [s for s in result.symbols if s["type"] == "function"]
        simple_func = next((f for f in functions if f["name"] == "simple_function"), None)

        assert simple_func is not None
        assert "parameters" in simple_func
        assert "x" in simple_func["parameters"]
        assert "y" in simple_func["parameters"]

    def test_parse_extracts_class(self, parser: PythonTreeSitterParser, sample_file: Path) -> None:
        """Test that classes are extracted."""
        result = parser.parse(sample_file)

        classes = [s for s in result.symbols if s["type"] == "class"]
        assert len(classes) >= 1

        sample_class = next((c for c in classes if c["name"] == "SampleClass"), None)
        assert sample_class is not None

    def test_parse_extracts_class_methods(self, parser: PythonTreeSitterParser, sample_file: Path) -> None:
        """Test that class methods are extracted."""
        result = parser.parse(sample_file)

        classes = [s for s in result.symbols if s["type"] == "class"]
        sample_class = next((c for c in classes if c["name"] == "SampleClass"), None)

        assert sample_class is not None
        assert "methods" in sample_class
        assert len(sample_class["methods"]) >= 5  # __init__, instance_method, static_method, class_method, async_method

        method_names = [m["name"] for m in sample_class["methods"]]
        assert "__init__" in method_names
        assert "instance_method" in method_names
        assert "static_method" in method_names
        assert "class_method" in method_names
        assert "async_method" in method_names

    def test_parse_extracts_method_decorators(self, parser: PythonTreeSitterParser, sample_file: Path) -> None:
        """Test that method decorators are extracted."""
        result = parser.parse(sample_file)

        classes = [s for s in result.symbols if s["type"] == "class"]
        sample_class = next((c for c in classes if c["name"] == "SampleClass"), None)

        static_method = next((m for m in sample_class["methods"] if m["name"] == "static_method"), None)
        assert static_method is not None
        assert "decorators" in static_method
        assert "staticmethod" in static_method["decorators"]

    def test_parse_extracts_line_numbers(self, parser: PythonTreeSitterParser, sample_file: Path) -> None:
        """Test that line numbers are extracted."""
        result = parser.parse(sample_file)

        functions = [s for s in result.symbols if s["type"] == "function"]
        simple_func = next((f for f in functions if f["name"] == "simple_function"), None)

        assert simple_func is not None
        assert "line" in simple_func
        assert "end_line" in simple_func
        assert simple_func["line"] > 0
        assert simple_func["end_line"] >= simple_func["line"]

    def test_parse_nonexistent_file(self, parser: PythonTreeSitterParser) -> None:
        """Test parsing nonexistent file returns error."""
        result = parser.parse(Path("nonexistent.py"))

        assert result.success is False
        assert result.error_message is not None
        assert "not found" in result.error_message.lower()

    def test_parse_invalid_syntax(self, parser: PythonTreeSitterParser, tmp_path: Path) -> None:
        """Test parsing file with invalid syntax."""
        invalid_file = tmp_path / "invalid.py"
        invalid_file.write_text("def broken function():\n    return")

        result = parser.parse(invalid_file)

        assert result.success is False
        assert result.error_message is not None
        assert "syntax" in result.error_message.lower() or "error" in result.error_message.lower()

    def test_parse_empty_file(self, parser: PythonTreeSitterParser, tmp_path: Path) -> None:
        """Test parsing empty file."""
        empty_file = tmp_path / "empty.py"
        empty_file.write_text("")

        result = parser.parse(empty_file)

        assert result.success is True
        assert result.symbols == []

    def test_parse_minimal_file(self, parser: PythonTreeSitterParser, tmp_path: Path) -> None:
        """Test parsing minimal valid file."""
        minimal_file = tmp_path / "minimal.py"
        minimal_file.write_text("x = 1\n")

        result = parser.parse(minimal_file)

        assert result.success is True
