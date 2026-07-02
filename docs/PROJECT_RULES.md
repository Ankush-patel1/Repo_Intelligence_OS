# Repo Intelligence OS — Project Rules

## 1. Project Philosophy

- **Build for maintainability, not for speed.** Code is written once and read a hundred times. Optimize for the reader.
- **Prefer boring technology.** Choose well-understood tools over novel ones. Novelty is a liability in production.
- **Make it work, then make it right, then make it fast.** Premature optimization is the root of all evil.
- **Favor composition over inheritance.** Build systems from small, interchangeable parts.
- **Explicit over implicit.** Code should reveal its intent. Magic is acceptable only when it eliminates boilerplate without hiding behavior.
- **Coverage over perfection.** 80% test coverage today is better than 100% coverage next quarter.
- **Documentation is code.** Keep docs in version control, review them in PRs, update them with features.

## 2. Architecture Rules

| Rule | Rationale |
|---|---|
| API handlers must be thin (< 100 lines). Delegate to services. | Prevents business logic from leaking into HTTP layer. |
| Services never import from `api/`. | Services are HTTP-unaware and testable without a client. |
| Repositories never import from `services/` or `api/`. | Data access layer is the lowest dependency. Unidirectional: `api → services → repositories → db`. |
| AI agents live under `backend/app/ai/agents/`. | All AI functionality is grouped for discoverability and future modularization. |
| AI agents never call the database directly. Use services or repositories. | Agents should be testable with mock data, not a real database. |
| Orchestration logic lives in `backend/app/ai/orchestration/`, not in workers. | Workers dispatch; orchestration decides the execution graph. |
| Report builders are separate from exporters. | Builders produce structured data; exporters format it. Adding a new export format must not require touching builder logic. |
| Parser modules are language-specific and share a common interface. | Adding a new language means adding a new parser module without changing existing parsers. |
| No circular imports between `backend/app/` sub-packages. | Enforced via CI. Common pattern: use `TYPE_CHECKING` blocks for type-only imports. |
| Frontend pages are leaf nodes — they import from components, hooks, and services, but nothing imports from pages. | Prevents dependency cycles and enforces component reusability. |
| CSS Modules are co-located with their component. | Encourages self-contained components. Global styles are only for reset, tokens, and animations. |

## 3. Code Quality Rules

- **Type annotations are required** on all Python function signatures and public methods. `mypy --strict` in CI.
- **No `Any` in TypeScript.** Use `unknown` and narrow with type guards.
- **Keep functions under 30 lines.** If a function does more than one thing, split it.
- **Maximum nesting: 3 levels.** Use early returns and guard clauses.
- **No commented-out code.** Delete it. Git history preserves it.
- **No `print()` / `console.log()`**. Use structured logging with correlation IDs.
- **User-facing strings must be defined in constants, not inline.** Enables future i18n.
- **Test files are co-located with source files** (unit tests) or in the appropriate `tests/` directory (integration, e2e).
- **One primary export per module.** Secondary exports are rare and intentional.
- **No barrel files.** Explicit imports prevent circular dependencies and make import chains traceable.

## 4. Security Rules

| Rule | Rationale |
|---|---|
| No secrets in code, config files, or Docker images. Use environment variables or a secret manager. | Even encrypted secrets in code can be extracted from CI logs or Docker layers. |
| GitHub tokens are encrypted at rest and never logged. | Users' GitHub access tokens are sensitive credentials. Encryption provides defense in depth. |
| All API traffic must use TLS 1.3 in production. | Non-negotiable for any SaaS handling user data. |
| Rate limit all endpoints (100 req/min per user default). | Prevents abuse and accidental runaway clients. |
| Analysis queue is depth-limited per user (max 5 concurrent). | Prevents resource exhaustion by a single user. |
| Repository secrets (API keys, tokens in source code) are identified during analysis but never stored. | The Scout agent flags secrets but does not persist them. |
| LLM prompt injection is mitigated by input sanitization and output schema enforcement. | File contents from analyzed repos could contain malicious prompt injection. |
| Dependency scanning runs in CI for every PR. | Catch known CVEs before they reach production. |
| Workers run in a private subnet with no public access. | Reduces attack surface — workers only need outbound access to LLM/GitHub APIs. |

## 5. Performance Rules

- **LLM calls timeout at 120 seconds.** Agents must handle timeout gracefully (retry or degrade).
- **Repository clone timeout: 5 minutes.** Repos exceeding 500 MB or 5-minute clone are rejected.
- **Database queries must have a 30-second timeout.** Long queries are logged and optimized.
- **API response time target: P95 < 500 ms for read endpoints.** Monitor in CI with performance tests.
- **Analysis pipeline target: ≤ 5 minutes for repos under 10K files.** Monitoring dashboards track median and P95 analysis duration.
- **No N+1 queries in repository layer.** Use eager loading or batch queries. Code review gates for this.
- **Frontend bundle size target: < 200 KB (gzipped).** Monitored in CI with bundle analyzer.

## 6. Documentation Rules

- **Every public function and class has a docstring** (Google style for Python, JSDoc for TypeScript). Docstrings explain "why", not "what" — the code should be self-explanatory.
- **Architecture Decision Records (ADRs) in `docs/adr/`** for every significant technical decision. ADRs are immutable once accepted — superseded ADRs get a "Superseded by" header.
- **Runbooks in `docs/runbooks/`** for operational procedures: deploy, rollback, database migration, incident response.
- **CHANGELOG.md follows Keep a Changelog.** Every PR with user-facing changes must update the changelog.
- **README.md contains**: project description, setup instructions, development commands, test commands, and a link to `docs/`.
- **Documentation is reviewed in PRs.** A PR that changes behavior without updating docs should be rejected.

## 7. Definition of Done

A task or user story is "done" when:

1. Code is written and follows all project conventions.
2. Automated tests pass (unit, integration, and where applicable, e2e).
3. Test coverage meets the threshold (≥ 80% line coverage, ≥ 90% for critical paths).
4. Type checking passes (`mypy --strict` for Python, `tsc --noEmit` for TypeScript).
5. Linting passes (Ruff for Python, ESLint for TypeScript).
6. Documentation is updated if behavior changed (docstrings, ADRs, runbooks, README).
7. No secrets or credentials are committed.
8. PR has been reviewed and approved by at least one teammate.
9. All CI checks pass.
10. The feature has been verified in a production-like environment (staging).
11. Monitoring and alerting are in place for any new metrics or error conditions.
12. No regressions in existing functionality.

## 8. AI Development Rules

| Rule | Rationale |
|---|---|
| Every agent extends `BaseAgent` and implements `run()` returning a Pydantic model. | Consistent interface enables the orchestration layer to treat all agents uniformly. |
| Agent output must be structured JSON (Pydantic model), not free text. | Structured output enables validation, merging, and downstream consumption without fragile parsing. |
| Each agent has a dedicated system prompt stored in `ai/prompts/templates/`. | Prompts are version-controlled, reviewable, and separable from agent logic. |
| Agent prompts must include an output schema specification. | LLM needs to know the exact structure to return; schema-in-prompt reduces parse errors. |
| No agent calls an LLM with raw repository content exceeding 32K tokens. | Context window management is handled by the retrieval layer, not by agents. |
| Agents must handle LLM failure gracefully (timeout, invalid JSON, empty response). | LLM APIs are unreliable. Retry logic is built into `BaseAgent`. |
| Agent outputs are validated against their schema before persisting. Invalid outputs trigger a retry. | Prevents garbage data from entering the database. |
| Cross-agent validation is the Validator's responsibility, not individual agents'. | Agents should not know about each other. |
| Prompts must not contain secrets or hardcoded credentials. | Prompts are checked into version control; secrets would leak. |
| Agent evaluation (confidence scoring, quality metrics) is separate from agent execution. | Evaluation can be improved or replaced without touching agent logic. |
