import subprocess
from pathlib import Path

import pytest

from app.core.exceptions.base import AppError
from app.services.github.clone_service import CloneService
from app.services.github.github_client import GitHubClient


def test_parse_repository_accepts_full_name() -> None:
    assert GitHubClient.parse_repository("octocat/Hello-World") == ("octocat", "Hello-World")


def test_parse_repository_accepts_github_url() -> None:
    assert GitHubClient.parse_repository("https://github.com/octocat/Hello-World.git") == (
        "octocat",
        "Hello-World",
    )


def test_parse_repository_rejects_invalid_value() -> None:
    with pytest.raises(AppError) as exc_info:
        GitHubClient.parse_repository("not-a-repo")

    assert exc_info.value.code == "validation_error"


def test_github_client_uses_token_header() -> None:
    client = GitHubClient(token="ghp_test")

    assert client._headers["Authorization"] == "Bearer ghp_test"


def test_clone_service_builds_clone_command(monkeypatch: pytest.MonkeyPatch) -> None:
    commands: list[list[str]] = []

    def fake_run(command, *_args, **_kwargs):
        commands.append(command)
        return subprocess.CompletedProcess(command, 0)

    def fake_mkdir(*_args, **_kwargs) -> None:
        return None

    monkeypatch.setattr(subprocess, "run", fake_run)
    monkeypatch.setattr(Path, "mkdir", fake_mkdir)

    CloneService(storage_root="data/repos").clone(
        "https://github.com/octocat/Hello-World.git",
        Path("data/repos/octocat/Hello-World"),
        "main",
    )

    assert commands[0] == [
        "git",
        "clone",
        "--branch",
        "main",
        "--single-branch",
        "https://github.com/octocat/Hello-World.git",
        "data\\repos\\octocat\\Hello-World",
    ]


def test_clone_service_builds_pull_command(monkeypatch: pytest.MonkeyPatch) -> None:
    commands: list[list[str]] = []

    def fake_run(command, *_args, **_kwargs):
        commands.append(command)
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(subprocess, "run", fake_run)

    CloneService(storage_root="data/repos").pull(Path("data/repos/octocat/Hello-World"))

    assert commands[0] == [
        "git",
        "-C",
        "data\\repos\\octocat\\Hello-World",
        "pull",
        "--ff-only",
    ]
