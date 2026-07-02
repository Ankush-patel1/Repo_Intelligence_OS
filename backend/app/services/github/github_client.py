from dataclasses import dataclass
from http import HTTPStatus
from urllib.parse import urlparse

import httpx

from app.core.exceptions.base import AppError
from app.core.exceptions.codes import FORBIDDEN, UPSTREAM_ERROR, VALIDATION_ERROR

GITHUB_API_BASE_URL = "https://api.github.com"
REPOSITORY_PATH_PARTS = 2


@dataclass(frozen=True)
class GitHubRepositoryMetadata:
    owner: str
    name: str
    full_name: str
    private: bool
    default_branch: str
    clone_url: str
    html_url: str


class GitHubClient:
    def __init__(self, token: str = "", api_base_url: str = GITHUB_API_BASE_URL) -> None:
        self.token = token
        self.api_base_url = api_base_url.rstrip("/")

    async def validate_repository_access(self, repository: str) -> bool:
        await self.fetch_repository_metadata(repository)
        return True

    async def fetch_repository_metadata(self, repository: str) -> GitHubRepositoryMetadata:
        owner, name = self.parse_repository(repository)
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{self.api_base_url}/repos/{owner}/{name}",
                headers=self._headers,
            )

        if response.status_code == HTTPStatus.NOT_FOUND:
            raise AppError(
                FORBIDDEN,
                "Repository was not found or the configured GitHub token cannot access it.",
                {"repository": f"{owner}/{name}"},
            )
        if response.status_code in {HTTPStatus.UNAUTHORIZED, HTTPStatus.FORBIDDEN}:
            raise AppError(
                FORBIDDEN,
                "GitHub rejected the configured token for this repository.",
                {"repository": f"{owner}/{name}", "status_code": response.status_code},
            )
        if response.status_code >= HTTPStatus.BAD_REQUEST:
            raise AppError(
                UPSTREAM_ERROR,
                "GitHub metadata request failed.",
                {"repository": f"{owner}/{name}", "status_code": response.status_code},
            )

        payload = response.json()
        return GitHubRepositoryMetadata(
            owner=payload["owner"]["login"],
            name=payload["name"],
            full_name=payload["full_name"],
            private=payload["private"],
            default_branch=payload["default_branch"],
            clone_url=payload["clone_url"],
            html_url=payload["html_url"],
        )

    @staticmethod
    def parse_repository(repository: str) -> tuple[str, str]:
        value = repository.strip().removesuffix(".git")
        if not value:
            raise AppError(VALIDATION_ERROR, "Repository is required.")

        if value.startswith("http://") or value.startswith("https://"):
            parsed = urlparse(value)
            path_parts = [part for part in parsed.path.strip("/").split("/") if part]
            if parsed.netloc.lower() != "github.com" or len(path_parts) < REPOSITORY_PATH_PARTS:
                raise AppError(
                    VALIDATION_ERROR,
                    "Repository URL must be a GitHub URL in the form https://github.com/owner/repo.",
                    {"repository": repository},
                )
            return path_parts[0], path_parts[1]

        parts = value.split("/")
        if len(parts) != REPOSITORY_PATH_PARTS or not all(parts):
            raise AppError(
                VALIDATION_ERROR,
                "Repository must be in the form owner/repo or a GitHub repository URL.",
                {"repository": repository},
            )
        return parts[0], parts[1]

    @property
    def _headers(self) -> dict[str, str]:
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "repo-intelligence-os",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers
