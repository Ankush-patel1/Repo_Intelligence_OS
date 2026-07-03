# Repository Knowledge Graph - Design Document

**Version**: v0.4.0 (Planned)  
**Date**: 2026-07-03  
**Status**: Design Phase - NO CODE IMPLEMENTATION YET

---

## 1. Existing Models to Reuse

### ✅ Repository (Fully Reusable)
**Location**: `backend/app/db/models/repository.py`

**Fields**:
- `id` (UUID) - Primary key
- `owner` (String) - Repository owner
- `name` (String) - Repository name
- `full_name` (String) - owner/name
- `branch` (String) - Branch being analyzed
- `clone_path` (String) - Local filesystem path
- `default_branch` (String)
- `last_synced` (DateTime)

**Usage in Knowledge Graph**: Root node for all graph queries, provides repository context.

---

### ✅ RepositoryFile (Fully Reusable)
**Location**: `backend/app/db/models/repository_file.py`

**Fields**:
- `id` (UUID) - Primary key
- `repository_id` (UUID FK) - Links to Repository
- `relative_path` (Text) - File path within repo
- `absolute_path` (Text) - Full filesystem path
- `file_name` (String) - Filename
- `extension` (String) - File extension
- `language` (String) - Programming language
- `size_bytes` (BigInteger)
- `line_count` (Integer)
- `sha256_hash` (String) - Content hash
- `last_modified` (DateTime)
- `is_binary` (Boolean)

**Relationship**: Has many `RepositorySymbol` (cascade delete)

**Usage in Knowledge Graph**: File nodes represent modules/packages, source of all symbols.

---

### ✅ RepositorySymbol (Fully Reusable)
**Location**: `backend/app/db/models/repository_symbol.py`

**Fields**:
- `id` (UUID) - Primary key
- `repository_file_id` (UUID FK) - Links to RepositoryFile
- `symbol_name` (String 512) - Symbol identifier
- `symbol_type` (String 64) - function, class, method, import, export, etc.
- `parent_symbol` (UUID FK) - Self-referencing for class/method hierarchy
- `start_line` (Integer) - Start location
- `end_line` (Integer) - End location
- `start_column` (Integer)
- `end_column` (Integer)
- `language` (String 32)
- `signature` (Text) - Full signature
- `symbol_metadata` (Text/JSON) - Decorators, parameters, async, etc.
- `created_at` (DateTime)

**Existing Relationships**:
- `repository_file` → RepositoryFile (selectin)
- `parent` → Self (class-method hierarchy)
- `children` → Self backref

**Existing Indexes**:
- `ix_repository_symbols_repository_file_id_symbol_type`
- `ix_repository_symbols_language_symbol_type`
- `ix_repository_symbols_location` (file_id, start_line, end_line)
- Individual indexes on: symbol_name, symbol_type, language, parent_symbol

**Usage in Knowledge Graph**: Primary nodes in the graph, represent code entities.

---

## 2. Existing Parser Outputs Available

### Data Already Extracted (Per Language)

#### All Languages Provide:
- Symbol name
- Symbol type (import, export, function, class, method, etc.)
- Line numbers (start_line, end_line)
- Signature (function/method signatures)
- Parent-child relationships (class → methods)

#### Python Parser Outputs:
```python
{
    "type": "import|class|function",
    "name": "symbol_name",
    "line": 1,
    "end_line": 10,
    "kind": "import|from_import",  # for imports
    "parameters": ["param1", "param2"],  # for functions
    "is_async": True/False,
    "is_method": True/False,
    "decorators": ["@decorator1"],
    "methods": [...]  # for classes
}
```

#### JavaScript/TypeScript Parser Outputs:
```python
{
    "type": "import|export|class|function",
    "name": "symbol_name",
    "kind": "import|named|default",  # for imports/exports
    "line": 1,
    "end_line": 10,
    "parameters": ["param1"],
    "is_async": True/False,
    "methods": [...]  # for classes
}
```

#### Java/C/C++/Go/Rust Similar Patterns:
- Package/module declarations
- Import statements
- Class/struct/interface definitions
- Method/function definitions
- Inheritance/implementation relationships (in metadata)

### Currently NOT Extracted (Gaps):
❌ Function call targets (who calls whom)
❌ Variable references across files
❌ Type resolution for parameters/returns
❌ Explicit dependency edges between symbols
❌ Import source resolution (which file does import point to)

---

## 3. Recommended Graph Architecture

### Graph Type: **Directed Property Graph**

**Why?**
- Relationships have direction (A calls B, A imports B)
- Relationships need properties (call count, import type)
- Supports multiple relationship types
- Enables graph traversal queries

### Node Types:

1. **Repository Node** (1 per repo)
   - Properties: name, owner, branch, language_stats

2. **File Node** (maps to RepositoryFile)
   - Properties: path, language, size, line_count

3. **Symbol Node** (maps to RepositorySymbol)
   - Types: Class, Function, Method, Interface, Type, Enum, Variable
   - Properties: name, signature, line_range, language

4. **Module/Package Node** (virtual, aggregates files)
   - Properties: name, file_count, symbol_count

### Relationship Types:

1. **CONTAINS**
   - Repository → File
   - File → Symbol
   - Class → Method
   - Module → File

2. **IMPORTS**
   - File → File (cross-file imports)
   - Symbol → Symbol (specific symbol imports)
   - Properties: import_type (named, default, namespace), alias

3. **EXPORTS**
   - File → Symbol (what a file exports)
   - Properties: export_type (named, default)

4. **CALLS**
   - Function → Function
   - Method → Method/Function
   - Properties: call_count (if we add frequency analysis)

5. **INHERITS**
   - Class → Class (inheritance)
   - Class → Interface (implementation)
   - Properties: inheritance_type (extends, implements)

6. **REFERENCES**
   - Symbol → Symbol (general reference)
   - Properties: reference_type (variable, parameter, return_type)

7. **DEFINES**
   - Function → Variable
   - Class → Field

### Storage Strategy:

**Option A: PostgreSQL with Recursive CTEs** ✅ RECOMMENDED
- Leverage existing PostgreSQL infrastructure
- Use recursive queries for graph traversal
- Store relationships in new edge tables
- Good for moderate graphs (<100K symbols)

**Option B: Neo4j** (Future consideration)
- Native graph database
- Better for very large graphs (>1M symbols)
- Requires additional infrastructure
- Migration path available later

---

## 4. Database Models Required

### 4.1 SymbolRelationship (New Model)
**Purpose**: Store relationships between symbols

```python
class SymbolRelationship(Base):
    __tablename__ = "symbol_relationships"
    
    # Primary key
    id: UUID (PK)
    
    # Source and target symbols
    source_symbol_id: UUID (FK → repository_symbols.id)
    target_symbol_id: UUID (FK → repository_symbols.id)
    
    # Relationship type
    relationship_type: String(64)
    # Values: CALLS, IMPORTS, INHERITS, REFERENCES, DEFINES
    
    # Relationship metadata
    metadata: Text (JSON)
    # Examples:
    # - import_type: "named" | "default" | "namespace"
    # - alias: "import x as y" → "y"
    # - call_count: 5
    # - inheritance_type: "extends" | "implements"
    
    # Context
    repository_id: UUID (FK → repositories.id)
    source_file_id: UUID (FK → repository_files.id)
    target_file_id: UUID (FK → repository_files.id, nullable)
    
    # Timestamps
    created_at: DateTime
    
    # Indexes
    - (source_symbol_id, relationship_type)
    - (target_symbol_id, relationship_type)
    - (repository_id, relationship_type)
    - (source_file_id, target_file_id)
```

### 4.2 FileRelationship (New Model)
**Purpose**: Store file-level dependencies

```python
class FileRelationship(Base):
    __tablename__ = "file_relationships"
    
    # Primary key
    id: UUID (PK)
    
    # Source and target files
    source_file_id: UUID (FK → repository_files.id)
    target_file_id: UUID (FK → repository_files.id)
    
    # Relationship type
    relationship_type: String(64)
    # Values: IMPORTS, DEPENDS_ON
    
    # Metadata
    import_count: Integer  # How many imports from source to target
    metadata: Text (JSON)
    # - import_specifiers: ["func1", "Class1"]
    # - import_style: "es6" | "commonjs" | "python" | etc.
    
    # Context
    repository_id: UUID (FK → repositories.id)
    
    # Timestamps
    created_at: DateTime
    
    # Indexes
    - (source_file_id, relationship_type)
    - (target_file_id, relationship_type)
    - (repository_id)
    
    # Unique constraint
    - UNIQUE(source_file_id, target_file_id, relationship_type)
```

### 4.3 SymbolReference (New Model)
**Purpose**: Track where symbols are referenced (cross-file)

```python
class SymbolReference(Base):
    __tablename__ = "symbol_references"
    
    # Primary key
    id: UUID (PK)
    
    # Symbol being referenced
    referenced_symbol_id: UUID (FK → repository_symbols.id)
    
    # Where it's referenced
    referencing_file_id: UUID (FK → repository_files.id)
    referencing_symbol_id: UUID (FK → repository_symbols.id, nullable)
    # nullable: reference might be at file level, not within a symbol
    
    # Reference details
    reference_type: String(64)
    # Values: CALL, IMPORT, TYPE_ANNOTATION, INHERITANCE, INSTANTIATION
    
    line_number: Integer
    column_number: Integer (nullable)
    
    # Context
    repository_id: UUID (FK → repositories.id)
    
    # Metadata
    metadata: Text (JSON)
    # - context: "function call" | "type hint" | etc.
    
    # Timestamps
    created_at: DateTime
    
    # Indexes
    - (referenced_symbol_id, reference_type)
    - (referencing_file_id)
    - (referencing_symbol_id)
    - (repository_id, reference_type)
```

### 4.4 ModuleNode (New Model - Optional)
**Purpose**: Represent logical modules/packages

```python
class ModuleNode(Base):
    __tablename__ = "module_nodes"
    
    # Primary key
    id: UUID (PK)
    
    # Module identification
    repository_id: UUID (FK → repositories.id)
    module_path: String(1024)  # e.g., "src/services/parser"
    module_name: String(255)   # e.g., "parser"
    
    # Module type
    module_type: String(64)
    # Values: PACKAGE, NAMESPACE, DIRECTORY
    
    # Statistics (cached)
    file_count: Integer
    symbol_count: Integer
    language: String(32)
    
    # Timestamps
    created_at: DateTime
    updated_at: DateTime
    
    # Indexes
    - (repository_id, module_path)
    - UNIQUE(repository_id, module_path)
```

---

## 5. Services Required

### 5.1 GraphBuilder Service
**Location**: `backend/app/services/graph/graph_builder.py`

**Responsibilities**:
- Build knowledge graph from existing symbols
- Analyze import/export statements
- Resolve symbol references across files
- Create relationship edges
- Handle incremental updates

**Key Methods**:
```python
class GraphBuilder:
    async def build_graph(repository_id: UUID) -> dict
    async def build_import_relationships(repository_id: UUID) -> int
    async def build_call_relationships(repository_id: UUID) -> int
    async def build_inheritance_relationships(repository_id: UUID) -> int
    async def resolve_import_targets(import_symbol: RepositorySymbol) -> UUID | None
    async def find_symbol_references(symbol_id: UUID) -> list[SymbolReference]
```

### 5.2 ImportResolver Service
**Location**: `backend/app/services/graph/import_resolver.py`

**Responsibilities**:
- Resolve import statements to actual files/symbols
- Handle different import styles (ES6, CommonJS, Python, Java, etc.)
- Resolve relative imports (./module, ../module)
- Resolve absolute imports (package.module)
- Handle import aliases

**Key Methods**:
```python
class ImportResolver:
    async def resolve_import(
        import_statement: str,
        source_file: RepositoryFile,
        language: str
    ) -> ResolvedImport | None
    
    def parse_import_statement(statement: str, language: str) -> ImportInfo
    async def find_target_file(import_path: str, source_file: RepositoryFile) -> RepositoryFile | None
    async def find_exported_symbol(target_file: RepositoryFile, symbol_name: str) -> RepositorySymbol | None
```

### 5.3 CallGraphAnalyzer Service
**Location**: `backend/app/services/graph/call_graph_analyzer.py`

**Responsibilities**:
- Analyze function calls within code
- Requires AST re-parsing to find call expressions
- Build CALLS relationships
- Track call frequency (optional)

**Key Methods**:
```python
class CallGraphAnalyzer:
    async def analyze_function_calls(repository_id: UUID) -> int
    async def extract_calls_from_symbol(symbol: RepositorySymbol) -> list[str]
    async def resolve_call_target(call_name: str, context: SymbolContext) -> UUID | None
```

### 5.4 InheritanceAnalyzer Service
**Location**: `backend/app/services/graph/inheritance_analyzer.py`

**Responsibilities**:
- Extract class inheritance information
- Extract interface implementations
- Build INHERITS relationships
- Create class hierarchy trees

**Key Methods**:
```python
class InheritanceAnalyzer:
    async def analyze_inheritance(repository_id: UUID) -> int
    async def extract_base_classes(class_symbol: RepositorySymbol) -> list[str]
    async def resolve_base_class(class_name: str, file: RepositoryFile) -> UUID | None
    async def build_inheritance_tree(repository_id: UUID) -> dict
```

### 5.5 GraphQueryService
**Location**: `backend/app/services/graph/graph_query_service.py`

**Responsibilities**:
- Query the knowledge graph
- Find relationships between symbols
- Traverse graph paths
- Aggregate graph statistics

**Key Methods**:
```python
class GraphQueryService:
    async def get_symbol_dependencies(symbol_id: UUID) -> list[SymbolRelationship]
    async def get_file_dependencies(file_id: UUID) -> list[FileRelationship]
    async def find_path_between_symbols(source_id: UUID, target_id: UUID) -> list[UUID]
    async def get_callers(symbol_id: UUID) -> list[RepositorySymbol]
    async def get_callees(symbol_id: UUID) -> list[RepositorySymbol]
    async def get_symbol_references(symbol_id: UUID) -> list[SymbolReference]
    async def get_import_graph(repository_id: UUID) -> dict
    async def get_inheritance_tree(class_id: UUID) -> dict
```

### 5.6 GraphStatistics Service
**Location**: `backend/app/services/graph/graph_statistics.py`

**Responsibilities**:
- Calculate graph metrics
- Find central/important nodes
- Detect circular dependencies
- Calculate complexity scores

**Key Methods**:
```python
class GraphStatistics:
    async def calculate_repository_metrics(repository_id: UUID) -> dict
    async def find_most_referenced_symbols(repository_id: UUID, limit: int) -> list
    async def find_most_dependent_files(repository_id: UUID, limit: int) -> list
    async def detect_circular_dependencies(repository_id: UUID) -> list[list[UUID]]
    async def calculate_symbol_centrality(symbol_id: UUID) -> float
```

---

## 6. APIs Required

### 6.1 Knowledge Graph Build API

**POST** `/api/v1/repositories/{repository_id}/graph/build`
- Build complete knowledge graph for repository
- Status: 202 Accepted (async operation)
- Response: Job ID + initial statistics

**POST** `/api/v1/repositories/{repository_id}/graph/rebuild`
- Rebuild graph from scratch
- Deletes existing relationships
- Status: 202 Accepted

### 6.2 Relationship Query APIs

**GET** `/api/v1/repositories/{repository_id}/graph/relationships`
- List all relationships
- Query params: relationship_type, source_file_id, target_file_id
- Returns: Paginated list of SymbolRelationship

**GET** `/api/v1/symbols/{symbol_id}/dependencies`
- Get all symbols this symbol depends on
- Includes: imports, calls, references
- Returns: List of related symbols with relationship types

**GET** `/api/v1/symbols/{symbol_id}/dependents`
- Get all symbols that depend on this symbol
- Inverse of dependencies
- Returns: List of related symbols

**GET** `/api/v1/symbols/{symbol_id}/references`
- Get all places where symbol is referenced
- Returns: List of SymbolReference with file/line info

**GET** `/api/v1/symbols/{symbol_id}/callers`
- Get all functions/methods that call this symbol
- Returns: List of symbols with CALLS relationship

**GET** `/api/v1/symbols/{symbol_id}/callees`
- Get all functions/methods this symbol calls
- Returns: List of symbols

### 6.3 File Relationship APIs

**GET** `/api/v1/files/{file_id}/imports`
- Get all files this file imports from
- Returns: List of FileRelationship

**GET** `/api/v1/files/{file_id}/imported-by`
- Get all files that import this file
- Returns: List of FileRelationship

**GET** `/api/v1/files/{file_id}/dependency-graph`
- Get complete dependency graph for file
- Returns: Tree structure of dependencies

### 6.4 Graph Traversal APIs

**GET** `/api/v1/repositories/{repository_id}/graph/import-graph`
- Get complete import graph visualization data
- Returns: Nodes + edges for visualization

**GET** `/api/v1/repositories/{repository_id}/graph/call-graph`
- Get function call graph
- Query params: depth, root_symbol_id
- Returns: Nodes + edges

**GET** `/api/v1/classes/{class_id}/inheritance-tree`
- Get inheritance hierarchy
- Returns: Tree structure

**GET** `/api/v1/symbols/{source_id}/path-to/{target_id}`
- Find path between two symbols
- Returns: List of symbols in path

### 6.5 Graph Statistics APIs

**GET** `/api/v1/repositories/{repository_id}/graph/statistics`
- Get graph metrics
- Returns:
  - Total nodes/edges
  - Relationship type counts
  - Most referenced symbols
  - Most dependent files
  - Circular dependencies

**GET** `/api/v1/repositories/{repository_id}/graph/circular-dependencies`
- Detect circular dependencies
- Returns: List of dependency cycles

**GET** `/api/v1/repositories/{repository_id}/graph/hotspots`
- Find central/critical code
- Returns: Ranked list of symbols by centrality

---

## 7. Integration Points

### 7.1 Integration with Repository Indexer
**Location**: `backend/app/services/indexing/repository_indexer.py`

**Changes Needed**:
- After symbol extraction completes, trigger graph building
- Add optional flag: `build_graph=True` to index_repository()
- Call GraphBuilder.build_graph() after symbol extraction

**Integration Flow**:
```
Repository Import
  ↓
Clone Repository
  ↓
Index Files (existing)
  ↓
Extract Symbols (existing)
  ↓
[NEW] Build Knowledge Graph
  ↓
Complete
```

### 7.2 Integration with Symbol Extractor
**Location**: `backend/app/services/indexing/symbol_extractor.py`

**No Changes Required**:
- Symbol extractor already provides all needed data
- Metadata field already captures decorators, parameters, etc.
- Parent-child relationships already established

**Data Flow**:
```
SymbolExtractor → RepositorySymbol (DB)
                         ↓
                  GraphBuilder (reads symbols)
                         ↓
                  SymbolRelationship (DB)
```

### 7.3 Integration with Parsers
**Location**: `backend/app/services/parser/*.py`

**Enhancement Opportunity** (Future):
- Add call expression extraction to parsers
- Extract base class names for inheritance
- More detailed import metadata

**Current State**: No changes required for v0.4.0
**Future State**: Enhance parsers to extract call targets

### 7.4 Integration with API Router
**Location**: `backend/app/api/v1/repositories.py`

**New Endpoints to Add**:
- Graph build endpoint
- Relationship query endpoints
- Graph statistics endpoint

**New Dependencies**:
```python
from app.services.graph import GraphBuilder, GraphQueryService
```

### 7.5 Database Migration Integration
**Location**: `backend/alembic/versions/`

**New Migration Required**:
- Migration: `20260704_0001_create_knowledge_graph_tables.py`
- Creates: symbol_relationships, file_relationships, symbol_references, module_nodes
- Down revision: `20260703_0001_create_repository_symbols`

---

## 8. Risks

### 8.1 Performance Risks

**Risk**: Graph building for large repositories (>10K files) could be slow
- **Impact**: HIGH - User experience degradation
- **Probability**: HIGH - Large repos are common
- **Mitigation**:
  - Make graph building asynchronous (use Celery)
  - Implement incremental graph updates
  - Add progress tracking
  - Cache frequently accessed graph queries
  - Add pagination to all list endpoints

**Risk**: Recursive graph queries could timeout
- **Impact**: MEDIUM - API timeouts
- **Probability**: MEDIUM - Deep dependency chains
- **Mitigation**:
  - Set depth limits on traversal queries
  - Use iterative queries instead of recursive CTEs for deep graphs
  - Add query timeouts
  - Consider materialized views for common queries

### 8.2 Data Quality Risks

**Risk**: Import resolution may fail for complex import patterns
- **Impact**: HIGH - Incomplete graph
- **Probability**: HIGH - Many import styles exist
- **Mitigation**:
  - Start with simple import patterns (relative, absolute)
  - Log failed resolutions for debugging
  - Provide partial graph (best-effort approach)
  - Add manual override capability
  - Iterate on resolver based on failure patterns

**Risk**: Symbol names may be ambiguous (same name in different scopes)
- **Impact**: MEDIUM - Incorrect relationships
- **Probability**: MEDIUM - Common in large codebases
- **Mitigation**:
  - Use fully qualified names where possible
  - Include file context in resolution
  - Prioritize local scope over global
  - Store ambiguity metadata for review

**Risk**: Dynamic imports/requires cannot be resolved statically
- **Impact**: MEDIUM - Missing edges in graph
- **Probability**: HIGH - Common in JavaScript/Python
- **Mitigation**:
  - Document limitation
  - Focus on static analysis first
  - Consider runtime analysis in future versions
  - Mark dynamic imports explicitly in metadata

### 8.3 Complexity Risks

**Risk**: Implementing call graph analysis requires re-parsing files
- **Impact**: MEDIUM - Additional parsing cost
- **Probability**: HIGH - Current parsers don't extract calls
- **Mitigation**:
  - Phase implementation: Start with imports only
  - Enhance parsers incrementally
  - Make call graph analysis optional
  - Cache parse results

**Risk**: Maintaining graph consistency after code changes
- **Impact**: HIGH - Stale graph data
- **Probability**: HIGH - Code changes frequently
- **Mitigation**:
  - Implement incremental updates
  - Trigger graph rebuild on sync
  - Add last_updated timestamps
  - Provide manual rebuild endpoint

### 8.4 Database Risks

**Risk**: Relationship tables could grow very large (millions of rows)
- **Impact**: HIGH - Database performance degradation
- **Probability**: HIGH - Many relationships in large repos
- **Mitigation**:
  - Add table partitioning by repository_id
  - Implement aggressive indexing strategy
  - Add retention policies (optional)
  - Monitor table sizes
  - Consider archiving old relationships

**Risk**: Complex join queries may be slow
- **Impact**: MEDIUM - Slow API responses
- **Probability**: MEDIUM - Multi-level joins needed
- **Mitigation**:
  - Use appropriate indexes
  - Implement query result caching
  - Add database query monitoring
  - Use EXPLAIN ANALYZE for optimization
  - Consider read replicas for heavy queries

### 8.5 Scope Creep Risks

**Risk**: Feature requests for advanced graph analytics
- **Impact**: LOW - Timeline extension
- **Probability**: HIGH - Many possibilities
- **Mitigation**:
  - Define clear v0.4.0 scope
  - Defer advanced features to v0.5.0+
  - Focus on core relationships first
  - Document future enhancements separately

**Risk**: Supporting all edge cases for all 8 languages
- **Impact**: MEDIUM - Extended development time
- **Probability**: HIGH - Language-specific complexities
- **Mitigation**:
  - Implement language-agnostic patterns first
  - Add language-specific resolvers incrementally
  - Start with Python/JavaScript (most common)
  - Document language support matrix

---

## 9. Implementation Phases

### Phase 1: Foundation (Week 1)
- Create database models (SymbolRelationship, FileRelationship)
- Add migrations
- Create GraphBuilder service skeleton
- Add unit tests for models

### Phase 2: Import Graph (Week 2)
- Implement ImportResolver service
- Build import relationships from existing symbols
- Create FileRelationship records
- Add API endpoints for file dependencies

### Phase 3: Symbol Relationships (Week 3)
- Implement SymbolRelationship creation
- Build symbol-level import edges
- Add inheritance analysis
- Create GraphQueryService

### Phase 4: APIs & Queries (Week 4)
- Implement all graph query APIs
- Add graph statistics endpoints
- Create graph visualization data endpoints
- Add comprehensive API tests

### Phase 5: Integration & Testing (Week 5)
- Integrate with repository indexer
- Add end-to-end tests
- Performance testing & optimization
- Documentation updates

---

## 10. Success Criteria

### Functional Criteria
✅ Can build complete import graph for repository  
✅ Can query file dependencies (imports/imported-by)  
✅ Can query symbol dependencies  
✅ Can detect circular dependencies  
✅ Can find inheritance hierarchies  
✅ Can traverse graph relationships via API  
✅ Graph rebuilds on repository re-indexing  

### Performance Criteria
✅ Graph builds for 1K files in <30 seconds  
✅ Graph builds for 10K files in <5 minutes  
✅ Single relationship query returns in <1 second  
✅ Graph traversal (depth 5) returns in <2 seconds  

### Quality Criteria
✅ 90%+ import resolution accuracy  
✅ 95%+ test coverage for graph services  
✅ Zero N+1 query issues  
✅ All APIs properly paginated  
✅ Comprehensive error handling  

---

## 11. Future Enhancements (v0.5.0+)

- **Call Graph Analysis**: Extract and track function calls
- **Type Resolution**: Resolve parameter/return types
- **Dead Code Detection**: Find unused symbols
- **Dependency Impact Analysis**: What breaks if X changes?
- **Graph Visualization**: Interactive graph UI in frontend
- **Change Impact Prediction**: ML-based impact scoring
- **Symbol Search**: Full-text search across symbols
- **Neo4j Migration**: For very large repositories
- **Real-time Graph Updates**: WebSocket updates on code changes

---

## Summary

The Knowledge Graph module will leverage all existing infrastructure:
- ✅ Reuses Repository, RepositoryFile, RepositorySymbol models
- ✅ Uses existing parser outputs and symbol metadata
- ✅ Adds 3-4 new relationship tables
- ✅ Requires 6 new services for graph building and querying
- ✅ Adds ~15 new API endpoints
- ✅ Integrates seamlessly with existing indexing pipeline
- ⚠️ Primary risks: performance, import resolution accuracy
- 📊 Estimated timeline: 5 weeks for core implementation

**Next Step**: Review and approve design before code implementation begins.
