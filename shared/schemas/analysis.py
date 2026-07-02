from datetime import datetime
from pydantic import BaseModel
from shared.constants.enums import AnalysisStatus


class AnalysisCreate(BaseModel):
    repository_id: str
    branch: str = "main"
    depth: str = "full"


class AnalysisResponse(BaseModel):
    id: str
    repository_id: str
    status: AnalysisStatus
    branch: str
    depth: str
    created_at: datetime


class AnalysisStatusResponse(BaseModel):
    id: str
    status: AnalysisStatus
    started_at: datetime | None = None
    completed_at: datetime | None = None
    progress: dict | None = None
