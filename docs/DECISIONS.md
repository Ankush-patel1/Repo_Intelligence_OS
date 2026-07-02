# Repo Intelligence OS — Architecture Decision Records

---

## ADR-001: Use FastAPI for the Backend API

**Status**: Accepted

**Decision**: Build the backend HTTP API with FastAPI (Python 3.11+).

**Reason**:
- Async-native framework that handles high-concurrency I/O without the complexity of Node.js or the overhead of Django.
- Automatic OpenAPI/Swagger documentation generation from Pydantic schemas — keeps API docs in sync with code.
- Built-in dependency injection simplifies auth, DB session, and request-scoped services.
- Pydantic v2 integration provides request/response validation with zero additional boilerplate.
- Large ecosystem of plugins and middleware (CORS, rate limiting, auth).
- Strong community adoption and production track record.

**Alternatives considered**:
- **Django + DRF**: Heavy framework with synchronous ORM by default. Overkill for a focused API service. Magic shell — too many conventions to learn and override.
- **Flask**: No native async support. Missing built-in validation, OpenAPI generation, and dependency injection. Would need 5+ extensions to match FastAPI's built-in capabilities.
- **Litestar**: Newer, smaller community. Fewer production references. Less third-party middleware available.

---

## ADR-002: Use React + Vite + TypeScript for the Frontend

**Status**: Accepted

**Decision**: Build the frontend SPA with React 18+, Vite, and TypeScript. Use CSS Modules for styling.

**Reason**:
- React is the most widely adopted UI library with the largest ecosystem, talent pool, and longest support horizon.
- Vite provides sub-second HMR, native TypeScript support, and fast production builds — 10x faster than Webpack in development.
- TypeScript catches entire classes of bugs at compile time. Strict mode forces explicit type boundaries.
- CSS Modules provide zero-runtime scoping without adding a runtime dependency. Native Vite support with no configuration.
- TanStack Query (React Query) handles all server state management with automatic caching, background refetching, and polling — critical for analysis job status tracking.

**Alternatives considered**:
- **Next.js**: Great for SSR/SSG. Overkill for a pure SPA with a separate backend API. Adds deployment complexity (Node server, edge functions).
- **Tailwind CSS**: Excellent for rapid prototyping but couples markup to utility classes. CSS Modules chosen for long-term maintainability and separation of concerns.
- **Vue 3 + Vite**: Viable alternative. Rejected due to smaller talent pool and less mature TypeScript patterns. React's `use` hooks and Suspense better suit the polling-heavy UI.

---

## ADR-003: Use PostgreSQL as the Primary Database

**Status**: Accepted

**Decision**: Use PostgreSQL 16+ with SQLAlchemy 2.0 (async) and Alembic for migrations.

**Reason**:
- JSONB columns for semi-structured report sections and agent findings — flexible schema where needed, relational integrity where it matters.
- Mature async driver (asyncpg) with SQLAlchemy 2.0 async support — important for FastAPI's async event loop.
- Full-text search (`tsvector`) for future report and finding search.
- Strong ACID guarantees for transactionally sensitive data (analysis state transitions, user tokens).
- Excellent indexing (GIN for JSONB, GiST for full-text, B-tree for everything else).
- Horizontal scaling via read replicas when needed.

**Alternatives considered**:
- **MySQL 8**: Weaker JSON support. Less reliable async Python driver (`aiomysql`). Inferior indexing for JSON queries. No native full-text search comparable to PostgreSQL.
- **MongoDB**: No joins between users, analyses, reports, findings. Document size limits (16 MB) could be hit by large reports with many findings. Schema-less design would push validation entirely to application code.
- **SQLite**: No concurrent write support. Cannot handle the worker fleet's parallel database access.

---

## ADR-004: Use LangGraph for AI Agent Orchestration

**Status**: Accepted

**Decision**: Use LangGraph (Python) to define and execute the multi-agent analysis pipeline as a directed graph.

**Reason**:
- Analysis pipeline naturally maps to a graph: sequential (Planner → Scout), parallel (Feature Detective, Security, Performance, etc.), sequential (Validator → Gap Analyst → Roadmap Planner).
- LangGraph provides built-in state management across graph nodes — agents can read/write shared state without coupling.
- Conditional branching enables dynamic execution paths (e.g., skip certain agents if Planner determines they're not needed).
- Python-native with any LLM provider — no vendor lock-in. Can swap between OpenAI, Anthropic, or self-hosted models without changing orchestration code.
- Graph structure is inspectable, testable, and visualizable — important for debugging agent pipelines.

**Alternatives considered**:
- **LangChain**: Higher-level abstraction that obscures the underlying execution model. "Chain of chains" pattern makes debugging difficult. We want explicit control over parallel execution and error handling.
- **CrewAI**: Opinionated about agent roles and delegation. Less flexible for custom orchestration patterns like "run 6 agents in parallel, then run 3 sequentially."
- **Custom Python state machine**: Would need to reimplement LangGraph's threading, state management, and error recovery from scratch. LangGraph is a focused solution to exactly this problem.

---

## ADR-005: Use FAISS for Vector Similarity Search

**Status**: Accepted

**Decision**: Use FAISS (Facebook AI Similarity Search) for embedding storage and similarity search.

**Reason**:
- Code analysis requires comparing code snippets, finding similar patterns, and deduplicating findings — all of which benefit from vector similarity search.
- FAISS is orders of magnitude faster than brute-force cosine similarity on large datasets. GPU acceleration available.
- Multiple index types (IVF, HNSW) allow trade-offs between search speed and accuracy depending on the use case.
- Open-source (MIT license), self-hosted — no network latency or vendor dependency for vector search.
- Python bindings integrate directly with the embedding pipeline.

**Alternatives considered**:
- **pgvector**: Convenient because it lives in PostgreSQL. Significantly slower than FAISS for large-scale search. Index build times increase query latency. Better suited for "good enough" similarity search on small datasets.
- **Pinecone / Weaviate (managed)**: Add network latency to every embedding lookup. Vendor lock-in. Operational cost at scale. Not justified for MVP where self-hosted FAISS is sufficient.
- **Chroma**: Simpler API but less performant at scale. Python-only runtime. Fewer index optimization options than FAISS.

---

## ADR-006: Use Tree-sitter for Code Parsing

**Status**: Accepted

**Decision**: Use Tree-sitter for parsing source files across multiple programming languages.

**Reason**:
- Repo Intelligence OS must analyze repositories written in any language. Tree-sitter supports 40+ languages with a consistent parsing interface.
- Produces concrete syntax trees (CSTs) that are error-tolerant — can parse partial or malformed code that traditional parsers reject.
- Incremental parsing enables re-parsing only changed files when implementing future incremental analysis features.
- Blazing fast — parsing is typically 10-100x faster than ANTLR or hand-written parsers.
- `.scm` query files provide a declarative way to extract specific syntax patterns (function definitions, class declarations, import statements) without writing language-specific traversal code.

**Alternatives considered**:
- **ANTLR**: Requires a separate grammar compilation step per language. Generated parsers are monolithic and hard to maintain. Not error-tolerant — rejects files with syntax errors.
- **Pygments**: Tokenizer only — produces colored tokens but no AST structure. Cannot extract class hierarchies, function signatures, or dependency relationships.
- **Regex-only parsing**: Fragile and unmaintainable at scale. Cannot handle nested syntax (e.g., matching function bodies with nested braces). Different regex sets needed per language.
- **Language Server Protocol (LSP)**: Running LSP servers per language in a sandboxed environment is operationally complex. Memory-heavy. Overkill for stateless analysis.

---

## ADR-007: Use Celery + Redis for Background Task Processing

**Status**: Accepted

**Decision**: Use Celery with Redis as the message broker for asynchronous analysis pipeline execution.

**Reason**:
- Celery is the most mature Python task queue with production deployment across thousands of companies.
- Redis serves dual purpose: Celery message broker + cache for repository clones and file contents.
- Celery Canvas (group, chord, chain) maps directly to the agent pipeline pattern: execute agents in parallel (`group`), then execute sequential agents when all parallel agents complete (`chord`).
- Built-in retry with exponential backoff, task timeouts, and rate limiting.
- Flower (web UI) for task monitoring during development and debugging.
- Workers are a separate deployment unit — can scale independently from the API.

**Alternatives considered**:
- **Arq**: Lightweight Redis-based task queue. Simpler but missing Canvas primitives needed for parallel agent execution. Smaller community, fewer production references.
- **Dramatiq**: Simpler API. Missing group/chord patterns. Would need to implement parallel agent coordination manually.
- **Temporal / AWS SWF**: Powerful but heavy. Durable execution with workflow history is unnecessary for MVP where analysis pipelines complete in minutes. Significant operational overhead. Can migrate to Temporal if workflow durability becomes a requirement.
- **Redis Queue (RQ)**: Simple but missing scheduled tasks, complex workflows, and monitoring capabilities needed for production.

---

## ADR-008: Evidence-First AI Architecture

**Status**: Accepted

**Decision**: Every AI agent output must cite specific evidence (file paths, line numbers, code excerpts) for each finding. Findings without evidence are discarded.

**Reason**:
- Without evidence, AI agents can hallucinate findings that waste developer time. Evidence-first architecture forces factual grounding.
- Evidence enables the Validator to cross-reference findings from different agents and detect contradictions.
- Report consumers (engineering managers, staff engineers) can immediately verify findings by navigating to the cited code — builds trust in the system.
- Evidence provides an audit trail for every claim in the report. Essential for due diligence and security audit use cases.
- The output schema for every agent includes a required `location` field (file path + line range). The `BaseAgent` rejects outputs missing location data and triggers a retry.

**Alternatives considered**:
- **Summary-only approach**: Agents produce free-text summaries. No evidence required. Faster development but produces unverifiable reports. Users cannot distinguish hallucinated findings from real ones.
- **Confidence-scoring-only approach**: Agents score confidence but provide no evidence. Slightly better than summary-only, but still lacks auditability. A high-confidence hallucination is worse than a low-confidence real finding.
- **Hybrid with optional evidence**: Weaker constraint — LLMs tend to skip optional fields. Many findings would lack evidence, making the "evidence-first" guarantee unreliable.

**Consequences**:
- Agent prompt templates must explicitly instruct the LLM to cite evidence. Few-shot examples include evidence citations.
- File paths must be resolved relative to repository root for consistency.
- The Validator checks evidence against the actual file index. Findings referencing nonexistent paths are flagged.
- Some agents (e.g., Gap Analyst) synthesize findings from multiple agent outputs — their evidence is cross-references to other findings' IDs, not file paths.
