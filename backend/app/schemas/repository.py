import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class RepositoryImportRequest(BaseModel):
    repository: str = Field(..., examples=["octocat/Hello-World"])
    branch: str | None = None


class RepositoryResponse(BaseModel):
    id: uuid.UUID
    owner: str
    name: str
    full_name: str
    branch: str
    clone_path: str
    private: bool
    default_branch: str
    last_synced: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class RepositoryFileCreate(BaseModel):
    repository_id: uuid.UUID
    relative_path: str
    absolute_path: str
    file_name: str
    extension: str
    language: str
    size_bytes: int
    line_count: int | None = None
    sha256_hash: str
    last_modified: datetime
    is_binary: bool = False


class RepositoryFileResponse(BaseModel):
    id: uuid.UUID
    repository_id: uuid.UUID
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
    created_at: datetime

    model_config = {"from_attributes": True}


class LargestFile(BaseModel):
    """Information about a large file."""

    relative_path: str
    language: str
    size_bytes: int


class RepositoryStatistics(BaseModel):
    """Statistics about repository files."""

    total_files: int
    files_per_language: dict[str, int]
    total_bytes: int
    largest_files: list[LargestFile]
    binary_file_count: int


class RepositoryIndexResponse(BaseModel):
    """Response from indexing operation."""

    repository_id: uuid.UUID
    statistics: RepositoryStatistics
