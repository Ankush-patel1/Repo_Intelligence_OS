"""Unit tests for LanguageDetector service."""

from pathlib import Path

import pytest

from app.services.indexing.language_detector import LanguageDetector


class TestLanguageDetector:
    """Test suite for LanguageDetector."""

    @pytest.fixture
    def detector(self) -> LanguageDetector:
        """Create a LanguageDetector instance."""
        return LanguageDetector()

    # Python tests
    def test_detect_python(self, detector: LanguageDetector) -> None:
        """Test detection of Python files."""
        assert detector.detect(Path("script.py")) == "Python"
        assert detector.detect(Path("main.py")) == "Python"
        assert detector.detect(Path("/path/to/module.py")) == "Python"

    # JavaScript tests
    def test_detect_javascript_js(self, detector: LanguageDetector) -> None:
        """Test detection of .js files."""
        assert detector.detect(Path("app.js")) == "JavaScript"
        assert detector.detect(Path("index.js")) == "JavaScript"

    def test_detect_javascript_jsx(self, detector: LanguageDetector) -> None:
        """Test detection of .jsx files."""
        assert detector.detect(Path("Component.jsx")) == "JavaScript"

    def test_detect_javascript_mjs(self, detector: LanguageDetector) -> None:
        """Test detection of .mjs files."""
        assert detector.detect(Path("module.mjs")) == "JavaScript"

    def test_detect_javascript_cjs(self, detector: LanguageDetector) -> None:
        """Test detection of .cjs files."""
        assert detector.detect(Path("config.cjs")) == "JavaScript"

    # TypeScript tests
    def test_detect_typescript_ts(self, detector: LanguageDetector) -> None:
        """Test detection of .ts files."""
        assert detector.detect(Path("app.ts")) == "TypeScript"
        assert detector.detect(Path("types.ts")) == "TypeScript"

    def test_detect_typescript_tsx(self, detector: LanguageDetector) -> None:
        """Test detection of .tsx files."""
        assert detector.detect(Path("App.tsx")) == "TypeScript"
        assert detector.detect(Path("Component.tsx")) == "TypeScript"

    # Java tests
    def test_detect_java(self, detector: LanguageDetector) -> None:
        """Test detection of Java files."""
        assert detector.detect(Path("Main.java")) == "Java"
        assert detector.detect(Path("Application.java")) == "Java"

    # C tests
    def test_detect_c_source(self, detector: LanguageDetector) -> None:
        """Test detection of .c files."""
        assert detector.detect(Path("main.c")) == "C"
        assert detector.detect(Path("utils.c")) == "C"

    def test_detect_c_header(self, detector: LanguageDetector) -> None:
        """Test detection of .h files."""
        assert detector.detect(Path("header.h")) == "C"
        assert detector.detect(Path("utils.h")) == "C"

    # C++ tests
    def test_detect_cpp_cpp_extension(self, detector: LanguageDetector) -> None:
        """Test detection of .cpp files."""
        assert detector.detect(Path("main.cpp")) == "C++"

    def test_detect_cpp_cc_extension(self, detector: LanguageDetector) -> None:
        """Test detection of .cc files."""
        assert detector.detect(Path("module.cc")) == "C++"

    def test_detect_cpp_cxx_extension(self, detector: LanguageDetector) -> None:
        """Test detection of .cxx files."""
        assert detector.detect(Path("app.cxx")) == "C++"

    def test_detect_cpp_hpp_header(self, detector: LanguageDetector) -> None:
        """Test detection of .hpp files."""
        assert detector.detect(Path("header.hpp")) == "C++"

    def test_detect_cpp_hh_header(self, detector: LanguageDetector) -> None:
        """Test detection of .hh files."""
        assert detector.detect(Path("header.hh")) == "C++"

    # Go tests
    def test_detect_go(self, detector: LanguageDetector) -> None:
        """Test detection of Go files."""
        assert detector.detect(Path("main.go")) == "Go"
        assert detector.detect(Path("server.go")) == "Go"

    # Rust tests
    def test_detect_rust(self, detector: LanguageDetector) -> None:
        """Test detection of Rust files."""
        assert detector.detect(Path("main.rs")) == "Rust"
        assert detector.detect(Path("lib.rs")) == "Rust"

    # HTML tests
    def test_detect_html_html_extension(self, detector: LanguageDetector) -> None:
        """Test detection of .html files."""
        assert detector.detect(Path("index.html")) == "HTML"
        assert detector.detect(Path("page.html")) == "HTML"

    def test_detect_html_htm_extension(self, detector: LanguageDetector) -> None:
        """Test detection of .htm files."""
        assert detector.detect(Path("page.htm")) == "HTML"

    # CSS tests
    def test_detect_css(self, detector: LanguageDetector) -> None:
        """Test detection of CSS files."""
        assert detector.detect(Path("styles.css")) == "CSS"
        assert detector.detect(Path("main.css")) == "CSS"

    # SQL tests
    def test_detect_sql(self, detector: LanguageDetector) -> None:
        """Test detection of SQL files."""
        assert detector.detect(Path("schema.sql")) == "SQL"
        assert detector.detect(Path("queries.sql")) == "SQL"

    # JSON tests
    def test_detect_json(self, detector: LanguageDetector) -> None:
        """Test detection of JSON files."""
        assert detector.detect(Path("package.json")) == "JSON"
        assert detector.detect(Path("config.json")) == "JSON"

    # YAML tests
    def test_detect_yaml_yml_extension(self, detector: LanguageDetector) -> None:
        """Test detection of .yml files."""
        assert detector.detect(Path("config.yml")) == "YAML"
        assert detector.detect(Path("docker-compose.yml")) == "YAML"

    def test_detect_yaml_yaml_extension(self, detector: LanguageDetector) -> None:
        """Test detection of .yaml files."""
        assert detector.detect(Path("config.yaml")) == "YAML"
        assert detector.detect(Path("github-workflow.yaml")) == "YAML"

    # Markdown tests
    def test_detect_markdown_md_extension(self, detector: LanguageDetector) -> None:
        """Test detection of .md files."""
        assert detector.detect(Path("README.md")) == "Markdown"
        assert detector.detect(Path("CONTRIBUTING.md")) == "Markdown"

    def test_detect_markdown_markdown_extension(self, detector: LanguageDetector) -> None:
        """Test detection of .markdown files."""
        assert detector.detect(Path("doc.markdown")) == "Markdown"

    # Case sensitivity tests
    def test_detect_case_insensitive_uppercase(self, detector: LanguageDetector) -> None:
        """Test that detection is case-insensitive for uppercase extensions."""
        assert detector.detect(Path("Main.PY")) == "Python"
        assert detector.detect(Path("App.JS")) == "JavaScript"
        assert detector.detect(Path("Component.TSX")) == "TypeScript"

    def test_detect_case_insensitive_mixed(self, detector: LanguageDetector) -> None:
        """Test that detection is case-insensitive for mixed case extensions."""
        assert detector.detect(Path("file.Py")) == "Python"
        assert detector.detect(Path("script.Js")) == "JavaScript"
        assert detector.detect(Path("config.YmL")) == "YAML"

    # Unknown extension tests
    def test_detect_unknown_extension(self, detector: LanguageDetector) -> None:
        """Test that unknown extensions return 'Unknown'."""
        assert detector.detect(Path("file.xyz")) == "Unknown"
        assert detector.detect(Path("data.dat")) == "Unknown"
        assert detector.detect(Path("binary.bin")) == "Unknown"

    def test_detect_no_extension(self, detector: LanguageDetector) -> None:
        """Test that files without extension return 'Unknown'."""
        assert detector.detect(Path("Makefile")) == "Unknown"
        assert detector.detect(Path("Dockerfile")) == "Unknown"
        assert detector.detect(Path("README")) == "Unknown"

    def test_detect_empty_extension(self, detector: LanguageDetector) -> None:
        """Test that files with empty extension return 'Unknown'."""
        assert detector.detect(Path("file.")) == "Unknown"

    # Path variation tests
    def test_detect_with_absolute_path(self, detector: LanguageDetector) -> None:
        """Test detection with absolute paths."""
        assert detector.detect(Path("/usr/local/bin/script.py")) == "Python"
        assert detector.detect(Path("C:\\Users\\test\\app.js")) == "JavaScript"

    def test_detect_with_relative_path(self, detector: LanguageDetector) -> None:
        """Test detection with relative paths."""
        assert detector.detect(Path("../src/main.py")) == "Python"
        assert detector.detect(Path("./config.json")) == "JSON"

    def test_detect_with_nested_path(self, detector: LanguageDetector) -> None:
        """Test detection with deeply nested paths."""
        path = Path("project/src/components/ui/Button.tsx")
        assert detector.detect(path) == "TypeScript"

    # Multiple extension tests
    def test_detect_with_multiple_extensions(self, detector: LanguageDetector) -> None:
        """Test that only the last extension is considered."""
        assert detector.detect(Path("archive.tar.gz")) == "Unknown"
        assert detector.detect(Path("config.json.bak")) == "Unknown"
        assert detector.detect(Path("test.spec.ts")) == "TypeScript"

    # Edge cases
    def test_detect_hidden_file(self, detector: LanguageDetector) -> None:
        """Test detection of hidden files (starting with dot)."""
        assert detector.detect(Path(".eslintrc.js")) == "JavaScript"
        assert detector.detect(Path(".gitignore")) == "Unknown"

    def test_detect_file_with_dots_in_name(self, detector: LanguageDetector) -> None:
        """Test detection of files with multiple dots in name."""
        assert detector.detect(Path("my.component.spec.ts")) == "TypeScript"
        assert detector.detect(Path("app.module.ts")) == "TypeScript"
        assert detector.detect(Path("v1.2.3.py")) == "Python"
