# Graph Services Framework

This package provides the architectural framework for building and querying the repository knowledge graph.

## Architecture Overview

The graph framework follows a **plugin architecture** where:
- **Analyzers** implement `GraphInterface` to extract specific relationship types
- **Registry** manages analyzer discovery and lifecycle
- **Builder** orchestrates analyzer execution
- **Service** provides query interface for the built graph

## Components

### 1. GraphInterface (graph_interface.py)

Abstract base class for all graph analyzers.

**Key Methods:**
- `relationship_type` (property) - Type of relationship this analyzer handles
- `supported_languages` (property) - Languages this analyzer supports
- `analyze(repository_id)` - Main analysis logic, returns statistics
- `can_analyze(repository_id)` - Check if analyzer can run
- `cleanup(repository_id)` - Remove existing relationships
- `get_priority()` - Execution order priority

**Analyzer Responsibilities:**
1. Query necessary data (symbols, files)
2. Extract relationships using analyzer-specific logic
3. Create nodes and edges in the graph
4. Return statistics about created entities

**Example Analyzer Structure:**
```python
class ImportAnalyzer(GraphInterface):
    @property
    def relationship_type(self) -> str:
        return "IMPORTS"
    
    @property
    def supported_languages(self) -> list[str]:
        return ["Python", "JavaScript", "TypeScript"]
    
    async def analyze(self, repository_id: UUID) -> dict:
        # 1. Query import symbols
        # 2. Resolve import targets
        # 3. Create nodes and edges
        # 4. Return statistics
        pass
```

### 2. GraphRegistry (graph_registry.py)

Central registry for all graph analyzers.

**Key Features:**
- Maintains collection of analyzer classes
- Discovers and instantiates analyzers
- Manages analyzer lifecycle
- Provides global registry instance

**Usage:**
```python
from app.services.graph import register_analyzer

# Register an analyzer
register_analyzer(ImportAnalyzer)

# Get registry
registry = get_registry()

# Get specific analyzer
analyzer = registry.get_analyzer("IMPORTS", session)

# Get all analyzers (sorted by priority)
analyzers = registry.get_all_analyzers(session)
```

### 3. GraphBuilder (graph_builder.py)

Orchestrates graph building across multiple analyzers.

**Key Methods:**
- `build_graph(repository_id, relationship_types, cleanup)` - Build graph
- `rebuild_graph(repository_id)` - Rebuild from scratch
- `update_graph(repository_id, relationship_types)` - Incremental update
- `get_available_analyzers()` - List registered analyzers

**Features:**
- Executes analyzers in priority order
- Handles partial failures gracefully
- Aggregates results from all analyzers
- Tracks execution time and statistics

**Usage:**
```python
builder = GraphBuilder(session)

# Build complete graph
result = await builder.build_graph(repository_id)
# Returns:
# {
#     "total_nodes_created": 1500,
#     "total_edges_created": 2300,
#     "analyzers_run": 5,
#     "analyzers_skipped": 1,
#     "analyzers_failed": 0,
#     "results": [...],
#     "duration_seconds": 12.5
# }

# Build specific relationships only
result = await builder.build_graph(
    repository_id,
    relationship_types=["IMPORTS", "CONTAINS"]
)

# Rebuild from scratch
result = await builder.rebuild_graph(repository_id)
```

### 4. GraphService (graph_service.py)

High-level query interface for the knowledge graph.

**Query Operations:**
- `get_node(node_id)` - Fetch single node
- `get_nodes_by_repository(repo_id, node_type, language)` - Query nodes
- `get_outgoing_edges(node_id, relationship_type)` - Get edges from node
- `get_incoming_edges(node_id, relationship_type)` - Get edges to node
- `get_neighbors(node_id, relationship_type, direction)` - Get adjacent nodes
- `find_path(source_id, target_id, max_depth)` - BFS path finding
- `has_relationship(source_id, target_id, relationship_type)` - Check edge
- `get_graph_statistics(repository_id)` - Aggregate statistics

**Usage:**
```python
service = GraphService(session)

# Get node
node = await service.get_node(node_id)

# Get all symbol nodes for repository
symbols = await service.get_nodes_by_repository(
    repository_id,
    node_type="symbol",
    language="Python"
)

# Get what a file imports
imports = await service.get_outgoing_edges(
    file_node_id,
    relationship_type="IMPORTS"
)

# Get what imports a file
imported_by = await service.get_incoming_edges(
    file_node_id,
    relationship_type="IMPORTS"
)

# Find path between symbols
path = await service.find_path(func1_id, func2_id, max_depth=5)

# Get graph statistics
stats = await service.get_graph_statistics(repository_id)
# Returns:
# {
#     "total_nodes": 1500,
#     "nodes_by_type": {"file": 100, "symbol": 1400},
#     "total_edges": 2300,
#     "edges_by_type": {"IMPORTS": 500, "CONTAINS": 1800},
#     "nodes_by_language": {"Python": 800, "JavaScript": 600}
# }
```

## Workflow

### Building a Graph

```
1. User/API triggers graph building
   ↓
2. GraphBuilder initialized with session
   ↓
3. GraphBuilder queries GraphRegistry for analyzers
   ↓
4. For each analyzer (by priority):
   a. Check can_analyze() → skip if false
   b. Call cleanup() if cleanup=True
   c. Call analyze() → create nodes/edges
   d. Collect statistics
   ↓
5. Aggregate results and return statistics
```

### Querying the Graph

```
1. User/API queries graph
   ↓
2. GraphService initialized with session
   ↓
3. GraphService executes SQLAlchemy queries
   ↓
4. Results returned to caller
```

## Extension Pattern

To add a new relationship type:

1. **Create Analyzer Class**:
```python
class CallAnalyzer(GraphInterface):
    _relationship_type = "CALLS"  # For registry
    
    @property
    def relationship_type(self) -> str:
        return "CALLS"
    
    @property
    def supported_languages(self) -> list[str]:
        return ["*"]  # All languages
    
    async def analyze(self, repository_id: UUID) -> dict:
        # Implementation
        pass
    
    async def can_analyze(self, repository_id: UUID) -> bool:
        # Check if symbols exist
        pass
    
    def get_priority(self) -> int:
        return 200  # Run after file/symbol creation
```

2. **Register Analyzer**:
```python
from app.services.graph import register_analyzer
register_analyzer(CallAnalyzer)
```

3. **Analyzer Runs Automatically**:
When `GraphBuilder.build_graph()` is called, the new analyzer will be included.

## Design Principles

1. **Separation of Concerns**: Each analyzer handles one relationship type
2. **Plugin Architecture**: New analyzers added without modifying core
3. **Priority-based Execution**: Control analyzer order via `get_priority()`
4. **Graceful Degradation**: Individual analyzer failures don't break entire build
5. **Language Agnostic**: Framework supports any language with appropriate analyzer
6. **Query Flexibility**: GraphService provides building blocks for complex queries

## Integration Points

### With Database Layer
- Uses `RepositoryNode` and `RepositoryEdge` models
- Queries `Repository`, `RepositoryFile`, `RepositorySymbol` for input data
- No direct schema modifications

### With Parser System
- Analyzers read `RepositorySymbol` metadata
- Uses `symbol_type`, `signature`, `symbol_metadata` fields
- No parser modifications needed

### With Indexing Pipeline
- Graph building triggered after symbol extraction
- Can be integrated into `RepositoryIndexer` workflow
- Independent operation - can run separately

## Future Enhancements

- **Incremental Updates**: Track changed files and update only affected subgraph
- **Caching Layer**: Cache frequently accessed graph queries
- **Async Analyzers**: Parallel analyzer execution with async/await
- **Graph Algorithms**: PageRank, community detection, centrality measures
- **Visualization Data**: Export formats for graph visualization tools
- **Query Language**: DSL for complex graph queries

## Testing

To test the framework:

```python
# Test analyzer registration
registry = GraphRegistry()
registry.register(MyAnalyzer)
assert registry.has_analyzer("MY_TYPE")

# Test builder orchestration
builder = GraphBuilder(session)
result = await builder.build_graph(repository_id)
assert result["analyzers_run"] > 0

# Test service queries
service = GraphService(session)
nodes = await service.get_nodes_by_repository(repository_id)
assert len(nodes) > 0
```

## Summary

This framework provides a **flexible, extensible architecture** for building and querying repository knowledge graphs:

- ✅ No extraction logic (delegated to analyzers)
- ✅ No database schema changes (uses existing models)
- ✅ Plugin-based analyzer system
- ✅ Orchestration and query interfaces
- ✅ Ready for analyzer implementations

**Next Steps**: Implement concrete analyzers (ImportAnalyzer, ContainsAnalyzer, etc.)
