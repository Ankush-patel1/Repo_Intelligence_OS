# Repository Knowledge Graph - Design Summary

**Status**: ✅ Design Complete - Awaiting Approval  
**Next Version**: v0.4.0  
**Date**: 2026-07-03

---

## Quick Summary

The Repository Knowledge Graph module will build a **directed property graph** representing code relationships using existing parsed symbols. The design reuses all current infrastructure and adds relationship tracking on top.

---

## 1. Existing Models to Reuse

✅ **Repository** - Root node, provides context (100% reusable)  
✅ **RepositoryFile** - File nodes, source of symbols (100% reusable)  
✅ **RepositorySymbol** - Primary graph nodes (100% reusable)  
  - Already has parent-child hierarchy (class → methods)
  - Already stores signature, metadata, location
  - Already indexed for efficient queries

**No modifications needed to existing models.**

---

## 2. Existing Parser Outputs Available

### ✅ Already Captured:
- Symbol names and types (function, class, method, import, export)
- Signatures (parameters, async, decorators)
- Parent-child relationships (class → method)
- Location information (line numbers)
- Import/export statements (as symbols)
- Metadata (decorators, parameters, access modifiers)

### ❌ Missing Data (Requires New Analysis):
- Function call targets (who calls whom)
- Import source resolution (which file does import point to)
- Type resolution for parameters/returns
- Explicit inheritance chains

**Gap**: Need to analyze existing symbols to build relationships.

---

## 3. Recommended Graph Architecture

### Graph Type: **PostgreSQL with Recursive CTEs**

**Why?**
- Leverage existing PostgreSQL infrastructure
- No new database system needed
- Good performance for graphs <100K symbols
- Recursive queries handle traversal
- Migration path to Neo4j if needed later

### Node Types (Mapped to Existing Models):
1. Repository (Repository model)
2. File (RepositoryFile model)
3. Symbol (RepositorySymbol model)
4. Module/Package (new ModuleNode model - optional)

### Relationship Types (New):
1. **CONTAINS** - Repository → File → Symbol
2. **IMPORTS** - File → File, Symbol → Symbol
3. **EXPORTS** - File → Symbol
4. **CALLS** - Function → Function (phase 2)
5. **INHERITS** - Class → Class/Interface
6. **REFERENCES** - Symbol → Symbol (general)
7. **DEFINES** - Function → Variable

---

## 4. Database Models Required

### NEW Models (3 Required + 1 Optional):

#### 4.1 SymbolRelationship ✅ REQUIRED
Tracks relationships between symbols (imports, calls, inheritance)

**Key Fields**:
- source_symbol_id, target_symbol_id (FKs)
- relationship_type (CALLS, IMPORTS, INHERITS, REFERENCES)
- metadata (JSON: import_type, alias, call_count)
- repository_id, source_file_id, target_file_id

**Indexes**: 6 indexes for efficient queries

#### 4.2 FileRelationship ✅ REQUIRED
Tracks file-level dependencies

**Key Fields**:
- source_file_id, target_file_id (FKs)
- relationship_type (IMPORTS, DEPENDS_ON)
- import_count, metadata (JSON)
- repository_id

**Unique Constraint**: (source_file_id, target_file_id, relationship_type)

#### 4.3 SymbolReference ✅ REQUIRED
Tracks where symbols are referenced across files

**Key Fields**:
- referenced_symbol_id (FK)
- referencing_file_id, referencing_symbol_id (FKs)
- reference_type (CALL, IMPORT, TYPE_ANNOTATION, etc.)
- line_number, column_number
- repository_id, metadata (JSON)

#### 4.4 ModuleNode ⚠️ OPTIONAL
Represents logical modules/packages (aggregates files)

**Key Fields**:
- repository_id (FK)
- module_path, module_name
- module_type (PACKAGE, NAMESPACE, DIRECTORY)
- file_count, symbol_count, language (cached stats)

---

## 5. Services Required

### NEW Services (6):

1. **GraphBuilder** - Main orchestrator
   - `build_graph(repository_id)` - Build complete graph
   - `build_import_relationships()` - Analyze imports
   - `build_inheritance_relationships()` - Analyze inheritance
   - Coordinates all analysis

2. **ImportResolver** - Import statement resolution
   - `resolve_import(statement, file, language)` - Find target
   - Handles relative/absolute imports
   - Language-specific resolution logic

3. **CallGraphAnalyzer** - Function call analysis (Phase 2)
   - `analyze_function_calls(repository_id)` - Extract calls
   - Requires AST re-parsing
   - Builds CALLS relationships

4. **InheritanceAnalyzer** - Class hierarchy analysis
   - `analyze_inheritance(repository_id)` - Extract inheritance
   - `build_inheritance_tree()` - Create hierarchy
   - Resolves base classes

5. **GraphQueryService** - Query interface
   - `get_symbol_dependencies(symbol_id)` - Get dependencies
   - `get_callers()`, `get_callees()` - Call graph queries
   - `find_path_between_symbols()` - Graph traversal
   - `get_import_graph()` - Visualization data

6. **GraphStatistics** - Metrics and analytics
   - `calculate_repository_metrics()` - Graph stats
   - `find_most_referenced_symbols()` - Hotspot detection
   - `detect_circular_dependencies()` - Cycle detection
   - `calculate_symbol_centrality()` - Importance scoring

---

## 6. APIs Required

### NEW API Endpoints (~15):

#### Graph Building
- `POST /api/v1/repositories/{id}/graph/build` - Build graph (async)
- `POST /api/v1/repositories/{id}/graph/rebuild` - Rebuild from scratch

#### Relationship Queries
- `GET /api/v1/repositories/{id}/graph/relationships` - List relationships
- `GET /api/v1/symbols/{id}/dependencies` - Get dependencies
- `GET /api/v1/symbols/{id}/dependents` - Get dependents
- `GET /api/v1/symbols/{id}/references` - Get all references
- `GET /api/v1/symbols/{id}/callers` - Get callers
- `GET /api/v1/symbols/{id}/callees` - Get callees

#### File Relationships
- `GET /api/v1/files/{id}/imports` - Files this imports
- `GET /api/v1/files/{id}/imported-by` - Files importing this
- `GET /api/v1/files/{id}/dependency-graph` - Dependency tree

#### Graph Traversal
- `GET /api/v1/repositories/{id}/graph/import-graph` - Import graph data
- `GET /api/v1/repositories/{id}/graph/call-graph` - Call graph data
- `GET /api/v1/classes/{id}/inheritance-tree` - Inheritance hierarchy
- `GET /api/v1/symbols/{source_id}/path-to/{target_id}` - Find path

#### Statistics
- `GET /api/v1/repositories/{id}/graph/statistics` - Graph metrics
- `GET /api/v1/repositories/{id}/graph/circular-dependencies` - Detect cycles
- `GET /api/v1/repositories/{id}/graph/hotspots` - Critical symbols

---

## 7. Integration Points

### 7.1 Repository Indexer Integration
**Location**: `backend/app/services/indexing/repository_indexer.py`

**Change**: Add optional graph building after symbol extraction

**Flow**:
```
Index Repository
  ↓
Extract Symbols (existing)
  ↓
[NEW] Build Knowledge Graph (if flag enabled)
  ↓
Complete
```

### 7.2 Symbol Extractor Integration
**Location**: `backend/app/services/indexing/symbol_extractor.py`

**Change**: NONE - Already provides all needed data

### 7.3 Parser Integration
**Location**: `backend/app/services/parser/*.py`

**Change**: NONE for v0.4.0
**Future**: Enhance parsers to extract call expressions

### 7.4 API Router Integration
**Location**: `backend/app/api/v1/repositories.py`

**Change**: Add new graph endpoints

### 7.5 Database Migration
**Location**: `backend/alembic/versions/`

**Change**: Add migration `20260704_0001_create_knowledge_graph_tables.py`

---

## 8. Risks

### 🔴 HIGH Risk

**Performance**
- Large repos (>10K files) may take minutes to build graph
- **Mitigation**: Async building, incremental updates, caching

**Import Resolution Accuracy**
- Complex import patterns may fail (dynamic imports, aliases)
- **Mitigation**: Start simple, iterate based on failures, best-effort approach

**Data Consistency**
- Graph becomes stale after code changes
- **Mitigation**: Rebuild on sync, incremental updates, timestamps

### 🟡 MEDIUM Risk

**Query Performance**
- Deep graph traversals may timeout
- **Mitigation**: Depth limits, query timeouts, materialized views

**Symbol Ambiguity**
- Same name in different scopes
- **Mitigation**: Use fully qualified names, file context, prioritize local scope

**Database Growth**
- Relationship tables could be very large
- **Mitigation**: Partitioning, aggressive indexing, retention policies

### 🟢 LOW Risk

**Scope Creep**
- Many possible graph features
- **Mitigation**: Define clear v0.4.0 scope, defer advanced features

---

## 9. Implementation Phases

**Phase 1** (Week 1): Database models + migrations  
**Phase 2** (Week 2): Import graph (FileRelationship)  
**Phase 3** (Week 3): Symbol relationships + inheritance  
**Phase 4** (Week 4): APIs + query service  
**Phase 5** (Week 5): Integration + testing  

**Total Estimated Time**: 5 weeks

---

## 10. Success Criteria

### Functional ✅
- Build complete import graph for repository
- Query file/symbol dependencies
- Detect circular dependencies
- Find inheritance hierarchies
- Traverse graph via API

### Performance ✅
- 1K files: <30 seconds to build
- 10K files: <5 minutes to build
- Query response: <1 second
- Traversal (depth 5): <2 seconds

### Quality ✅
- 90%+ import resolution accuracy
- 95%+ test coverage
- Zero N+1 queries
- All APIs paginated

---

## 11. Out of Scope for v0.4.0

❌ Call graph analysis (defer to v0.5.0)  
❌ Type resolution  
❌ Dead code detection  
❌ Graph visualization UI  
❌ Real-time updates  
❌ Neo4j migration  

**Focus**: Import graph, symbol relationships, inheritance only

---

## Conclusion

### ✅ Design Complete

The knowledge graph design:
- **Reuses** all 3 existing models (100%)
- **Adds** 3-4 new models for relationships
- **Requires** 6 new services
- **Adds** ~15 new API endpoints
- **Integrates** seamlessly with existing pipeline
- **Risks** are manageable with proper mitigations
- **Timeline** is 5 weeks

### 📋 Next Steps

1. **Review** this design document
2. **Approve** scope and approach
3. **Prioritize** features (if needed)
4. **Begin** Phase 1 implementation

---

**Full Design**: See `KNOWLEDGE_GRAPH_DESIGN.md` for complete details.
