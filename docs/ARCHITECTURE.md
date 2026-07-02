# Repo Intelligence OS — Architecture

## 1. High-Level Architecture

```
┌─────────────────────┐       ┌──────────────────────────────┐
│     Browser (SPA)   │──────▶│   API Gateway / Load Balancer │
└─────────────────────┘       └──────────────┬───────────────┘
                                             │
                          ┌──────────────────┴──────────────────┐
                          │         Web API (FastAPI)            │
                          │  REST · Auth · Job Management        │
                          └────────┬────────┬───────────────────┘
                                   │        │
                    ┌──────────────┘        └──────────────┐
                    ▼                                       ▼
          ┌─────────────────┐                    ┌──────────────────┐
          │  PostgreSQL DB  │                    │  Task Queue       │
          │  (reports,      │                    │  (RabbitMQ/Redis) │
          │   users, repos) │                    │                   │
          └─────────────────┘                    └────────┬─────────┘
                                                          │
                                                          ▼
                                               ┌─────────────────────┐
                                               │  Worker Fleet        │
                                               │  Agent Pipeline      │
                                               │  · Planner           │
                                               │  · Scout             │
                                               │  · Feature Detective │
                                               │  · Architecture Agent│
                                               │  · Security Agent    │
                                               │  · Performance Agent │
                                               │  · Documentation Ag. │
                                               │  · Testing Agent     │
                                               │  · Gap Analyst      │
                                               │  · Validator        │
                                               │  · Roadmap Planner  │
                                               └────────┬────────────┘
                                                        │
                                                        ▼
                                               ┌─────────────────────┐
                                               │  LLM Provider API   │
                                               │  GitHub API         │
                                               └─────────────────────┘
```

## 2. Frontend Architecture

- **Framework**: React 18+ with TypeScript
- **Routing**: React Router v6 (file-based or declarative)
- **State management**: React Query (server state) + Zustand (client state)
- **UI library**: CSS Modules + headless component primitives (Radix UI)
- **Build tool**: Vite
- **Key patterns**:
  - Components are organized by feature, not by type
  - API layer is a thin typed wrapper around `fetch` with error transformation
  - WebSocket / polling for job status updates
  - Progressive enhancement — skeleton loaders for every async view

## 3. Backend Architecture

- **Framework**: Python 3.11+ with FastAPI
- **ORM**: SQLAlchemy 2.0 (async) with Alembic migrations
- **Task queue**: Celery with Redis broker
- **Background workers**: Separate process pool (workers/), horizontally scalable
- **File storage**: Local disk (MVP) → S3-compatible (future)
- **Auth**: GitHub OAuth via `authlib`, JWT session tokens
- **API style**: RESTful with pagination, filtering, sorting on list endpoints

## 4. AI Pipeline

### 4.1 Pipeline Stages

```
Trigger ──▶ Planner ──▶ Repo Scout ──▶ ┌──────────────────┐
                                        │ Parallel Agents  │
                                        │ · Feature Detect │
                                        │ · Architecture   │
                                        │ · Security       │
                                        │ · Performance    │
                                        │ · Documentation  │
                                        │ · Testing        │
                                        └────────┬─────────┘
                                                 │
                                    ┌────────────▼────────────┐
                                    │  Validator              │
                                    │  Gap Analyst            │
                                    │  Roadmap Planner        │
                                    └────────────┬────────────┘
                                                 │
                                    ┌────────────▼────────────┐
                                    │  Report Aggregator      │
                                    │  (not an agent — merge) │
                                    └─────────────────────────┘
```

### 4.2 LLM Strategy

- Single LLM provider (e.g. OpenAI GPT-4o / Anthropic Claude 3.5 Sonnet).
- Each agent calls the LLM with a specialized system prompt + retrieved context.
- Agent outputs are structured JSON (not free text) to enable validation and aggregation.
- Large files are chunked; chunks are summarized, then summaries are combined.

### 4.3. Context Window Management

- Files > 100 KB are summarized via map-reduce before agent consumption.
- Repository file tree is always included as context.
- Each agent receives only the context it needs (filtered by file type, path patterns).
- Total prompt budget per agent: ≤ 32K tokens (configurable).

## 5. Folder Structure

See `PROJECT_STRUCTURE.md` for the complete and authoritative folder structure. The following is a summary of top-level layout:

```
repo-intelligence-os/
├── frontend/                    # React SPA (see PROJECT_STRUCTURE.md §4)
├── backend/                     # FastAPI server (see PROJECT_STRUCTURE.md §2)
│   ├── app/
│   │   ├── api/                 # Route handlers
│   │   ├── services/            # Business logic
│   │   ├── repositories/        # Data access layer
│   │   ├── ai/                  # All AI: agents, orchestration, retrieval, embeddings, prompts, evaluation
│   │   ├── parser/              # Tree-sitter code parsing (per-language)
│   │   ├── reports/             # Builders, exporters, templates
│   │   ├── integrations/        # GitHub, Jira, Slack, Linear adapters
│   │   ├── security/            # Auth, encryption, rate limiting
│   │   ├── core/                # Config, logging, exceptions, middleware, constants
│   │   ├── db/                  # SQLAlchemy models, session
│   │   └── schemas/             # Pydantic request/response schemas
│   └── ...
├── workers/                     # Celery worker fleet (separate deployment)
├── shared/                      # Schemas, constants, utils shared by backend + workers
├── docs/                        # Project documentation
├── docker/                      # Dockerfiles and Compose files
├── scripts/                     # Build, deploy, maintenance scripts
└── tests/                       # Top-level E2E and cross-service tests
```

## 6. Database Design

See `DATABASE.md` for the full schema.

## 7. API Design

See `API.md` for the full endpoint specification.

## 8. Agent Orchestration Flow

```
1. User POST /api/v1/analyses → creates analysis record (status: pending)
2. Celery task enqueued → worker picks it up
3. Planner agent:
   - Reads repo metadata (name, description, language, topics)
   - Produces analysis plan (which agents to run, priority files)
   - Updates analysis record (status: in_progress)
4. Repo Scout agent:
   - Clones or fetches the repository
   - Builds file tree with metadata (size, language, lines)
   - Stores file index in DB
   - Returns structured repo overview
5. Parallel agents are dispatched via LangGraph (in `backend/app/ai/orchestration/`):
   - Each receives the file index + relevant files (via `backend/app/ai/retrieval/`)
   - Each produces structured findings
   - Each writes findings to the findings table
6. Validator runs after all parallel agents complete:
   - Cross-checks findings for consistency
   - Merges duplicate or overlapping findings
   - Scores confidence levels
7. Gap Analyst:
   - Reviews all findings
   - Identifies what is missing (test coverage gaps, doc gaps, security gaps)
   - Produces gap analysis report
8. Roadmap Planner:
   - Takes findings + gap analysis
   - Produces prioritized roadmap and sprint plan
9. Report Aggregator (service, not agent):
   - Merges all agent outputs into the final report JSON
   - Updates analysis status: completed
10. User notified via polling / WebSocket
```

## 9. Retrieval Flow

```
Agent Request
    │
    ▼
┌────────────────────┐
│  Retrieve Context   │
│  · File index from  │
│    DB (tree + meta) │
│  · Relevant file    │
│    contents (cached)│
│  · Prior findings   │
│    (for validator)  │
└────────┬───────────┘
         │
         ▼
┌────────────────────┐
│  Build Prompt      │
│  · System prompt   │
│    (agent-specific)│
│  · Context window  │
│    assembly        │
│  · Truncation      │
│    strategy        │
└────────┬───────────┘
         │
         ▼
┌────────────────────┐
│  LLM Call          │
│  · Structured      │
│    output (JSON)   │
│  · Retry on failure│
│  · Timeout: 120s   │
└────────┬───────────┘
         │
         ▼
┌────────────────────┐
│  Validate Output   │
│  · Schema check    │
│  · Business rules  │
│  · Retry if invalid│
└────────┬───────────┘
         │
         ▼
    Persist to DB
```

## 10. Error Handling Strategy

| Layer | Strategy |
|---|---|
| API | Consistent error response schema: `{ error: { code, message, details } }`. HTTP status codes follow RFC 7807. |
| Worker | Retry with exponential backoff (3 attempts). Permanent failures stored as `failed` status with error details. |
| LLM | JSON parse failure → re-prompt with stricter schema. Token limit → truncate and retry. Empty response → retry once. |
| GitHub API | 429 → exponential backoff with jitter. 404 → skip file. 403 → credential rotation signal. |
| Database | Connection pooling with retry. Query timeout: 30s. Deadlock retry. |

All errors are logged with correlation IDs. Critical errors trigger alerts.

## 11. Deployment Architecture

```
┌─────────────────────────────────────────────┐
│              Cloud Provider (AWS/GCP)        │
│                                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │  ALB /   │  │  Redis   │  │  RDS     │   │
│  │  CDN     │  │  (cache/ │  │  (PG)    │   │
│  │          │  │   queue) │  │          │   │
│  └────┬─────┘  └──────────┘  └──────────┘   │
│       │                                       │
│  ┌────▼──────────────────┐                   │
│  │  Container Cluster    │                   │
│  │  (ECS / GKE / K8s)    │                   │
│  │                       │                   │
│  │  ┌─────┐ ┌──────────┐│                   │
│  │  │ Web │ │  Worker  ││                   │
│  │  │ API │ │  Fleet   ││                   │
│  │  └─────┘ └──────────┘│                   │
│  └──────────────────────┘                   │
│                                              │
│  ┌──────────────────────────────────┐        │
│  │  Object Storage (S3/GCS)        │        │
│  │  · Repo clones (cached)         │        │
│  │  · Report artifacts             │        │
│  └──────────────────────────────────┘        │
└─────────────────────────────────────────────┘
```

## 12. Security Considerations

| Concern | Mitigation |
|---|---|
| GitHub token exposure | Tokens stored encrypted at rest, scoped to least privilege, never logged. |
| Repository data leaks | All analysis stored encrypted. Reports only accessible by the creating user. |
| LLM prompt injection | Input sanitization on file contents. Agent output schema enforcement. |
| Supply chain | Dependency vulnerability scanning in CI/CD. Lock files required. |
| API abuse | Rate limiting per user (100 req/min). Analysis queue depth limit. |
| Secrets in repos | Scout agent skips files matching `.gitignore` + common secret patterns. Analysis never stores credentials. |
| Network | All traffic over TLS 1.3. Workers in private subnet. No public DB access. |
