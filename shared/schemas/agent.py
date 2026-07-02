from pydantic import BaseModel


class AgentOutput(BaseModel):
    agent_name: str
    findings: list[dict]
    metadata: dict | None = None


class AnalysisPlan(BaseModel):
    agents: list[str]
    priority_files: list[str]
    depth: str


class RepoOverview(BaseModel):
    file_tree: list[dict]
    technologies: list[str]
    total_files: int
    total_lines: int
    languages: list[dict]
