import hashlib
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from app.services.indexing.language_detector import LanguageDetector

IGNORED_DIRECTORIES = {
    ".git",
    "node_modules",
    "dist",
    "build",
    "venv",
    ".venv",
    "__pycache__",
    "coverage",
    ".next",
    "target",
}
MAX_INDEXED_FILE_SIZE_BYTES = 2 * 1024 * 1024
BINARY_SAMPLE_SIZE = 8192
READ_CHUNK_SIZE = 1024 * 1024


@dataclass(frozen=True)
class ScannedFile:
    relative_path: str
    absolute_path: str
    file_name: str
    extension: str
    language: str
    size_bytes: int
    line_count: int | None
    sha256_hash: str
    last_modified: datetime
    is_binary: bool


class FileScanner:
    def __init__(
        self,
        language_detector: LanguageDetector | None = None,
        max_file_size_bytes: int = MAX_INDEXED_FILE_SIZE_BYTES,
    ) -> None:
        self.language_detector = language_detector or LanguageDetector()
        self.max_file_size_bytes = max_file_size_bytes

    def scan(self, repository_path: str | Path) -> list[ScannedFile]:
        root = Path(repository_path).resolve()
        scanned_files: list[ScannedFile] = []
        if not root.exists() or not root.is_dir():
            return scanned_files

        for current_root, dir_names, file_names in os.walk(root):
            dir_names[:] = [name for name in dir_names if name not in IGNORED_DIRECTORIES]
            current_path = Path(current_root)
            for file_name in file_names:
                path = current_path / file_name
                try:
                    stat = path.stat()
                except OSError:
                    continue
                if stat.st_size > self.max_file_size_bytes:
                    continue
                scanned_files.append(self._scan_file(root, path, stat.st_size, stat.st_mtime))
        return scanned_files

    def _scan_file(self, root: Path, path: Path, size_bytes: int, modified_timestamp: float) -> ScannedFile:
        is_binary = self._is_binary(path)
        return ScannedFile(
            relative_path=path.relative_to(root).as_posix(),
            absolute_path=str(path.resolve()),
            file_name=path.name,
            extension=path.suffix.lower(),
            language=self.language_detector.detect(path),
            size_bytes=size_bytes,
            line_count=None if is_binary else self._count_lines(path),
            sha256_hash=self._sha256(path),
            last_modified=datetime.fromtimestamp(modified_timestamp, tz=UTC),
            is_binary=is_binary,
        )

    @staticmethod
    def _is_binary(path: Path) -> bool:
        try:
            with path.open("rb") as file:
                return b"\0" in file.read(BINARY_SAMPLE_SIZE)
        except OSError:
            return True

    @staticmethod
    def _count_lines(path: Path) -> int:
        line_count = 0
        try:
            with path.open("rb") as file:
                for line_count, _line in enumerate(file, start=1):
                    pass
        except OSError:
            return 0
        return line_count

    @staticmethod
    def _sha256(path: Path) -> str:
        digest = hashlib.sha256()
        try:
            with path.open("rb") as file:
                for chunk in iter(lambda: file.read(READ_CHUNK_SIZE), b""):
                    digest.update(chunk)
        except OSError:
            return ""
        return digest.hexdigest()
