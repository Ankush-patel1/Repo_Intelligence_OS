from typing import Literal

AgentType = Literal[
    "planner",
    "repo_scout",
    "feature_detective",
    "architecture_agent",
    "security_agent",
    "performance_agent",
    "documentation_agent",
    "testing_agent",
    "gap_analyst",
    "validator",
    "roadmap_planner",
]

SeverityLevel = Literal["critical", "high", "medium", "low", "info"]

PhaseType = Literal["immediate", "short_term", "medium_term", "long_term"]
