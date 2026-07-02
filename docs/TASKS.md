# Repo Intelligence OS — Tasks & Milestones

---

## Milestone 1: Foundation

**Objective**: Establish the project skeleton, development environment, and CI/CD pipeline.

**Deliverables**:
- [ ] Initialize monorepo structure (frontend, backend, docs)
- [ ] Backend: FastAPI project with health check endpoint
- [ ] Frontend: React + Vite + TypeScript scaffold
- [ ] Docker Compose for local development (PostgreSQL, Redis, API, worker)
- [ ] Database migrations (Alembic) with initial schema
- [ ] CI pipeline (lint, type-check, test)
- [ ] Shared configuration management (env vars, secrets)
- [ ] GitHub OAuth integration (login flow, token exchange)
- [ ] README with setup instructions

**Dependencies**: None

**Estimated complexity**: Medium (5–7 days)

---

## Milestone 2: Repository Analysis Core

**Objective**: Implement the analysis pipeline from trigger to completion.

**Deliverables**:
- [ ] API endpoint: `POST /api/v1/analyses` (trigger analysis)
- [ ] Celery task queue integration (`workers/`)
- [ ] Base agent class with LLM call, retry, structured output (`backend/app/ai/agents/base.py`)
- [ ] Planner agent
- [ ] Repo Scout agent (clone, file tree, metadata)
- [ ] LangGraph orchestration scaffolding (`backend/app/ai/orchestration/`)
- [ ] Analysis status tracking (pending → in_progress → completed / failed)
- [ ] File content retrieval service (cached reads, chunking)
- [ ] WebSocket / polling for real-time status updates

**Dependencies**: Milestone 1

**Estimated complexity**: High (10–14 days)

---

## Milestone 3: AI Agents & Pipeline

**Objective**: Build all analysis agents and the AI orchestration pipeline.

**Deliverables**:
- [ ] BaseAgent class (`backend/app/ai/agents/base.py`)
- [ ] Agent prompt templates (`backend/app/ai/prompts/templates/`)
- [ ] Feature Detective agent
- [ ] Architecture Agent
- [ ] Security Agent (with regex secret scanner)
- [ ] Performance Agent
- [ ] Documentation Agent
- [ ] Testing Agent
- [ ] Agent output schema definitions (`shared/schemas/agent.py`)
- [ ] LangGraph orchestration graph (`backend/app/ai/orchestration/`)
- [ ] File chunking and context retrieval (`backend/app/ai/retrieval/`)
- [ ] FAISS embedding and vector search (`backend/app/ai/embeddings/`)
- [ ] Tree-sitter parser per language (`backend/app/parser/`)
- [ ] Agent timeout and error handling
- [ ] Agent logging and telemetry

**Dependencies**: Milestone 2 (base agent, context retrieval)

**Estimated complexity**: High (14–18 days)

---

## Milestone 4: Aggregation & Reporting

**Objective**: Combine agent outputs into final reports and expose them via the API.

**Deliverables**:
- [ ] Validator agent (`backend/app/ai/agents/validator.py`)
- [ ] Gap Analyst agent (`backend/app/ai/agents/gap_analyst.py`)
- [ ] Roadmap Planner agent (`backend/app/ai/agents/roadmap_planner.py`)
- [ ] Report builder modules (`backend/app/reports/builders/`)
- [ ] Report exporters (`backend/app/reports/exporters/`)
- [ ] Report aggregator service (merges all outputs)
- [ ] Report persistence (full JSON + per-section storage)
- [ ] API endpoints: `GET /api/v1/reports/{id}`, `GET /api/v1/reports/{id}/sections/{section}`
- [ ] Finding persistence and retrieval
- [ ] Report versioning (re-analysis creates new report, keeps old)

**Dependencies**: Milestone 3

**Estimated complexity**: High (10–14 days)

---

## Milestone 5: Frontend Application

**Objective**: Build the user-facing web application.

**Deliverables**:
- [ ] Project scaffold (Vite + React + TypeScript + CSS Modules + React Router)
- [ ] Typed API client layer (`src/services/`)
- [ ] Shared component library (`src/components/`: Button, Card, Modal, Badge, Skeleton, Toast, ProgressBar, DataTable, EmptyState, ErrorBoundary)
- [ ] Layout components (`src/layouts/`: RootLayout, AuthLayout, AppLayout)
- [ ] Authentication flow (GitHub OAuth callback, token management)
- [ ] Dashboard page (`src/pages/Dashboard/`)
- [ ] Analyze page (`src/pages/Analyze/`: repo selector, trigger, progress view)
- [ ] Reports page (`src/pages/Reports/`: structured report viewer with sections)
- [ ] History page (`src/pages/History/`: analysis list, search, filter, delete)
- [ ] Settings page (`src/pages/Settings/`: profile, preferences, integrations)
- [ ] TanStack Query hooks (`src/hooks/`: useAnalyses, useReports, useAuth, usePolling)
- [ ] Responsive layout (desktop-first, tablet-capable)
- [ ] Loading / error / empty states for every view

**Dependencies**: Milestone 4 (reports API)

**Estimated complexity**: High (14–18 days)

---

## Milestone 6: Testing & Quality

**Objective**: Achieve production-ready quality through comprehensive testing.

**Deliverables**:
- [ ] Backend unit tests for all services and agents (≥80% coverage)
- [ ] Backend integration tests for API endpoints
- [ ] Frontend unit tests for critical components
- [ ] Frontend integration tests for main user flows
- [ ] Agent output validation tests (fixtures for each agent)
- [ ] E2E test: login → analyze repo → view report
- [ ] Performance tests (analysis pipeline with fixture repos)
- [ ] Error scenario tests (GitHub unavailable, LLM failure, etc.)
- [ ] Security scan (dependency audit, SAST)
- [ ] Load test (concurrent analyses)

**Dependencies**: Milestones 1–5

**Estimated complexity**: Medium (10–14 days)

---

## Milestone 7: Production Readiness

**Objective**: Deploy to production with monitoring, alerting, and operations tooling.

**Deliverables**:
- [ ] Docker image builds for API and worker
- [ ] Kubernetes manifests (or equivalent cloud-native configs)
- [ ] Database migrations automation (CI/CD run on deploy)
- [ ] Logging aggregation (structured JSON logs)
- [ ] Monitoring dashboards (API latency, analysis duration, error rate, queue depth)
- [ ] Alert rules (PagerDuty / Slack integration)
- [ ] Rate limiting (API + analysis queue)
- [ ] Backup strategy (DB snapshots, report artifacts)
- [ ] Secrets management (HashiCorp Vault / cloud secret manager)
- [ ] Documentation: runbooks for common failures
- [ ] SSL / TLS termination
- [ ] Domain and DNS setup

**Dependencies**: Milestone 6

**Estimated complexity**: Medium (7–10 days)

---

## Milestone 8: MVP Launch

**Objective**: Feature-complete MVP ready for beta users.

**Deliverables**:
- [ ] User onboarding flow (first analysis guided experience)
- [ ] Error messaging improvements (user-facing error descriptions)
- [ ] Email notification on analysis completion (optional, MVP)
- [ ] Feedback mechanism (in-app feedback form)
- [ ] Usage analytics (basic event tracking, opt-in)
- [ ] Public beta announcement (landing page update)
- [ ] Known issues document
- [ ] Support channel (email / Discord)

**Dependencies**: Milestone 7

**Estimated complexity**: Low (3–5 days)

---

## Post-MVP (Future Milestones)

| Milestone | Description |
|---|---|
| Incremental analysis | Analyze only changed files on new commits |
| Team workspaces | Shared reports, team management |
| Scheduled analysis | Weekly / monthly auto-analysis of tracked repos |
| Custom agent SDK | Third-party agent development |
| On-premise deployment | Private cloud / self-hosted option |
| Advanced caching | Repo clone caching, result caching |
| Comparative analysis | Diff reports between two analyses |
| PDF / PPTX export | Downloadable report formats |
