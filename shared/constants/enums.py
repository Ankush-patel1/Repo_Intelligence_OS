from enum import Enum


class AnalysisStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class FindingSeverity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class AgentName(str, Enum):
    PLANNER = "planner"
    REPO_SCOUT = "repo_scout"
    FEATURE_DETECTIVE = "feature_detective"
    ARCHITECTURE_AGENT = "architecture_agent"
    SECURITY_AGENT = "security_agent"
    PERFORMANCE_AGENT = "performance_agent"
    DOCUMENTATION_AGENT = "documentation_agent"
    TESTING_AGENT = "testing_agent"
    GAP_ANALYST = "gap_analyst"
    VALIDATOR = "validator"
    ROADMAP_PLANNER = "roadmap_planner"


class RoadmapPhase(str, Enum):
    IMMEDIATE = "immediate"
    SHORT_TERM = "short_term"
    MEDIUM_TERM = "medium_term"
    LONG_TERM = "long_term"


class Priority(str, Enum):
    P0 = "p0"
    P1 = "p1"
    P2 = "p2"
    P3 = "p3"
