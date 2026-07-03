# Pipeline Architecture

## Complete System Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           API LAYER                                     │
│                     (FastAPI Endpoints)                                 │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  Import Endpoints          Pipeline Endpoints (NEW)    Graph Endpoints │
│  ─────────────────         ────────────────────────    ─────────────── │
│  POST /import              POST /analyze               POST /graph     │
│  GET  /list                POST /rebuild-graph         GET  /graph     │
│  GET  /{id}                GET  /pipeline-status       GET  /nodes     │
│  POST /sync                                            GET  /edges     │
│  POST /index                                                           │
│                                                                         │
└─────────────────┬───────────────────┬─────────────────────┬────────────┘
                  │                   │                     │
                  │                   │                     │
     ┌────────────▼──────┐  ┌─────────▼──────────┐  ┌──────▼─────────┐
     │ GitHub Services   │  │ RepositoryPipeline │  │ Graph Services │
     │ ─────────────────│  │ ──────────────────  │  │ ────────────── │
     │ • GitHubClient   │  │ • Orchestrator     │  │ • NodeExtractor│
     │ • CloneService   │  │ • Coordinator      │  │ • EdgeExtractor│
     │ • RepoService    │  │ • Workflow Manager │  │ • GraphPersister│
     └──────────────────┘  └─────────┬──────────┘  └────────────────┘
                                     │
                    ┌────────────────┴────────────────┐
                    │                                 │
          ┌─────────▼──────────┐         ┌───────────▼─────────┐
          │ Indexing Services  │         │   Graph Services    │
          │ ──────────────────│         │   ───────────────   │
          │ • FileScanner     │         │   • NodeExtractor   │
          │ • RepositoryIndexer│         │   • EdgeExtractor   │
          │ • SymbolExtractor │         │   • GraphPersister  │
          └─────────┬──────────┘         └─────────────────────┘
                    │
          ┌─────────▼──────────┐
          │ Parser Services    │
          │ ──────────────────│
          │ • ParserManager   │
          │ • ParserFactory   │
          │ • Language Parsers│
          └────────────────────┘
```

## Pipeline Flow Diagram

```
┌──────────────────────────────────────────────────────────────────────┐
│                    REPOSITORY ANALYSIS PIPELINE                      │
└──────────────────────────────────────────────────────────────────────┘

Step 1: IMPORT                           (External - GitHub API)
  │
  ├─► Clone repository from GitHub
  ├─► Store repository metadata
  └─► Create repository record in DB
       │
       ▼
Step 2: INDEX                            (RepositoryIndexer)
  │
  ├─► Scan filesystem for files
  ├─► Detect file languages
  ├─► Calculate file metadata (size, hash, etc.)
  └─► Store RepositoryFile records
       │
       ▼
Step 3: PARSE                            (SymbolExtractor)
  │
  ├─► Parse each file with tree-sitter
  ├─► Extract symbols (functions, classes, etc.)
  ├─► Extract symbol metadata
  └─► Store RepositorySymbol records
       │
       ▼
Step 4: BUILD KNOWLEDGE GRAPH            (Graph Services - NEW)
  │
  ├─► Extract Nodes
  │    ├─► Repository → 1 repository node
  │    ├─► RepositoryFiles → N file nodes
  │    └─► RepositorySymbols → M symbol nodes
  │
  ├─► Extract Edges
  │    ├─► CONTAINS (Repository→File, File→Symbol)
  │    ├─► IMPORTS (Symbol→Symbol)
  │    ├─► INHERITS (Class→Class)
  │    ├─► IMPLEMENTS (Class→Interface)
  │    ├─► DECLARES (Function→Parameter)
  │    └─► REFERENCES (Symbol→Symbol)
  │
  └─► Persist Graph
       ├─► Store RepositoryNode records
       └─► Store RepositoryEdge records
            │
            ▼
       ┌────────────┐
       │  COMPLETE  │
       └────────────┘
```

## Service Dependencies

```
RepositoryPipeline (Orchestrator)
│
├─► RepositoryIndexer
│   ├─► FileScanner
│   │   └─► LanguageDetector
│   │
│   └─► SymbolExtractor
│       └─► ParserManager
│           └─► ParserFactory
│               ├─► PythonParser
│               ├─► JavaScriptParser
│               ├─► TypeScriptParser
│               ├─► JavaParser
│               ├─► CParser
│               ├─► CppParser
│               ├─► GoParser
│               └─► RustParser
│
└─► Graph Services
    ├─► NodeExtractor
    │   └─► Session (DB)
    │
    ├─► EdgeExtractor
    │   └─► Session (DB)
    │
    └─► GraphPersister
        └─► Session (DB)
```

## Data Flow

```
┌─────────────┐
│   GitHub    │
│ Repository  │
└──────┬──────┘
       │ clone
       ▼
┌─────────────┐
│ Filesystem  │
└──────┬──────┘
       │ scan
       ▼
┌─────────────────┐
│ RepositoryFile  │ (DB)
└──────┬──────────┘
       │ parse
       ▼
┌───────────────────┐
│ RepositorySymbol  │ (DB)
└──────┬────────────┘
       │ extract
       ▼
┌───────────────────┐
│ RepositoryNode    │ (DB)
│ RepositoryEdge    │ (DB)
└───────────────────┘
       │
       ▼
┌───────────────────┐
│ Knowledge Graph   │
│   (Queryable)     │
└───────────────────┘
```

## API Request Flow

### Option 1: Single Request (Recommended)

```
Client
  │
  │ POST /repositories/import
  ├────────────────────────────────► Import Service
  │                                   (Clone from GitHub)
  │
  │ POST /repositories/{id}/analyze
  ├────────────────────────────────► RepositoryPipeline
  │                                   │
  │                                   ├─► RepositoryIndexer
  │                                   │   (Scan + Parse)
  │                                   │
  │                                   └─► Graph Services
  │                                       (Build Graph)
  │
  │◄──────────────────────────────── Complete Statistics
  │
  │ GET /repositories/{id}/graph/nodes
  ├────────────────────────────────► Graph API
  │                                   (Query Graph)
  │
  │◄──────────────────────────────── Graph Nodes
```

### Option 2: Manual Steps

```
Client
  │
  │ POST /repositories/import
  ├────────────────────────────────► Import Service
  │
  │ POST /repositories/{id}/index
  ├────────────────────────────────► RepositoryIndexer
  │
  │ POST /repositories/{id}/graph
  ├────────────────────────────────► Graph Services
  │
  │ GET /repositories/{id}/graph
  ├────────────────────────────────► Graph API
```

## Database Schema

```
repositories
  │
  ├──1:N──► repository_files
  │           │
  │           └──1:N──► repository_symbols
  │
  └──1:N──► repository_nodes
              │
              └──M:N──► repository_edges
```

## Integration Points

```
┌──────────────────────────────────────────────────────────────┐
│                    INTEGRATION POINTS                        │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  Existing Modules              New Orchestration Layer      │
│  ────────────────              ───────────────────────      │
│                                                              │
│  ┌─────────────────┐           ┌──────────────────┐        │
│  │RepositoryIndexer│◄──────────┤RepositoryPipeline│        │
│  └─────────────────┘           └────────┬─────────┘        │
│         ▲                                │                   │
│         │                                │                   │
│         │ (No Changes)                   │                   │
│         │                                │                   │
│  ┌──────┴────────┐                      │                   │
│  │SymbolExtractor│                      │                   │
│  └───────────────┘                      │                   │
│                                          │                   │
│  ┌──────────────┐                       │                   │
│  │NodeExtractor │◄──────────────────────┤                   │
│  └──────────────┘                       │                   │
│         ▲                                │                   │
│         │                                │                   │
│         │ (No Changes)                   │                   │
│         │                                │                   │
│  ┌──────┴─────────┐                     │                   │
│  │ EdgeExtractor  │◄────────────────────┤                   │
│  └────────────────┘                     │                   │
│         ▲                                │                   │
│         │                                │                   │
│         │ (No Changes)                   │                   │
│         │                                │                   │
│  ┌──────┴─────────┐                     │                   │
│  │ GraphPersister │◄────────────────────┘                   │
│  └────────────────┘                                          │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

## Key Design Principles

1. **Separation of Concerns**
   - Each service has a single responsibility
   - Orchestration layer coordinates, doesn't implement

2. **Loose Coupling**
   - Services don't depend on each other directly
   - Pipeline injects dependencies

3. **Open/Closed**
   - Extended functionality without modifying existing code
   - New behavior through new components

4. **Dependency Injection**
   - All services injected via FastAPI
   - Easy to test and replace

## Deployment View

```
┌────────────────────────────────────────────────────────┐
│                   Production System                    │
├────────────────────────────────────────────────────────┤
│                                                        │
│  ┌──────────────┐    ┌──────────────┐               │
│  │   FastAPI    │────│  PostgreSQL  │               │
│  │   Backend    │    │   Database   │               │
│  └──────┬───────┘    └──────────────┘               │
│         │                                             │
│         │ calls                                       │
│         │                                             │
│  ┌──────▼───────┐    ┌──────────────┐               │
│  │   GitHub     │    │    Redis     │               │
│  │     API      │    │    Cache     │               │
│  └──────────────┘    └──────────────┘               │
│                                                        │
└────────────────────────────────────────────────────────┘
```

## Summary

The pipeline architecture provides:
- ✅ Clean separation of concerns
- ✅ Modular, maintainable code
- ✅ Easy to test and extend
- ✅ Non-invasive integration
- ✅ Complete workflow automation
