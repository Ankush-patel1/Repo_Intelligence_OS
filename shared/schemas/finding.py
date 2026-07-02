from datetime import datetime
from pydantic import BaseModel
from shared.constants.enums import FindingSeverity


class FindingResponse(BaseModel):
    id: str
    analysis_id: str
    agent_name: str
    finding_type: str
    severity: FindingSeverity
    confidence: float
    title: str
    description: str
    location: dict | None = None
    evidence: str | None = None
    recommendation: str | None = None
    is_validated: bool
    created_at: datetime
