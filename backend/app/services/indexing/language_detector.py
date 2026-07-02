from pathlib import Path

LANGUAGE_BY_EXTENSION = {
    ".py": "Python",
    ".js": "JavaScript",
    ".jsx": "JavaScript",
    ".mjs": "JavaScript",
    ".cjs": "JavaScript",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".java": "Java",
    ".c": "C",
    ".h": "C",
    ".cpp": "C++",
    ".cc": "C++",
    ".cxx": "C++",
    ".hpp": "C++",
    ".hh": "C++",
    ".go": "Go",
    ".rs": "Rust",
    ".md": "Markdown",
    ".markdown": "Markdown",
    ".json": "JSON",
    ".yml": "YAML",
    ".yaml": "YAML",
    ".html": "HTML",
    ".htm": "HTML",
    ".css": "CSS",
    ".sql": "SQL",
}


class LanguageDetector:
    def detect(self, path: Path) -> str:
        return LANGUAGE_BY_EXTENSION.get(path.suffix.lower(), "Unknown")
