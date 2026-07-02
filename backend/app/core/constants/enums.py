ANALYSIS_STATUSES = frozenset({"pending", "in_progress", "completed", "failed", "cancelled"})
FINDING_SEVERITIES = frozenset({"critical", "high", "medium", "low", "info"})
REPORT_SECTION_SLUGS = frozenset({
    "executive_summary",
    "repository_overview",
    "architecture_analysis",
    "feature_inventory",
    "security_audit",
    "performance_review",
    "documentation_review",
    "testing_review",
    "gap_analysis",
    "roadmap",
    "sprint_plan",
})
