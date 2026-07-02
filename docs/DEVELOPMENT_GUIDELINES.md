# Repo Intelligence OS — Development Guidelines

## 1. Coding Conventions

### 1.1 General

- Favor readability over brevity. Code is written once, read many times.
- Avoid premature optimization. Profile first, optimize second.
- Keep functions small (< 30 lines). If a function does more than one thing, split it.
- Avoid deep nesting (max 3 levels). Use early returns and guard clauses.
- No commented-out code. Delete it.
- No `print()` / `console.log()` — use structured logging.
- All user-facing strings must be defined in a constants / i18n module, not inline.

### 1.2 Python (Backend)

- Type annotations required for all function signatures and public methods.
- Use `mypy --strict` for static type checking.
- Follow PEP 8 (line length: 100 chars).
- Use Pydantic v2 for all data validation (request/response schemas, configs).
- Imports order: standard library → third-party → local (groups separated by blank line).
- Use `async`/`await` for I/O-bound operations. Use `anyio` or `asyncio` primitives.
- Prefer composition over inheritance. Agents extend `BaseAgent`; services are composition-based.
- Error handling: raise domain-specific exceptions (e.g. `AnalysisNotFoundError`) — not generic `Exception`.

### 1.3 TypeScript (Frontend)

- Strict mode enabled in `tsconfig.json`.
- Prefer `interface` over `type` for object shapes. Use `type` for unions and primitives.
- No `any`. Use `unknown` and narrow with type guards when necessary.
- File naming: `PascalCase` for components, `camelCase` for utilities and hooks.
- Export only what is consumed externally. Co-locate tests with the module.
- Use `const` assertions for literal types. Use `as const` sparingly — prefer satisfies.
- Event handlers: prefix with `handle` (e.g. `handleSubmit`, `handleClick`).

## 2. Folder Conventions

### 2.1 Backend

```
app/
├── api/                    # Route handlers — thin layer, calls services
│   ├── deps.py             # FastAPI dependencies (auth, DB session)
│   └── v1/                 # Versioned routes
├── services/               # Business logic — no HTTP awareness
├── repositories/           # Data access layer (DAO pattern)
├── ai/
│   ├── agents/             # Agent implementations extending BaseAgent
│   ├── orchestration/      # LangGraph pipeline graph
│   ├── retrieval/          # File chunking, context assembly
│   ├── embeddings/         # FAISS vector index, similarity search
│   ├── prompts/            # Prompt templates, registry, few-shot examples
│   └── evaluation/         # Confidence scoring, validation
├── parser/                 # Tree-sitter parsing per language
│   ├── base.py
│   ├── python/
│   ├── javascript/
│   ├── typescript/
│   └── generic/
├── reports/
│   ├── builders/           # Per-section report builders
│   ├── exporters/          # Markdown, JSON export
│   └── templates/          # Report structure templates
├── integrations/           # GitHub, Jira, Slack, Linear adapters
├── security/               # Auth, encryption, rate limiting, scanning
├── core/
│   ├── config/             # Pydantic-settings
│   ├── logging/            # Structured logging
│   ├── exceptions/         # Domain exception hierarchy
│   ├── middleware/         # ASGI middleware
│   └── constants/          # App-wide constants
├── db/                     # SQLAlchemy models, session factory, base
└── schemas/                # Pydantic models (one file per domain entity)
```

### 2.2 Frontend

```
src/
├── layouts/       # Page-level layout components (RootLayout, AppLayout, AuthLayout)
├── pages/         # Top-level route pages — each folder is a route
│   ├── Dashboard/
│   ├── Analyze/
│   ├── History/
│   ├── Reports/
│   └── Settings/
├── components/    # Shared UI components (Button, Card, Modal, Badge, etc.)
├── hooks/         # Shared custom hooks (useAnalyses, useAuth, usePolling, etc.)
├── services/      # Typed API client (auth, analyses, reports, repositories, users)
├── types/         # Shared TypeScript type definitions
├── assets/        # Static assets (icons, images, fonts)
└── styles/        # Global styles (reset, design tokens, utilities, animations)
```

- Each page folder contains: `PageName.tsx`, `PageName.module.css`, `PageName.test.tsx`, plus `components/` and `hooks/` subfolders for page-specific code.
- Shared components go in `components/`. Page-specific components stay in the page folder.

## 3. Naming Conventions

| Artifact | Convention | Example |
|---|---|---|
| Python files | `snake_case` | `security_agent.py` |
| Python classes | `PascalCase` | `SecurityAgent` |
| Python functions | `snake_case` | `get_analysis_by_id()` |
| Python constants | `UPPER_SNAKE_CASE` | `MAX_RETRY_COUNT` |
| Python test functions | `test_<scenario>` | `test_analysis_fails_on_timeout()` |
| Prompt template files | `snake_case.txt` | `planner.txt`, `security_agent.txt` |
| Tree-sitter query files | `queries.scm` | `queries.scm` |
| TypeScript files | `PascalCase` (components), `camelCase` (utils) | `ReportView.tsx`, `formatDate.ts` |
| TypeScript components | `PascalCase` | `ReportView` |
| TypeScript functions | `camelCase` | `fetchAnalyses()` |
| TypeScript interfaces | `PascalCase` | `AnalysisResponse` |
| TypeScript CSS Modules | `<ComponentName>.module.css` | `Button.module.css` |
| SVG icons | `kebab-case.svg` | `github-icon.svg` |
| SQL tables | `snake_case`, plural | `analyses`, `roadmap_items` |
| SQL columns | `snake_case` | `created_at` |
| Alembic revisions | `auto` (timestamp prefix) | `20260702_1200_add_finding_table.py` |
| API endpoint paths | `kebab-case` | `/api/v1/roadmap-items` |
| JSON keys (API) | `snake_case` | `agent_name`, `finding_type` |
| Git branches | `kebab-case` with type prefix | `feat/parallel-agents`, `fix/scout-timeout` |
| Docker images | lowercase | `rio-api`, `rio-worker` |
| Environment variables | `UPPER_SNAKE_CASE` with `RIO_` prefix | `RIO_DATABASE_URL` |

## 4. Git Conventions

### 4.1 Branch Strategy

- `main` — production-ready, protected, requires PR + review.
- `develop` — integration branch (optional for small teams; main can serve as both).
- Feature branches: `feat/<description>`.
- Bug fixes: `fix/<description>`.
- Chores: `chore/<description>`.
- Docs: `docs/<description>`.

### 4.2 Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <short summary>

[optional body]
```

Types: `feat`, `fix`, `chore`, `docs`, `refactor`, `test`, `style`, `ci`, `perf`.

Examples:
```
feat(agents): add parallel execution for analysis agents
fix(api): handle missing GitHub token in analysis trigger
docs(architecture): update deployment diagram
```

### 4.3 Pull Requests

- PR title follows conventional commit format.
- Description includes: what, why, how to test.
- Link to related issue if applicable.
- Request review from at least one teammate.
- Squash-merge to `main` (keep history clean).

## 5. Error Handling Conventions

### 5.1 Backend

- Define domain exceptions in `app/core/exceptions.py`.
- Use FastAPI exception handlers to convert exceptions to HTTP responses.
- Never expose stack traces to the client. Log them with correlation ID.
- Every service function either returns a result or raises a domain exception.
- Background task errors: caught, logged, persisted to `analysis_errors` table, task marked as failed.

```python
class AppError(Exception):
    def __init__(self, code: str, message: str, details: dict | None = None):
        self.code = code
        self.message = message
        self.details = details or {}

class AnalysisNotFoundError(AppError):
    def __init__(self, analysis_id: UUID):
        super().__init__("analysis_not_found", "Analysis not found", {"analysis_id": str(analysis_id)})
```

### 5.2 Frontend

- API errors are transformed by the API layer into structured `ApiError` objects.
- Components handle error states via error boundaries and React Query's `onError`.
- User-facing errors use a consistent toast or inline banner component.
- Network errors show "Connection lost. Retrying..." with automatic retry.
- Form validation errors are displayed inline next to the relevant field.

## 6. Testing Conventions

### 6.1 Philosophy

- Test behavior, not implementation.
- Write tests that read like specifications.
- A test should fail for exactly one reason.

### 6.2 Backend

- **Unit tests**: Pure function and service tests. Mock external calls (LLM, GitHub API, DB).
- **Integration tests**: Test API endpoints with a test database. Use `httpx.AsyncClient` with FastAPI's `TestClient`.
- **Agent tests**: Fixture-based. Each agent has a fixture repository and expected output snapshot.
- **Coverage target**: ≥ 80% line coverage. Critical paths (auth, analysis pipeline) ≥ 90%.
- Test directories mirror source: `tests/unit/services/`, `tests/unit/ai/agents/`, `tests/integration/api/v1/`.
- Fixtures in `tests/fixtures/` — sample repos, agent outputs, mock LLM responses.

### 6.3 Frontend

- **Unit tests**: Component rendering, hooks, utils. Use Vitest + React Testing Library.
- **Integration tests**: Feature workflows (login → analyze → view report). Use MSW for API mocking.
- **Accessibility tests**: `jest-axe` for automated a11y checks on every component.
- Test files are co-located: `src/pages/Dashboard/Dashboard.test.tsx`.

### 6.4 Naming

- `test_<function_name>_<scenario>` (backend)
- `<ComponentName>.test.tsx` (frontend)

## 7. Documentation Conventions

- **Code docs**: Docstrings for all public functions and classes (Google style for Python, JSDoc for TypeScript). No comments explaining "what" — the code should be self-explanatory. Comments explain "why".
- **Architecture decisions**: Recorded as ADRs in `docs/adr/` for significant decisions (e.g. "Use Celery over Arq", "PostgreSQL over MongoDB").
- **API documentation**: Auto-generated from Pydantic schemas + FastAPI's OpenAPI. Hand-written only for developer guides.
- **Runbooks**: `docs/runbooks/` for operational procedures (deploy, rollback, database migration, incident response).
- **README**: Setup, development, testing, and deployment instructions.
- **Changelog**: `CHANGELOG.md` following [Keep a Changelog](https://keepachangelog.com/) format.

## 8. Code Review Standards

- Every PR requires at least one approval before merging.
- Reviewers check for:
  - Correctness — does the code do what it claims?
  - Test coverage — are there tests for the new code?
  - Error handling — are failure paths handled?
  - Security — are there any obvious vulnerabilities?
  - Performance — is there any obviously inefficient code?
  - Style — does it follow these guidelines?
- Address all review comments before merging. Use "Resolve conversation" when addressed.
- No self-approvals. No merging your own PR (except for urgent hotfixes with post-merge review).

## 9. Tooling

| Purpose | Backend | Frontend |
|---|---|---|
| Linting | Ruff | ESLint (flat config) |
| Formatting | Ruff | Prettier |
| Type checking | mypy | tsc |
| Testing | pytest | Vitest |
| Coverage | pytest-cov | c8 / istanbul |
| CI | GitHub Actions | GitHub Actions |
