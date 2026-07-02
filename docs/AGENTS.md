# Repo Intelligence OS — Agent Specifications

All agents live in `backend/app/ai/agents/` and extend a common `BaseAgent` (defined in `base.py`) that provides:
- LLM call with retry logic
- Structured output parsing
- Context retrieval from `ai/retrieval/`
- Logging with correlation ID

---

## 1. Planner

| Field | Description |
|---|---|
| **Purpose** | Create the analysis plan for a repository. Determines which agents to run, which files are high-priority, and configures analysis depth. |
| **Inputs** | Repository name, URL, default branch, language, topics, description, file count, total size. |
| **Outputs** | `AnalysisPlan`: agents list, priority file paths, depth configuration (full / shallow), estimated duration. |
| **Tools** | LLM call only. Reads repo metadata from DB. |
| **Prompt strategy** | System prompt defines analysis planning as a classification task. Few-shot examples for different repo types (monolith, microservices, library, framework). |
| **Failure conditions** | Repo metadata unavailable → abort. LLM returns invalid plan → retry once with stricter schema. |
| **Validation rules** | Output must contain at least the standard agent list. Priority files must exist in repo file tree. Depth must be one of: `full`, `shallow`. |

## 2. Repo Scout

| Field | Description |
|---|---|
| **Purpose** | Fetch and index the repository. Clone (or fetch archive), build a complete file tree with metadata, detect technologies used, and produce a repository overview. |
| **Inputs** | Repository URL, branch, access token, analysis depth. |
| **Outputs** | `RepoOverview`: file tree (paths, sizes, languages), detected technologies, total stats (files, lines, languages), README summary, license info, branch count, contributor count. |
| **Tools** | Git CLI (clone / fetch), GitHub API (metadata, contributors, branches), file system traversal. |
| **Prompt strategy** | Summarizes README and key config files. No per-file LLM analysis — this agent is data-collection heavy, LLM-light. |
| **Failure conditions** | Clone fails (repo not found, no access) → fail with `repo_unreachable`. Clone exceeds 500 MB → abort with `repo_too_large`. Git LFS files → skip with warning. |
| **Validation rules** | File tree must be a non-empty list. Every file path must be relative. Total size must match sum of file sizes within tolerance. |

## 3. Feature Detective

| Field | Description |
|---|---|
| **Purpose** | Identify and catalog all features, modules, and capabilities in the repository. Produces a feature inventory. |
| **Inputs** | File tree, all source files (filtered by extension), package manifests, config files, README. |
| **Outputs** | `FeatureInventory`: list of features with name, description, location (paths), dependencies, estimated complexity, status (active / deprecated / experimental). |
| **Tools** | LLM call, file content retrieval. |
| **Prompt strategy** | Prompts the LLM to think like a product manager reading a codebase. Feature identification is guided by: entry points, route definitions, CLI commands, API endpoints, package exports, UI components. |
| **Failure conditions** | Repository has zero source files → empty inventory with warning. LLM hallucinates features → mitigated by requiring file path evidence for each feature. |
| **Validation rules** | Each feature must reference ≥1 file path that exists. Feature names must be unique. Status enum: `active`, `deprecated`, `experimental`. |

## 4. Architecture Agent

| Field | Description |
|---|---|
| **Purpose** | Analyze the software architecture: patterns used, component structure, dependency graph, layering, and design decisions. |
| **Inputs** | File tree, source files (entry points, main modules), dependency manifests (package.json, requirements.txt, etc.), architectural config files (Dockerfile, CI configs, etc.). |
| **Outputs** | `ArchitectureAnalysis`: architectural patterns detected, component inventory, layer diagram (text), dependency analysis, tech stack summary, architectural risks, recommendations. |
| **Tools** | LLM call, file content retrieval, dependency graph analysis (simple adjacency from imports). |
| **Prompt strategy** | Prompts the LLM as a software architect conducting a codebase review. Focuses on: separation of concerns, coupling, cohesion, framework usage, dependency management, configuration philosophy. |
| **Failure conditions** | No recognizable architecture patterns → report as "unstructured" rather than failing. |
| **Validation rules** | Must identify ≥1 architectural pattern (or explicitly state "none detected"). Risks must be actionable (not generic). Recommendations must link to detected patterns. |

## 5. Security Agent

| Field | Description |
|---|---|
| **Purpose** | Identify security vulnerabilities, exposed secrets, dependency risks, and unsafe patterns. |
| **Inputs** | File tree, source files, dependency manifests, Dockerfile, CI configs, environment file examples. |
| **Outputs** | `SecurityAudit`: vulnerability list (severity, location, description, CVE if applicable), secret exposure findings, dependency risk summary, OWASP Top 10 mapping, recommendations. |
| **Tools** | LLM call, file content retrieval, regex-based secret scanner (API keys, tokens, passwords in code), dependency check (version vs known CVEs via external feed or bundled DB). |
| **Prompt strategy** | Two-phase: (1) automated scanner (regex + dep check) produces preliminary findings, (2) LLM reviews findings + scans code for logical vulnerabilities (SQL injection, XSS, auth bypass, SSRF, etc.). |
| **Failure conditions** | LLM finds no issues and scanner finds no issues → report as "no vulnerabilities detected" (not a failure). Scanner exceeds memory limit → fall back to LLM-only analysis. |
| **Validation rules** | Findings must be classified as: `critical`, `high`, `medium`, `low`, `info`. Each finding must include a file path and line range. Severity must follow defined rubric (not arbitrary). |

## 6. Performance Agent

| Field | Description |
|---|---|
| **Purpose** | Analyze code for performance anti-patterns, inefficient algorithms, unnecessary I/O, and scalability bottlenecks. |
| **Inputs** | File tree, source files (hot paths, loops, DB queries, API handlers), dependency manifests. |
| **Outputs** | `PerformanceReview`: performance findings (severity, location, description), detected anti-patterns, bottleneck analysis, recommendations with estimated impact. |
| **Tools** | LLM call, file content retrieval. |
| **Prompt strategy** | Prompts as a performance engineer. Focus areas: N+1 queries, unnecessary allocations, synchronous I/O in async context, large payloads, missing caching, O(n²) algorithms in hot paths. |
| **Failure conditions** | No performance-relevant code → report as "no significant issues detected." |
| **Validation rules** | Findings must include code evidence. Impact must be estimated: `high`, `medium`, `low`. Recommendations must include a suggested fix approach (not specific code — this is analysis, not remediation). |

## 7. Documentation Agent

| Field | Description |
|---|---|
| **Purpose** | Evaluate documentation quality, completeness, and coverage. |
| **Inputs** | File tree, all documentation files (README, CONTRIBUTING, CHANGELOG, docs/ folder, inline comments, API docs, ADRs). |
| **Outputs** | `DocumentationReview`: doc coverage by area, quality score, missing documentation gaps, API documentation status, inline documentation quality, recommendations. |
| **Tools** | LLM call, file content retrieval. |
| **Prompt strategy** | Scoring rubric: README completeness (0–10), API coverage (0–10), architecture documentation (0–10), contribution guide (0–10), inline doc density. Gap identification based on source-to-doc ratio. |
| **Failure conditions** | No documentation files → score of 0, not a failure. |
| **Validation rules** | Scores must be 0–10 integers. Each gap must reference what is undocumented (e.g. "Module X has no README"). Recommendations must be specific and prioritized. |

## 8. Testing Agent

| Field | Description |
|---|---|
| **Purpose** | Evaluate test coverage, testing strategy, test quality, and CI testing practices. |
| **Inputs** | File tree, test files, CI configs, test framework configs, coverage reports (if available), source-to-test mapping. |
| **Outputs** | `TestingReview`: test coverage analysis (by module), test quality assessment, testing approach (unit / integration / e2e), CI testing pipeline evaluation, gaps and recommendations. |
| **Tools** | LLM call, file content retrieval, basic coverage mapping (test file per source file). |
| **Prompt strategy** | Two-phase: (1) mapping phase — pairs test files with source files, computes coverage ratios, (2) quality phase — LLM evaluates test structure, naming, assertion quality, mocking strategy. |
| **Failure conditions** | No test files → score of 0, not a failure. Coverage report not found → estimate from test-to-source ratio. |
| **Validation rules** | Coverage must be reported per module. Test quality score (0–10) must be justified with specific examples. Must distinguish unit, integration, and e2e coverage. |

## 9. Gap Analyst

| Field | Description |
|---|---|
| **Purpose** | Cross-reference all agent outputs to identify gaps, inconsistencies, and missing capabilities. Produces a product gap analysis. |
| **Inputs** | All agent outputs, file tree, original analysis plan. |
| **Outputs** | `GapAnalysis`: missing features (compared to similar repos / industry standards), documentation gaps, test coverage gaps, security gaps, architectural gaps, priority-ordered list. |
| **Tools** | LLM call, finding comparison logic. |
| **Prompt strategy** | System prompt defines "gap" as: (a) something that should exist but does not, (b) something that exists but is insufficient, (c) inconsistency between agents' findings. Uses industry heuristics (e.g. "a repo with a database should have migrations"). |
| **Failure conditions** | No gaps identified → report as "no significant gaps detected." |
| **Validation rules** | Each gap must reference evidence from another agent's output. Gaps must be categorized: `missing`, `incomplete`, `inconsistent`. Priority: `critical`, `high`, `medium`, `low`. |

## 10. Validator

| Field | Description |
|---|---|
| **Purpose** | Validate and cross-check all agent outputs for consistency, accuracy, and completeness. Merges duplicates and scores confidence. |
| **Inputs** | All agent outputs from a single analysis run. |
| **Outputs** | `ValidationReport`: consistency check results, merged findings list, confidence scores per finding, cross-references, potential conflicts. |
| **Tools** | LLM call, deduplication logic (similarity scoring on finding descriptions). |
| **Prompt strategy** | Presents all agent findings and asks the LLM to: (1) identify contradictions, (2) flag duplicates, (3) score confidence. The validator is opinionated — its output shapes the final report's emphasis. |
| **Failure conditions** | LLM finds a contradiction it cannot resolve → flag as `needs_review` rather than resolving. |
| **Validation rules** | Must produce a deduplicated findings list. Each finding must have a confidence score (0.0–1.0). Contradictions must be surfaced with both sides documented. Duplicates must reference original finding IDs. |

## 11. Roadmap Planner

| Field | Description |
|---|---|
| **Purpose** | Transform validated findings and gap analysis into a prioritized, phased roadmap and actionable sprint plan. |
| **Inputs** | Validated findings, gap analysis, repo metadata, tech stack. |
| **Outputs** | `Roadmap`: prioritized roadmap items (title, description, effort estimate, priority, phase), sprint plan (sprints with items, dependencies, suggested assignments), effort breakdown. |
| **Tools** | LLM call, prioritization logic. |
| **Prompt strategy** | Guides the LLM to act as a product manager + tech lead. Prioritization uses a simple rubric: (impact × urgency) / effort. Phases: Immediate (0–2 weeks), Short-term (2–6 weeks), Medium-term (6–12 weeks), Long-term (12+ weeks). |
| **Failure conditions** | No findings to prioritize → return empty roadmap (analysis found nothing actionable). Effort estimation unreasonable → constrain to t-shirt sizes (S/M/L/XL). |
| **Validation rules** | Each roadmap item must link to ≥1 finding ID. Effort must be S/M/L/XL. Phases must be exactly: `immediate`, `short_term`, `medium_term`, `long_term`. Sprint plan must have 2-week sprints with no gaps between phases. |
