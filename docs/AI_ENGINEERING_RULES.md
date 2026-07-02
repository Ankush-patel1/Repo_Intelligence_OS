# AI Engineering Rules — Repo Intelligence OS

Always follow the docs in `/docs/` before writing code.

## Document Priority

1. ARCHITECTURE.md
2. PROJECT_STRUCTURE.md
3. DATABASE.md
4. API.md
5. AGENTS.md
6. DEVELOPMENT_GUIDELINES.md
7. PROJECT_RULES.md
8. DECISIONS.md
9. TASKS.md
10. PRD.md

## Rules

- Never rewrite working code.
- Never modify unrelated files.
- Keep modules under approximately 300 lines.
- Prefer composition over inheritance.
- Keep comments minimal.
- Keep architecture modular.
- Use dependency injection.
- Avoid duplicated code.
- Explain architectural changes before implementing.
- After every task, list every modified file.

## Agent Implementation Rules

- Agents live in `backend/app/ai/agents/`. Each agent extends `BaseAgent`.
- Agent prompts live in `backend/app/ai/prompts/templates/` as `.txt` files.
- Agent outputs must be Pydantic models with evidence (file paths, line numbers).
- Orchestration lives in `backend/app/ai/orchestration/` using LangGraph.
- Retrieval and context building live in `backend/app/ai/retrieval/`.
- Embeddings and vector search live in `backend/app/ai/embeddings/` using FAISS.
- Code parsing per language lives in `backend/app/parser/<language>/` using Tree-sitter.
- Report sections are built in `backend/app/reports/builders/`.
- No agent calls the database directly. Use services and repositories.