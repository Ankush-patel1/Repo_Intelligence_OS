from typing import TypedDict


class ReportSection(TypedDict):
    slug: str
    title: str
    content: dict
    score: float | None


class ScoreMap(TypedDict):
    section: str
    score: float
