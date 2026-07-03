# Node Extractor Documentation

## Overview

The `NodeExtractor` service converts existing database models (`Repository`, `RepositoryFile`, `RepositorySymbol`) into `RepositoryNode` objects for the knowledge graph.

**Key Characteristics:**
- ✅ No edge creation
- ✅ No database persistence
- ✅ Returns in-memory node objects only
- ✅ Preserves all original metadata
- ✅ Supports selective extraction

---

## Class: NodeExtractor

**Location**: `app/services/graph/node_extractor.py`

### Initialization

```python
from app.services.graph import NodeExtractor

extractor = NodeExtractor(session)
```

**Parameters:**
- `session: AsyncSession` - Database session for querying existing models

---

## Methods

### 1. extract_repository_nodes()

Extract all nodes (repository, files, symbols) for a repository.

**Signature:**
```python
async def extract_repository_nodes(
    repository_id: UUID
) -> list[RepositoryNode]
```

**Returns:**
- List of `RepositoryNode` objects (not persisted to database)
- Includes: 1 repository node + N file nodes + M symbol nodes

**Example:**
```python
nodes = await extractor.extract_repository_nodes(repository_id)
# Returns: [repo_node, file1_node, file2_node, ..., symbol1_node, ...]

print(f"Total nodes: {len(nodes)}")
# Total nodes: 1523

repo_nodes = [n for n in nodes if n.node_type == "repository"]
file_nodes = [n for n in nodes if n.node_type == "file"]
symbol_nodes = [n for n in nodes if n.node_type == "symbol"]

print(f"Repository: {len(repo_nodes)}, Files: {len(file_nodes)}, Symbols: {len(symbol_nodes)}")
# Repository: 1, Files: 150, Symbols: 1372
```

---

### 2. extract_repository_node()

Extract the repository root node.

**Signature:**
```python
async def extract_repository_node(
    repository_id: UUID
) -> RepositoryNode | None
```

**Returns:**
- Single `RepositoryNode` for the repository
- `None` if repository not found

**Node Properties:**
```python
node = await extractor.extract_repository_node(repository_id)

# Properties
node.node_type           # "repository"
node.display_name        # "owner/repo-name"
node.language            # None
node.repository_id       # UUID
node.repository_file_id  # None
node.symbol_id           # None

# Metadata (JSON)
metadata = json.loads(node.node_metadata)
# {
#     "full_name": "owner/repo-name",
#     "owner": "owner",
#     "name": "repo-name",
#     "branch": "main",
#     "default_branch": "main",
#     "private": false,
#     "clone_path": "/path/to/repo"
# }
```

---

### 3. extract_file_nodes()

Extract all file nodes for a repository.

**Signature:**
```python
async def extract_file_nodes(
    repository_id: UUID
) -> list[RepositoryNode]
```

**Returns:**
- List of `RepositoryNode` objects for files
- Sorted by relative path

**Node Properties:**
```python
nodes = await extractor.extract_file_nodes(repository_id)

for node in nodes[:3]:
    # Properties
    node.node_type           # "file"
    node.display_name        # "src/utils/helper.py"
    node.language            # "Python"
    node.repository_id       # UUID
    node.repository_file_id  # UUID (links to RepositoryFile)
    node.symbol_id           # None
    
    # Metadata (JSON)
    metadata = json.loads(node.node_metadata)
    # {
    #     "relative_path": "src/utils/helper.py",
    #     "absolute_path": "/full/path/to/file.py",
    #     "file_name": "helper.py",
    #     "extension": ".py",
    #     "size_bytes": 2048,
    #     "line_count": 75,
    #     "sha256_hash": "abc123...",
    #     "is_binary": false
    # }
```

---

### 4. extract_symbol_nodes()

Extract all symbol nodes for a repository.

**Signature:**
```python
async def extract_symbol_nodes(
    repository_id: UUID
) -> list[RepositoryNode]
```

**Returns:**
- List of `RepositoryNode` objects for symbols
- Sorted by file path, then line number

**Node Properties:**
```python
nodes = await extractor.extract_symbol_nodes(repository_id)

for node in nodes[:3]:
    # Properties
    node.node_type           # "symbol"
    node.display_name        # "MyClass" or "my_function"
    node.language            # "Python"
    node.repository_id       # UUID
    node.repository_file_id  # UUID (links to RepositoryFile)
    node.symbol_id           # UUID (links to RepositorySymbol)
    
    # Metadata (JSON)
    metadata = json.loads(node.node_metadata)
    # {
    #     "symbol_type": "class" | "function" | "method" | etc.,
    #     "signature": "def my_function(arg1, arg2)",
    #     "start_line": 10,
    #     "end_line": 25,
    #     "start_column": 0,
    #     "end_column": 4,
    #     "parent_symbol_id": "uuid-of-parent" | null,
    #     "original_metadata": {
    #         "decorators": ["@staticmethod"],
    #         "parameters": ["arg1", "arg2"],
    #         "is_async": false
    #     }
    # }
```

---

### 5. extract_file_node()

Extract a single file node by ID.

**Signature:**
```python
async def extract_file_node(
    file_id: UUID
) -> RepositoryNode | None
```

**Returns:**
- Single `RepositoryNode` for the file
- `None` if file not found

**Example:**
```python
node = await extractor.extract_file_node(file_id)

if node:
    print(f"File: {node.display_name}")
    print(f"Language: {node.language}")
```

---

### 6. extract_symbol_node()

Extract a single symbol node by ID.

**Signature:**
```python
async def extract_symbol_node(
    symbol_id: UUID
) -> RepositoryNode | None
```

**Returns:**
- Single `RepositoryNode` for the symbol
- `None` if symbol not found

**Example:**
```python
node = await extractor.extract_symbol_node(symbol_id)

if node:
    print(f"Symbol: {node.display_name}")
    metadata = json.loads(node.node_metadata)
    print(f"Type: {metadata['symbol_type']}")
    print(f"Location: lines {metadata['start_line']}-{metadata['end_line']}")
```

---

### 7. extract_nodes_by_type()

Extract nodes of a specific type only.

**Signature:**
```python
async def extract_nodes_by_type(
    repository_id: UUID,
    node_type: str
) -> list[RepositoryNode]
```

**Parameters:**
- `node_type: str` - Must be "repository", "file", or "symbol"

**Returns:**
- List of `RepositoryNode` objects of the specified type

**Raises:**
- `ValueError` if node_type is invalid

**Example:**
```python
# Get only file nodes
file_nodes = await extractor.extract_nodes_by_type(repository_id, "file")

# Get only symbol nodes
symbol_nodes = await extractor.extract_nodes_by_type(repository_id, "symbol")

# Get only repository node
repo_nodes = await extractor.extract_nodes_by_type(repository_id, "repository")
```

---

### 8. get_node_statistics()

Get statistics about extractable nodes (without actually extracting them).

**Signature:**
```python
async def get_node_statistics(
    repository_id: UUID
) -> dict[str, Any]
```

**Returns:**
```python
{
    "repository_nodes": 1,
    "file_nodes": 150,
    "symbol_nodes": 1372,
    "total_nodes": 1523,
    "files_by_language": {
        "Python": 80,
        "JavaScript": 50,
        "TypeScript": 20
    },
    "symbols_by_language": {
        "Python": 800,
        "JavaScript": 400,
        "TypeScript": 172
    },
    "symbols_by_type": {
        "function": 600,
        "class": 200,
        "method": 400,
        "import": 150,
        "export": 22
    }
}
```

**Example:**
```python
stats = await extractor.get_node_statistics(repository_id)

print(f"Total nodes to extract: {stats['total_nodes']}")
print(f"Languages: {', '.join(stats['files_by_language'].keys())}")
print(f"Most common symbol type: {max(stats['symbols_by_type'], key=stats['symbols_by_type'].get)}")
```

---

## Node Structure

### RepositoryNode Properties

All extracted nodes are `RepositoryNode` instances with these properties:

| Property | Type | Description |
|----------|------|-------------|
| `id` | UUID | Auto-generated (not set in extraction) |
| `repository_id` | UUID | Links to Repository |
| `repository_file_id` | UUID \| None | Links to RepositoryFile (for file/symbol nodes) |
| `symbol_id` | UUID \| None | Links to RepositorySymbol (for symbol nodes) |
| `node_type` | str | "repository", "file", or "symbol" |
| `display_name` | str | Human-readable name |
| `language` | str \| None | Programming language (file/symbol nodes) |
| `node_metadata` | str | JSON metadata (type-specific properties) |
| `created_at` | DateTime | Auto-set on persist (not set in extraction) |

### Node Types

#### Repository Node
```python
{
    "node_type": "repository",
    "display_name": "owner/repo-name",
    "language": None,
    "metadata": {
        "full_name": "owner/repo-name",
        "owner": "owner",
        "name": "repo-name",
        "branch": "main",
        "default_branch": "main",
        "private": false,
        "clone_path": "/path"
    }
}
```

#### File Node
```python
{
    "node_type": "file",
    "display_name": "src/utils/helper.py",
    "language": "Python",
    "metadata": {
        "relative_path": "src/utils/helper.py",
        "absolute_path": "/full/path",
        "file_name": "helper.py",
        "extension": ".py",
        "size_bytes": 2048,
        "line_count": 75,
        "sha256_hash": "abc123...",
        "is_binary": false
    }
}
```

#### Symbol Node
```python
{
    "node_type": "symbol",
    "display_name": "MyClass",
    "language": "Python",
    "metadata": {
        "symbol_type": "class",
        "signature": "class MyClass",
        "start_line": 10,
        "end_line": 25,
        "start_column": 0,
        "end_column": 4,
        "parent_symbol_id": "uuid-or-null",
        "original_metadata": {
            "decorators": ["@decorator"],
            "parameters": ["param1"],
            "is_async": false
        }
    }
}
```

---

## Usage Patterns

### Pattern 1: Extract All Nodes

```python
from app.services.graph import NodeExtractor

extractor = NodeExtractor(session)

# Get all nodes for a repository
nodes = await extractor.extract_repository_nodes(repository_id)

# Separate by type
repo_node = next(n for n in nodes if n.node_type == "repository")
file_nodes = [n for n in nodes if n.node_type == "file"]
symbol_nodes = [n for n in nodes if n.node_type == "symbol"]

print(f"Extracted {len(nodes)} total nodes")
```

### Pattern 2: Extract Specific Type

```python
# Only extract symbol nodes (most common case)
symbol_nodes = await extractor.extract_nodes_by_type(repository_id, "symbol")

# Process symbols
for node in symbol_nodes:
    metadata = json.loads(node.node_metadata)
    if metadata["symbol_type"] == "function":
        print(f"Function: {node.display_name}")
```

### Pattern 3: Check Before Extracting

```python
# Get statistics first
stats = await extractor.get_node_statistics(repository_id)

if stats["total_nodes"] > 10000:
    print("Large repository - consider batch processing")
else:
    # Extract all at once
    nodes = await extractor.extract_repository_nodes(repository_id)
```

### Pattern 4: Selective Extraction

```python
# Extract only Python files
all_file_nodes = await extractor.extract_file_nodes(repository_id)
python_files = [n for n in all_file_nodes if n.language == "Python"]

# Extract symbols for specific file
file_node = await extractor.extract_file_node(file_id)
symbol_nodes = await extractor.extract_symbol_nodes(repository_id)
file_symbols = [
    n for n in symbol_nodes 
    if n.repository_file_id == file_node.repository_file_id
]
```

---

## Integration with Graph Framework

The `NodeExtractor` is designed to work with the graph framework:

```python
from app.services.graph import NodeExtractor, GraphBuilder

# In an analyzer's analyze() method:
class ContainsAnalyzer(GraphInterface):
    async def analyze(self, repository_id: UUID) -> dict:
        # Extract nodes
        extractor = NodeExtractor(self.session)
        nodes = await extractor.extract_repository_nodes(repository_id)
        
        # Now create edges between nodes
        # (edge creation logic here)
        
        # Persist nodes and edges
        # (persistence logic here)
        
        return {
            "nodes_created": len(nodes),
            "edges_created": edge_count
        }
```

---

## Important Notes

### ✅ What NodeExtractor Does:
- Queries existing `Repository`, `RepositoryFile`, `RepositorySymbol` models
- Converts them to `RepositoryNode` objects
- Preserves all metadata as JSON
- Returns in-memory objects

### ❌ What NodeExtractor Does NOT Do:
- Create edges (`RepositoryEdge`)
- Persist nodes to database
- Modify existing models
- Analyze relationships
- Resolve references

### Performance Considerations:

1. **Large Repositories**: For repos with >10K symbols, consider:
   - Using `extract_nodes_by_type()` to load incrementally
   - Checking statistics first with `get_node_statistics()`
   - Processing in batches

2. **Memory Usage**: All nodes are loaded into memory
   - 1K nodes ≈ ~1MB memory
   - 10K nodes ≈ ~10MB memory
   - 100K nodes ≈ ~100MB memory

3. **Database Queries**: Efficient queries with proper joins
   - Repository: 1 query
   - Files: 1 query (all files at once)
   - Symbols: 1 query (all symbols at once, joined with files)

---

## Summary

The `NodeExtractor`:
- ✅ Converts existing database models to graph nodes
- ✅ Preserves all original metadata
- ✅ Returns in-memory objects (not persisted)
- ✅ No edge creation (that's for analyzers)
- ✅ Efficient queries with joins
- ✅ Supports selective extraction
- ✅ Provides statistics

**Next Step**: Use extracted nodes in graph analyzers to create edges and persist the complete graph.
