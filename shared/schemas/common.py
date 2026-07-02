from datetime import datetime
from pydantic import BaseModel


class PaginationParams(BaseModel):
    page: int = 1
    per_page: int = 20


class PaginatedResponse(BaseModel):
    data: list
    meta: dict


class ErrorResponse(BaseModel):
    error: dict
    meta: dict


class HealthResponse(BaseModel):
    status: str
    version: str = "1.0.0"
    uptime_seconds: float = 0.0
