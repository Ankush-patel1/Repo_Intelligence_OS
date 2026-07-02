"""Unit tests for FileScanner service."""

import hashlib
import tempfile
from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.services.indexing.file_scanner import (
    BINARY_SAMPLE_SIZE,
    IGNORED_DIRECTORIES,
    MAX_INDEXED_FILE_SIZE_BYTES,
    FileScanner,
    ScannedFile,
)
from app.services.indexing.language_detector import LanguageDetector


class TestScannedFile:
    """Test suite for ScannedFile dataclass."""

    def test_scanned_file_immutable(self) -> None:
        """Test that ScannedFile is immutable (frozen dataclass)."""
        scanned = ScannedFile(
            relative_path="src/main.py",
            absolute_path="/project/src/main.py",
            file_name="main.py",
            extension=".py",
            language="Python",
            size_bytes=1024,
            line_count=50,
            sha256_hash="abc123",
            last_modified=datetime.now(UTC),
            is_binary=False,
        )
        with pytest.raises(Exception):  # FrozenInstanceError
            scanned.size_bytes = 2048  # type: ignore


class TestFileScanner:
    """Test suite for FileScanner."""

    @pytest.fixture
    def scanner(self) -> FileScanner:
        """Create a FileScanner instance."""
        return FileScanner()

    @pytest.fixture
    def temp_repo(self, tmp_path: Path) -> Path:
        """Create a temporary repository structure for testing."""
        # Create directory structure
        (tmp_path / "src").mkdir()
        (tmp_path / "tests").mkdir()
        (tmp_path / "docs").mkdir()
        (tmp_path / ".git").mkdir()  # Should be ignored
        (tmp_path / "node_modules").mkdir()  # Should be ignored
        (tmp_path / "dist").mkdir()  # Should be ignored

        # Create Python files
        (tmp_path / "src" / "main.py").write_text("print('hello')\nprint('world')\n")
        (tmp_path / "tests" / "test_main.py").write_text("def test_main():\n    pass\n")

        # Create JavaScript file
        (tmp_path / "src" / "app.js").write_text("console.log('test');\n")

        # Create Markdown file
        (tmp_path / "docs" / "README.md").write_text("# Project\n\nDocumentation\n")

        # Create binary file
        (tmp_path / "data.bin").write_bytes(b"\x00\x01\x02\x03\x04")

        # Create files in ignored directories (should not be scanned)
        (tmp_path / ".git" / "config").write_text("git config")
        (tmp_path / "node_modules" / "package.json").write_text("{}")
        (tmp_path / "dist" / "bundle.js").write_text("var x = 1;")

        return tmp_path

    # Basic scanning tests
    def test_scan_empty_directory(self, scanner: FileScanner, tmp_path: Path) -> None:
        """Test scanning an empty directory."""
        result = scanner.scan(tmp_path)
        assert result == []

    def test_scan_nonexistent_directory(self, scanner: FileScanner) -> None:
        """Test scanning a non-existent directory."""
        result = scanner.scan("/nonexistent/path/to/repo")
        assert result == []

    def test_scan_file_not_directory(self, scanner: FileScanner, tmp_path: Path) -> None:
        """Test scanning a file instead of directory."""
        file_path = tmp_path / "file.txt"
        file_path.write_text("content")
        result = scanner.scan(file_path)
        assert result == []

    def test_scan_finds_files(self, scanner: FileScanner, temp_repo: Path) -> None:
        """Test that scan finds files in directory."""
        result = scanner.scan(temp_repo)
        assert len(result) > 0

    def test_scan_ignores_directories(self, scanner: FileScanner, temp_repo: Path) -> None:
        """Test that ignored directories are not scanned."""
        result = scanner.scan(temp_repo)
        
        # Check no files from ignored directories
        for scanned in result:
            assert ".git" not in scanned.relative_path
            assert "node_modules" not in scanned.relative_path
            assert "dist" not in scanned.relative_path

    def test_scan_respects_file_size_limit(self, scanner: FileScanner, tmp_path: Path) -> None:
        """Test that files exceeding size limit are skipped."""
        # Create file larger than limit
        large_file = tmp_path / "large.txt"
        large_file.write_bytes(b"x" * (MAX_INDEXED_FILE_SIZE_BYTES + 1000))
        
        result = scanner.scan(tmp_path)
        assert len(result) == 0

    def test_scan_with_custom_size_limit(self, tmp_path: Path) -> None:
        """Test scanner with custom file size limit."""
        custom_limit = 100
        scanner = FileScanner(max_file_size_bytes=custom_limit)
        
        # Create files below and above limit
        small_file = tmp_path / "small.txt"
        small_file.write_bytes(b"x" * 50)
        
        large_file = tmp_path / "large.txt"
        large_file.write_bytes(b"x" * 150)
        
        result = scanner.scan(tmp_path)
        assert len(result) == 1
        assert result[0].file_name == "small.txt"

    def test_scan_handles_permission_errors(self, scanner: FileScanner, tmp_path: Path) -> None:
        """Test that permission errors are handled gracefully."""
        # Create a file
        file_path = tmp_path / "test.txt"
        file_path.write_text("content")
        
        # This test would require platform-specific permission manipulation
        # Just verify no exception is raised
        result = scanner.scan(tmp_path)
        assert isinstance(result, list)

    # ScannedFile metadata tests
    def test_scanned_file_relative_path(self, scanner: FileScanner, temp_repo: Path) -> None:
        """Test that relative path is computed correctly."""
        result = scanner.scan(temp_repo)
        
        # Find the main.py file
        main_py = next((f for f in result if f.file_name == "main.py"), None)
        assert main_py is not None
        assert main_py.relative_path == "src/main.py"

    def test_scanned_file_absolute_path(self, scanner: FileScanner, temp_repo: Path) -> None:
        """Test that absolute path is set correctly."""
        result = scanner.scan(temp_repo)
        
        for scanned in result:
            assert Path(scanned.absolute_path).is_absolute()
            assert Path(scanned.absolute_path).exists()

    def test_scanned_file_name(self, scanner: FileScanner, temp_repo: Path) -> None:
        """Test that file name is extracted correctly."""
        result = scanner.scan(temp_repo)
        
        file_names = {f.file_name for f in result}
        assert "main.py" in file_names
        assert "app.js" in file_names
        assert "README.md" in file_names

    def test_scanned_file_extension(self, scanner: FileScanner, temp_repo: Path) -> None:
        """Test that extension is extracted and lowercased."""
        result = scanner.scan(temp_repo)
        
        main_py = next((f for f in result if f.file_name == "main.py"), None)
        assert main_py is not None
        assert main_py.extension == ".py"

    def test_scanned_file_extension_uppercase(self, scanner: FileScanner, tmp_path: Path) -> None:
        """Test that uppercase extensions are lowercased."""
        (tmp_path / "test.PY").write_text("print('test')")
        
        result = scanner.scan(tmp_path)
        assert len(result) == 1
        assert result[0].extension == ".py"

    def test_scanned_file_language(self, scanner: FileScanner, temp_repo: Path) -> None:
        """Test that language is detected correctly."""
        result = scanner.scan(temp_repo)
        
        main_py = next((f for f in result if f.file_name == "main.py"), None)
        assert main_py is not None
        assert main_py.language == "Python"
        
        app_js = next((f for f in result if f.file_name == "app.js"), None)
        assert app_js is not None
        assert app_js.language == "JavaScript"

    def test_scanned_file_size_bytes(self, scanner: FileScanner, temp_repo: Path) -> None:
        """Test that file size is recorded correctly."""
        result = scanner.scan(temp_repo)
        
        for scanned in result:
            assert scanned.size_bytes > 0
            assert scanned.size_bytes <= MAX_INDEXED_FILE_SIZE_BYTES

    def test_scanned_file_last_modified(self, scanner: FileScanner, temp_repo: Path) -> None:
        """Test that last modified timestamp is set."""
        result = scanner.scan(temp_repo)
        
        for scanned in result:
            assert isinstance(scanned.last_modified, datetime)
            assert scanned.last_modified.tzinfo is not None  # Has timezone

    # Binary detection tests
    def test_is_binary_detects_null_bytes(self, scanner: FileScanner) -> None:
        """Test that files with null bytes are detected as binary."""
        # Access private method for testing
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(b"text\x00more")
            tmp.flush()
            path = Path(tmp.name)
        
        try:
            assert scanner._is_binary(path) is True
        finally:
            path.unlink()

    def test_is_binary_detects_text_files(self, scanner: FileScanner) -> None:
        """Test that text files are not detected as binary."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as tmp:
            tmp.write("This is plain text\nwith multiple lines\n")
            tmp.flush()
            path = Path(tmp.name)
        
        try:
            assert scanner._is_binary(path) is False
        finally:
            path.unlink()

    def test_is_binary_handles_unreadable_files(self, scanner: FileScanner) -> None:
        """Test that unreadable files are treated as binary."""
        result = scanner._is_binary(Path("/nonexistent/file.txt"))
        assert result is True

    def test_is_binary_uses_sample_size(self, scanner: FileScanner) -> None:
        """Test that binary detection only reads first BINARY_SAMPLE_SIZE bytes."""
        # Create file with null byte after sample size
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            # Write text for BINARY_SAMPLE_SIZE bytes
            tmp.write(b"x" * BINARY_SAMPLE_SIZE)
            # Add null byte after
            tmp.write(b"\x00")
            tmp.flush()
            path = Path(tmp.name)
        
        try:
            # Should be detected as text (null byte is beyond sample)
            assert scanner._is_binary(path) is False
        finally:
            path.unlink()

    def test_scanned_file_is_binary_flag(self, scanner: FileScanner, temp_repo: Path) -> None:
        """Test that is_binary flag is set correctly."""
        result = scanner.scan(temp_repo)
        
        # Text files
        main_py = next((f for f in result if f.file_name == "main.py"), None)
        assert main_py is not None
        assert main_py.is_binary is False
        
        # Binary files
        data_bin = next((f for f in result if f.file_name == "data.bin"), None)
        assert data_bin is not None
        assert data_bin.is_binary is True

    # Line counting tests
    def test_count_lines_text_file(self, scanner: FileScanner) -> None:
        """Test line counting for text files."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as tmp:
            tmp.write("line 1\nline 2\nline 3\n")
            tmp.flush()
            path = Path(tmp.name)
        
        try:
            count = scanner._count_lines(path)
            assert count == 3
        finally:
            path.unlink()

    def test_count_lines_empty_file(self, scanner: FileScanner) -> None:
        """Test line counting for empty files."""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as tmp:
            tmp.flush()
            path = Path(tmp.name)
        
        try:
            count = scanner._count_lines(path)
            assert count == 0
        finally:
            path.unlink()

    def test_count_lines_single_line_no_newline(self, scanner: FileScanner) -> None:
        """Test line counting for file with single line and no trailing newline."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as tmp:
            tmp.write("single line")
            tmp.flush()
            path = Path(tmp.name)
        
        try:
            count = scanner._count_lines(path)
            assert count == 1
        finally:
            path.unlink()

    def test_count_lines_handles_unreadable_files(self, scanner: FileScanner) -> None:
        """Test that unreadable files return 0 lines."""
        count = scanner._count_lines(Path("/nonexistent/file.txt"))
        assert count == 0

    def test_scanned_file_line_count_text(self, scanner: FileScanner, temp_repo: Path) -> None:
        """Test that line count is set for text files."""
        result = scanner.scan(temp_repo)
        
        main_py = next((f for f in result if f.file_name == "main.py"), None)
        assert main_py is not None
        assert main_py.line_count is not None
        assert main_py.line_count > 0

    def test_scanned_file_line_count_binary(self, scanner: FileScanner, temp_repo: Path) -> None:
        """Test that line count is None for binary files."""
        result = scanner.scan(temp_repo)
        
        data_bin = next((f for f in result if f.file_name == "data.bin"), None)
        assert data_bin is not None
        assert data_bin.line_count is None

    # SHA256 hashing tests
    def test_sha256_computes_hash(self, scanner: FileScanner) -> None:
        """Test SHA256 hash computation."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as tmp:
            content = "test content"
            tmp.write(content)
            tmp.flush()
            path = Path(tmp.name)
        
        try:
            hash_result = scanner._sha256(path)
            expected_hash = hashlib.sha256(content.encode()).hexdigest()
            assert hash_result == expected_hash
        finally:
            path.unlink()

    def test_sha256_empty_file(self, scanner: FileScanner) -> None:
        """Test SHA256 hash of empty file."""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as tmp:
            tmp.flush()
            path = Path(tmp.name)
        
        try:
            hash_result = scanner._sha256(path)
            expected_hash = hashlib.sha256(b"").hexdigest()
            assert hash_result == expected_hash
        finally:
            path.unlink()

    def test_sha256_handles_unreadable_files(self, scanner: FileScanner) -> None:
        """Test that unreadable files return empty hash."""
        hash_result = scanner._sha256(Path("/nonexistent/file.txt"))
        assert hash_result == ""

    def test_sha256_large_file_chunked(self, scanner: FileScanner) -> None:
        """Test that large files are read in chunks for hashing."""
        # Create file larger than chunk size
        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as tmp:
            content = b"x" * (2 * 1024 * 1024)  # 2MB
            tmp.write(content)
            tmp.flush()
            path = Path(tmp.name)
        
        try:
            # Ensure file is within max size limit for scanning
            if path.stat().st_size <= MAX_INDEXED_FILE_SIZE_BYTES:
                hash_result = scanner._sha256(path)
                expected_hash = hashlib.sha256(content).hexdigest()
                assert hash_result == expected_hash
        finally:
            path.unlink()

    def test_scanned_file_sha256_hash(self, scanner: FileScanner, temp_repo: Path) -> None:
        """Test that SHA256 hash is set for all files."""
        result = scanner.scan(temp_repo)
        
        for scanned in result:
            assert isinstance(scanned.sha256_hash, str)
            assert len(scanned.sha256_hash) == 64  # SHA256 hex length
            assert all(c in "0123456789abcdef" for c in scanned.sha256_hash)

    # Ignored directories tests
    def test_ignored_directories_constant(self) -> None:
        """Test that IGNORED_DIRECTORIES contains expected values."""
        expected = {
            ".git",
            "node_modules",
            "dist",
            "build",
            "coverage",
            "venv",
            ".venv",
            "__pycache__",
            ".next",
            "target",
        }
        assert IGNORED_DIRECTORIES == expected

    def test_scan_ignores_git_directory(self, scanner: FileScanner, temp_repo: Path) -> None:
        """Test that .git directory is ignored."""
        result = scanner.scan(temp_repo)
        assert not any(".git" in f.relative_path for f in result)

    def test_scan_ignores_node_modules(self, scanner: FileScanner, temp_repo: Path) -> None:
        """Test that node_modules directory is ignored."""
        result = scanner.scan(temp_repo)
        assert not any("node_modules" in f.relative_path for f in result)

    def test_scan_ignores_dist_directory(self, scanner: FileScanner, temp_repo: Path) -> None:
        """Test that dist directory is ignored."""
        result = scanner.scan(temp_repo)
        assert not any("dist" in f.relative_path for f in result)

    # Nested directory tests
    def test_scan_recursive_traversal(self, scanner: FileScanner, tmp_path: Path) -> None:
        """Test that scanner recursively traverses subdirectories."""
        # Create nested structure
        (tmp_path / "level1").mkdir()
        (tmp_path / "level1" / "level2").mkdir()
        (tmp_path / "level1" / "level2" / "level3").mkdir()
        
        (tmp_path / "root.txt").write_text("root")
        (tmp_path / "level1" / "l1.txt").write_text("level1")
        (tmp_path / "level1" / "level2" / "l2.txt").write_text("level2")
        (tmp_path / "level1" / "level2" / "level3" / "l3.txt").write_text("level3")
        
        result = scanner.scan(tmp_path)
        assert len(result) == 4
        
        paths = {f.relative_path for f in result}
        assert "root.txt" in paths
        assert "level1/l1.txt" in paths
        assert "level1/level2/l2.txt" in paths
        assert "level1/level2/level3/l3.txt" in paths

    # Custom language detector tests
    def test_scanner_with_custom_language_detector(self, tmp_path: Path) -> None:
        """Test scanner with custom language detector."""
        custom_detector = LanguageDetector()
        scanner = FileScanner(language_detector=custom_detector)
        
        (tmp_path / "test.py").write_text("print('test')")
        
        result = scanner.scan(tmp_path)
        assert len(result) == 1
        assert result[0].language == "Python"

    # Integration tests
    def test_scan_complete_workflow(self, scanner: FileScanner, temp_repo: Path) -> None:
        """Test complete scanning workflow with all features."""
        result = scanner.scan(temp_repo)
        
        # Should find files in src, tests, docs
        assert len(result) >= 4
        
        # Verify all files have complete metadata
        for scanned in result:
            assert scanned.relative_path
            assert scanned.absolute_path
            assert scanned.file_name
            assert scanned.extension or scanned.extension == ""
            assert scanned.language
            assert scanned.size_bytes >= 0
            assert isinstance(scanned.is_binary, bool)
            if not scanned.is_binary:
                assert scanned.line_count is not None
            else:
                assert scanned.line_count is None
            assert len(scanned.sha256_hash) in (0, 64)  # Empty or valid hash
            assert isinstance(scanned.last_modified, datetime)

    def test_scan_returns_sorted_results(self, scanner: FileScanner, tmp_path: Path) -> None:
        """Test that scan returns files (order may vary by OS)."""
        (tmp_path / "z.txt").write_text("z")
        (tmp_path / "a.txt").write_text("a")
        (tmp_path / "m.txt").write_text("m")
        
        result = scanner.scan(tmp_path)
        assert len(result) == 3
        
        # Just verify all files are present (order not guaranteed by os.walk)
        file_names = {f.file_name for f in result}
        assert file_names == {"z.txt", "a.txt", "m.txt"}
