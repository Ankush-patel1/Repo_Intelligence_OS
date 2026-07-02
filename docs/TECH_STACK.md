# Repo Intelligence OS — Technology Stack

## 1. Frontend

### React 18+ with TypeScript

| | |
|---|---|
**Why chosen** | Industry standard for SPAs. Huge ecosystem, excellent TypeScript support, concurrent features for smooth UI during long analysis polling. Mature server-side rendering ecosystem for future SEO needs. |
**Alternatives considered** | Vue 3, Svelte 5, Solid |
**Why rejected** | Vue 3 — smaller talent pool, less mature TypeScript integration. Svelte — too young for production SaaS, limited ecosystem for complex state management patterns. Solid — excellent performance but minimal ecosystem and smaller community. |
**Future replacement** | Unlikely within 3 years. If the React ecosystem fragments further (e.g., React 19+ breaking changes), consider migrating to Preact or a web-component-based approach. |

### Vite

| | |
|---|---|
**Why chosen** | Fastest build tool for React SPAs. Native ES module dev server with sub-second HMR. First-class TypeScript and CSS Modules support. |
**Alternatives considered** | Webpack, Turbopack, create-react-app |
**Why rejected** | Webpack — slow HMR, complex configuration. CRA — deprecated, no longer maintained. Turbopack — still experimental, unstable for production. |
**Future replacement** | Continue with Vite. Consider Turbopack once stable if build performance becomes a bottleneck at scale. |

### CSS Modules

| | |
|---|---|
**Why chosen** | Zero-runtime CSS scoping. Native Vite support. No additional dependencies. Co-located with components. Predictable class names at build time. |
**Alternatives considered** | Tailwind CSS, styled-components, CSS-in-JS, vanilla CSS |
**Why rejected** | Tailwind — excellent for rapid prototyping but leads to long class strings and couples markup to utility classes; adds a build step dependency and a learning curve for new developers. styled-components / CSS-in-JS — runtime overhead, complex SSR configuration, larger bundle size. |
**Future replacement** | If CSS container queries and `@scope` gain full cross-browser support, consider migrating to vanilla CSS with built-in scoping. Otherwise, CSS Modules remain the long-term choice. |

### React Router v6

| | |
|---|---|
**Why chosen** | De facto routing standard for React. Nested routes with `<Outlet />` pattern fits our layout hierarchy (Root → Auth/App → Pages). Loader/action API for data fetching aligns with TanStack Query. |
**Alternatives considered** | TanStack Router, Next.js App Router |
**Why rejected** | TanStack Router — excellent but newer; adds another TanStack dependency. App Router — requires full Next.js migration; overkill for a pure SPA with separate backend. |
**Future replacement** | Consider TanStack Router if we need type-safe routes, search param validation, or virtual routing at scale. |

### TanStack Query (React Query v5)

| | |
|---|---|
**Why chosen** | Best-in-class async state management for server data. Automatic caching, background refetching, pagination, optimistic updates. Built-in polling aligns with analysis job status tracking. |
**Alternatives considered** | Redux Toolkit Query, Zustand + manual fetch, SWR |
**Why rejected** | RTK Query — couples to Redux ecosystem; more boilerplate than needed. SWR — less feature-rich, smaller community. Zustand + manual fetch — loses caching, dedup, and background sync. |
**Future replacement** | No expected replacement. TanStack Query is the standard for this pattern. |

---

## 2. Backend

### Python 3.11+

| | |
|---|---|
**Why chosen** | Best ecosystem for AI/ML tooling (LangChain, LlamaIndex, Transformers). Excellent async support with `anyio` and `asyncio`. Rich type system with modern typing features. Dominant language for LLM-based applications. |
**Alternatives considered** | Go, TypeScript (Node.js), Rust |
**Why rejected** | Go — immature AI ecosystem, no mainstream LLM SDKs, verbose error handling. TypeScript — single-threaded event loop blocks during compute-heavy parsing; AI SDK ecosystem less mature. Rust — steep learning curve, slow iteration speed, smaller AI ecosystem. |
**Future replacement** | Python will remain the primary language. Specific performance-critical components (Tree-sitter parsing, FAISS indexing) can be offloaded to native extensions or microservices in Rust/Go. |

### FastAPI

| | |
|---|---|
**Why chosen** | Async-native Python framework with automatic OpenAPI generation, Pydantic integration, dependency injection, and excellent performance. Best fit for high-concurrency I/O-bound API serving. |
**Alternatives considered** | Django + DRF, Flask, Litestar |
**Why rejected** | Django — heavy ORM coupling, synchronous by default, too much overhead for a focused API service. Flask — no async support in core, no built-in validation or OpenAPI. Litestar — newer, smaller community, fewer production references. |
**Future replacement** | FastAPI is the long-term choice. If Python async ecosystem shifts significantly, consider Litestar as a drop-in alternative. |

### PostgreSQL

| | |
|---|---|
**Why chosen** | Most advanced open-source relational database. JSONB for semi-structured report data, full-text search for future features, excellent concurrency, strong ACID compliance. Mature async support via asyncpg. |
**Alternatives considered** | MySQL 8, MongoDB, CockroachDB |
**Why rejected** | MySQL 8 — weaker JSON support, less reliable async driver, inferior indexing for JSON queries. MongoDB — no joins, weak ACID for relational data (users, analyses), schema-less design causes complexity for report/finding queries. CockroachDB — operationally complex for MVP; can migrate to it later if horizontal scaling becomes necessary. |
**Future replacement** | Stick with PostgreSQL. If read scalability becomes a bottleneck, add read replicas. If global distribution is needed, consider CockroachDB or Aurora. |

### SQLAlchemy 2.0 (Async) + Alembic

| | |
|---|---|
**Why chosen** | Most mature Python ORM with async support (2.0). Alembic is the standard migration tool. Full type hint support, excellent PostgreSQL-specific features. |
**Alternatives considered** | SQLModel, Tortoise ORM, raw asyncpg |
**Why rejected** | SQLModel — young, tightly coupled to FastAPI, limited advanced ORM features. Tortoise ORM — async-native but smaller ecosystem, less proven in production. Raw asyncpg — too low-level, no migration tooling, no model layer. |
**Future replacement** | SQLAlchemy is the long-term standard. May supplement with SQLModel for simple CRUD if it matures. |

### Celery + Redis

| | |
|---|---|
**Why chosen** | Mature, production-proven task queue. Redis broker provides low-latency message passing. Celery Canvas (chords, groups, chains) maps naturally to agent pipeline orchestration. Flower for monitoring. |
**Alternatives considered** | Arq, Dramatiq, AWS SQS + Lambda, Temporal |
**Why rejected** | Arq — lightweight but immature, limited monitoring and retry features. Dramatiq — simpler but less flexible for complex DAG workflows. SQS + Lambda — vendor lock-in, Lambda cold starts add latency to analysis pipeline. Temporal — heavy operational overhead for MVP; excellent for future scale. |
**Future replacement** | Celery serves MVP well. If orchestration complexity grows beyond Celery's capabilities, migrate to Temporal for durable execution. |

---

## 3. AI & Machine Learning

### LangGraph

| | |
|---|---|
**Why chosen** | Purpose-built framework for defining agent workflows as graphs. Supports conditional branching, parallel execution, and state management. Python-native. Integrates with any LLM provider. |
**Alternatives considered** | LangChain, CrewAI, AutoGen, custom state machine |
**Why rejected** | LangChain — overly abstracted, "chain of chains" anti-pattern, debugging difficulty at scale. CrewAI — opinionated about agent structure, less flexible for custom orchestration. AutoGen — Microsoft-centric, tightly coupled to specific LLM patterns. Custom state machine — would need to build LangGraph from scratch; reinventing the wheel. |
**Future replacement** | LangGraph is the core orchestration layer. If the framework stagnates, we own the orchestration abstraction and can replace it without touching agent implementations. |

### FAISS

| | |
|---|---|
**Why chosen** | Industry standard for efficient similarity search and vector clustering. GPU-accelerated. Python bindings. Handles millions of vectors efficiently. Open-source (BSD license). |
**Alternatives considered** | Chroma, Pinecone, Weaviate, pgvector |
**Why rejected** | Chroma — simpler but less performant at scale, Python-only. Pinecone + Weaviate — managed services, add network latency, vendor lock-in, operational cost. pgvector — convenient for simple use cases but significantly slower than FAISS for large-scale similarity search on code embeddings. |
**Future replacement** | FAISS for MVP. If vector search needs to scale horizontally, consider migrating to Supabase pgvector with indexing, Qdrant, or Weaviate self-hosted. |

### Tree-sitter

| | |
|---|---|
**Why chosen** | Incremental parsing with precise syntax trees. Supports 40+ languages. Error-tolerant parsing (can parse partial or incomplete files). Blazing fast — orders of magnitude faster than AST generation with parser combinators. |
**Alternatives considered** | ANTLR, pygments, regex-based parsing, Language Server Protocol |
**Why rejected** | ANTLR — generates parsers, not a parsing library; each language needs a grammar compilation step. Pygments — tokenizer only, no AST structure. Regex — fragile, cannot handle nested syntax, needs constant maintenance. LSP — heavy process per language, too operationally complex for analysis context. |
**Future replacement** | Tree-sitter is the long-term choice. As it gains more language support, we simply add `.scm` query files. |

---

## 4. Infrastructure

### Docker + Docker Compose

| | |
|---|---|
**Why chosen** | Universal container standard. Compose provides single-command local environment. Multi-stage builds keep images small. |
**Alternatives considered** | Podman, Vagrant, dev containers |
**Why rejected** | Podman — Docker-compatible but fewer CI integrations. Vagrant — VM-based, heavier, slower startup. Dev containers — VS Code-specific, less portable across team tooling. |
**Future replacement** | Docker remains the standard. Consider migrating to containerd directly if Kubernetes becomes the sole deployment target. |

### Redis

| | |
|---|---|
**Why chosen** | Celery broker requirement. Also serves as cache for repository clones and file contents. In-memory speed for analysis queue operations. |
**Alternatives considered** | RabbitMQ, Amazon MQ, Kafka |
**Why rejected** | RabbitMQ — more complex topology, overkill for MVP queue needs. Kafka — event streaming is too heavy for task queuing; operational complexity. Redis serves both as broker and cache, reducing infrastructure surface area. |
**Future replacement** | Redis for MVP. If message durability becomes critical, add RabbitMQ as a secondary broker. If event sourcing is needed, add Kafka alongside. |

### GitHub Actions

| | |
|---|---|
**Why chosen** | CI/CD tightly integrated with GitHub. Free tier for public repos. Large marketplace of actions. Simple YAML configuration. |
**Alternatives considered** | GitLab CI, CircleCI, Jenkins |
**Why rejected** | GitLab CI — would require GitLab.com migration. CircleCI — paid tier needed for reasonable concurrency. Jenkins — excessive operational overhead for a SaaS project. |
**Future replacement** | GitHub Actions for MVP through production. Consider migrating if build times exceed 30 minutes or if matrix testing requires more concurrency than Actions allows. |

---

## 5. Monitoring & Observability

### Structured JSON Logging (stdlib + python-json-logger)

| | |
|---|---|
**Why chosen** | Zero additional infrastructure dependency. Parseable by any log aggregator (ELK, Grafana Loki, Datadog). Correlation IDs across API → worker → agent calls. |
**Alternatives considered** | OpenTelemetry, Sentry, DataDog |
**Why rejected** | OpenTelemetry — adds complexity; adopt when tracing needs exceed correlation IDs. Sentry — great for errors but not comprehensive logging. DataDog — expensive for MVP; adopt post-launch. |
**Future replacement** | Add OpenTelemetry for distributed tracing when the system spans multiple services. Add Sentry for error tracking at beta launch. |

### Prometheus + Grafana

| | |
|---|---|
**Why chosen** | Open-source monitoring standard. Pull model works well with container orchestration. Python Prometheus client library. Grafana for dashboards. |
**Alternatives considered** | Datadog, New Relic, CloudWatch |
**Why rejected** | All are paid services. Datadog and New Relic are expensive at scale. CloudWatch — vendor lock-in to AWS; less flexible dashboards than Grafana. Prometheus + Grafana is free, self-hosted, and portable across cloud providers. |
**Future replacement** | Keep Prometheus + Grafana. Consider Datadog as a paid upgrade if operational overhead of self-hosting exceeds cost. |
