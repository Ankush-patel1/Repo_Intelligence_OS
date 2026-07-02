import base64
import subprocess
from pathlib import Path

from app.core.exceptions.base import AppError
from app.core.exceptions.codes import CONFLICT, UPSTREAM_ERROR
from app.services.github.github_client import GitHubRepositoryMetadata


class CloneService:
    def __init__(self, storage_root: str = "data/repos", token: str = "") -> None:
        self.storage_root = Path(storage_root)
        self.token = token

    def clone_or_update(self, metadata: GitHubRepositoryMetadata, branch: str) -> Path:
        clone_path = self.clone_path(metadata.owner, metadata.name)
        if (clone_path / ".git").exists():
            self.pull(clone_path)
            return clone_path
        if clone_path.exists() and any(clone_path.iterdir()):
            raise AppError(
                CONFLICT,
                "Clone path already exists but is not a Git repository.",
                {"clone_path": str(clone_path)},
            )
        self.clone(metadata.clone_url, clone_path, branch)
        return clone_path

    def clone_path(self, owner: str, repository: str) -> Path:
        return self.storage_root / owner / repository

    def clone(self, clone_url: str, clone_path: Path, branch: str) -> None:
        clone_path.parent.mkdir(parents=True, exist_ok=True)
        command = [
            "git",
            *self._auth_options(),
            "clone",
            "--branch",
            branch,
            "--single-branch",
            clone_url,
            str(clone_path),
        ]
        self._run(command)

    def pull(self, clone_path: Path) -> None:
        command = ["git", *self._auth_options(), "-C", str(clone_path), "pull", "--ff-only"]
        self._run(command)

    def _auth_options(self) -> list[str]:
        if not self.token:
            return []
        token = base64.b64encode(f"x-access-token:{self.token}".encode()).decode()
        return ["-c", f"http.https://github.com/.extraheader=AUTHORIZATION: basic {token}"]

    @staticmethod
    def _run(command: list[str]) -> None:
        try:
            subprocess.run(command, check=True, capture_output=True, text=True)
        except FileNotFoundError as exc:
            raise AppError(UPSTREAM_ERROR, "git executable was not found.") from exc
        except subprocess.CalledProcessError as exc:
            raise AppError(
                UPSTREAM_ERROR,
                "Git command failed.",
                {"stderr": exc.stderr.strip(), "returncode": exc.returncode},
            ) from exc
