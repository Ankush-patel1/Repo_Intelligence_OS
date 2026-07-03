# Edge Extractor Documentation

## Overview

The `EdgeExtractor` service creates `RepositoryEdge` objects representing relationships between nodes based on parser output from `RepositorySymbol` metadata.

**Key Characteristics:**
- ✅ Uses parser output from symbols
- ✅ Creates 7 relationship types
- ✅ No database writes
- ✅ Returns in-memory edge objects only
- ✅ Preserves relationship metadata

---

## Supported Relationship Types

### 1. CONTAINS
**Hierarchy relationships**
- Repository CONTAINS File
- File CONTAINS Symbol
- Class CONTAINS Method
- Parent Symbol CONTAINS Child Symbol

### 2. IMPORTS
**Import relationships from import symbols**
- File IMPORTS File (implicit from import statements)
- Symbol IMPORTS Symbol

### 3. CALLS
**Function/method call relationships**
- Function CALLS Function
- Method CALLS Method/Function
- ⚠️ Placeholder: Requires enhanced parser output

### 4. INHERITS
**Class inheritance relationships**
- Class INHERITS Class (base classes)

### 5. IMPLEMENTS
**Interface implementation**
- Class IMPLEMENTS Interface

### 6. DECLARES
**Declaration relationships**
- Function DECLARES Parameter
- Class DECLARES Field

### 7. REFERENCES
**General symbol references**
- Symbol REFERENCES Decorator
- Symbol REFERENCES Type
- Symbol REFERENCES Variable

---

## Class: EdgeExtractor

**Location**: `app/services/graph/edge_extractor.py`

### Initialization

```python
from app.services.graph import EdgeExtractor

extractor = EdgeExtractor(session)
```

**Parameters:**
- `session: AsyncSession` - Database session for querying symbols

---

## Methods

### 1. extract_all_edges()

Extract all edge types for a repository.

**Signature:**
```python
async def extract_all_edges(
    repository_id: UUID,
    nodes: list[RepositoryNode],
) -> list[RepositoryEdge]
```

**Parameters:**
- `repository_id: UUID` - Repository to extract edges for
- `nodes: list[RepositoryNode]` - Pre-extracted nodes (from NodeExtractor)

**Returns:**
- List of `RepositoryEdge` objects (not persisted to database)
- Includes all relationship types

**Example:**
```python
from app.services.graph import NodeExtractor, EdgeExtractor

# Extract nodes first
node_extractor = NodeExtractor(session)
nodes = await node_extractor.extract_repository_nodes(repository_id)

# Extract edges
edge_extractor = EdgeExtractor(session)
edges = await edge_extractor.extract_all_edges(repository_id, nodes)

print(f"Total edges: {len(edges)}")
# Total edges: 2543

# Count by type
from collections import Counter
edge_types = Counter(e.relationship_type for e in edges)
print(edge_types)
# Counter({'CONTAINS': 1800, 'IMPORTS': 450, 'DECLARES': 250, 'REFERENCES': 43})
```

---

### 2. extract_contains_edges()

Extract CONTAINS relationships (hierarchy).

**Signature:**
```python
async def extract_contains_edges(
    nodes: list[RepositoryNode]
) -> list[RepositoryEdge]
```

**Creates:**
1. Repository → File edges
2. File → Symbol edges
3. Parent Symbol → Child Symbol edges (using parent_symbol_id)

**Edge Metadata:**
```json
{
    "container_type": "repository" | "file" | "class" | "symbol",
    "contained_type": "file" | "symbol" | "method",
    "parent_child": true  // for symbol hierarchies
}
```

**Example:**
```python
contains_edges = await extractor.extract_contains_edges(nodes)

for edge in contains_edges[:3]:
    print(f"{edge.source_node_id} CONTAINS {edge.target_node_id}")
    metadata = json.loads(edge.edge_metadata)
    print(f"  Type: {metadata['container_type']} → {metadata['contained_type']}")
```

---

### 3. extract_imports_edges()

Extract IMPORTS relationships from import symbols.

**Signature:**
```python
async def extract_imports_edges(
    repository_id: UUID,
    nodes: list[RepositoryNode],
    node_by_symbol: dict[UUID, RepositoryNode],
) -> list[RepositoryEdge]
```

**Parameters:**
- `node_by_symbol: dict` - Map of symbol_id to RepositoryNode for lookup

**Creates:**
- Edges from import/from_import symbols
- Preserves import statement and type

**Edge Metadata:**
```json
{
    "import_statement": "from module import function",
    "import_type": "import" | "from_import" | "import_statement"
}
```

**Note**: Target resolution (which file is imported) requires import resolver.
Currently creates edges with placeholder targets.

**Example:**
```python
node_by_symbol = {n.symbol_id: n for n in nodes if n.symbol_id}
imports_edges = await extractor.extract_imports_edges(
    repository_id, nodes, node_by_symbol
)

for edge in imports_edges[:3]:
    metadata = json.loads(edge.edge_metadata)
    print(f"Import: {metadata['import_statement']}")
```

---

### 4. extract_inherits_edges()

Extract INHERITS relationships from class metadata.

**Signature:**
```python
async def extract_inherits_edges(
    repository_id: UUID,
    nodes: list[RepositoryNode],
    node_by_symbol: dict[UUID, RepositoryNode],
) -> list[RepositoryEdge]
```

**Creates:**
- Class → Base Class edges
- Extracted from symbol metadata `base_classes` field

**Edge Metadata:**
```json
{
    "base_class": "BaseClassName",
    "derived_class": "DerivedClassName"
}
```

**Note**: Requires parsers to extract base class information into symbol metadata.

**Example:**
```python
inherits_edges = await extractor.extract_inherits_edges(
    repository_id, nodes, node_by_symbol
)

for edge in inherits_edges:
    metadata = json.loads(edge.edge_metadata)
    print(f"{metadata['derived_class']} → {metadata['base_class']}")
```

---

### 5. extract_implements_edges()

Extract IMPLEMENTS relationships (class implements interface).

**Signature:**
```python
async def extract_implements_edges(
    repository_id: UUID,
    nodes: list[RepositoryNode],
    node_by_symbol: dict[UUID, RepositoryNode],
) -> list[RepositoryEdge]
```

**Creates:**
- Class → Interface edges
- Extracted from symbol metadata `interfaces` or `implements` field

**Edge Metadata:**
```json
{
    "interface": "InterfaceName",
    "implementing_class": "ClassName"
}
```

**Note**: Primarily for TypeScript, Java, Go (interface languages).

**Example:**
```python
implements_edges = await extractor.extract_implements_edges(
    repository_id, nodes, node_by_symbol
)

for edge in implements_edges:
    metadata = json.loads(edge.edge_metadata)
    print(f"{metadata['implementing_class']} implements {metadata['interface']}")
```

---

### 6. extract_declares_edges()

Extract DECLARES relationships (declarations).

**Signature:**
```python
async def extract_declares_edges(
    nodes: list[RepositoryNode],
    node_by_symbol: dict[UUID, RepositoryNode],
) -> list[RepositoryEdge]
```

**Creates:**
1. Function DECLARES Parameter (from parameters metadata)
2. Class DECLARES Field (from fields metadata)

**Edge Metadata:**
```json
{
    "declaration_type": "parameter" | "field",
    "parameter_name": "param1" | "field_name": "field1",
    "declared_in": "function_name" | "class_name"
}
```

**Example:**
```python
declares_edges = await extractor.extract_declares_edges(nodes, node_by_symbol)

for edge in declares_edges[:5]:
    metadata = json.loads(edge.edge_metadata)
    if metadata['declaration_type'] == 'parameter':
        print(f"Param: {metadata['parameter_name']} in {metadata['declared_in']}")
```

---

### 7. extract_references_edges()

Extract REFERENCES relationships (general references).

**Signature:**
```python
async def extract_references_edges(
    nodes: list[RepositoryNode],
    node_by_symbol: dict[UUID, RepositoryNode],
) -> list[RepositoryEdge]
```

**Creates:**
- Symbol → Decorator references
- Symbol → Type references
- Other general references from metadata

**Edge Metadata:**
```json
{
    "reference_type": "decorator" | "type" | "variable",
    "decorator_name": "@decorator_name",
    "used_by": "symbol_name"
}
```

**Example:**
```python
references_edges = await extractor.extract_references_edges(nodes, node_by_symbol)

for edge in references_edges:
    metadata = json.loads(edge.edge_metadata)
    if metadata['reference_type'] == 'decorator':
        print(f"Decorator: {metadata['decorator_name']} on {metadata['used_by']}")
```

---

### 8. extract_calls_edges()

Extract CALLS relationships (function/method calls).

**Signature:**
```python
async def extract_calls_edges(
    repository_id: UUID,
    nodes: list[RepositoryNode],
    node_by_symbol: dict[UUID, RepositoryNode],
) -> list[RepositoryEdge]
```

**Status**: ⚠️ **Placeholder Implementation**

**Returns:** Empty list (no edges)

**Reason:** Current parsers don't extract call expressions from AST.

**Future Implementation Requires:**
1. Enhanced parsers to extract function call expressions
2. Call target resolution logic
3. Cross-file call tracking

---

### 9. get_edge_statistics()

Get statistics about extracted edges.

**Signature:**
```python
async def get_edge_statistics(
    edges: list[RepositoryEdge]
) -> dict[str, Any]
```

**Returns:**
```python
{
    "total_edges": 2543,
    "edges_by_type": {
        "CONTAINS": 1800,
        "IMPORTS": 450,
        "DECLARES": 250,
        "REFERENCES": 43
    },
    "unique_relationship_types": 4
}
```

**Example:**
```python
stats = await extractor.get_edge_statistics(edges)

print(f"Total edges: {stats['total_edges']}")
print(f"Edge types: {stats['unique_relationship_types']}")

for rel_type, count in stats['edges_by_type'].items():
    print(f"  {rel_type}: {count}")
```

---

## Edge Structure

### RepositoryEdge Properties

All extracted edges are `RepositoryEdge` instances:

| Property | Type | Description |
|----------|------|-------------|
| `id` | UUID | Auto-generated (not set in extraction) |
| `source_node_id` | UUID | Source node of relationship |
| `target_node_id` | UUID | Target node of relationship |
| `relationship_type` | str | Type of relationship |
| `edge_metadata` | str | JSON metadata (relationship-specific) |
| `created_at` | DateTime | Auto-set on persist (not set) |

---

## Usage Patterns

### Pattern 1: Extract All Edges

```python
from app.services.graph import NodeExtractor, EdgeExtractor

# Step 1: Extract nodes
node_extractor = NodeExtractor(session)
nodes = await node_extractor.extract_repository_nodes(repository_id)

# Step 2: Extract all edges
edge_extractor = EdgeExtractor(session)
edges = await edge_extractor.extract_all_edges(repository_id, nodes)

# Step 3: Get statistics
stats = await edge_extractor.get_edge_statistics(edges)
print(f"Created {stats['total_edges']} edges")
```

### Pattern 2: Extract Specific Edge Type

```python
# Only extract CONTAINS relationships
contains_edges = await edge_extractor.extract_contains_edges(nodes)

print(f"CONTAINS edges: {len(contains_edges)}")
```

### Pattern 3: Complete Graph Extraction

```python
# Full workflow: nodes + edges
nodes = await node_extractor.extract_repository_nodes(repository_id)
edges = await edge_extractor.extract_all_edges(repository_id, nodes)

# Now you have complete graph in memory
print(f"Graph: {len(nodes)} nodes, {len(edges)} edges")

# Persist together (in analyzer or service)
session.add_all(nodes)
session.add_all(edges)
await session.flush()
```

### Pattern 4: Filter and Analyze

```python
edges = await edge_extractor.extract_all_edges(repository_id, nodes)

# Find all imports
import_edges = [e for e in edges if e.relationship_type == "IMPORTS"]

# Find container relationships
contains_edges = [e for e in edges if e.relationship_type == "CONTAINS"]

# Analyze edge metadata
for edge in import_edges[:5]:
    metadata = json.loads(edge.edge_metadata)
    print(f"Import: {metadata.get('import_statement')}")
```

---

## Parser Output Requirements

### What EdgeExtractor Expects from Parsers:

#### Import Symbols
```python
RepositorySymbol(
    symbol_type="import" | "from_import",
    symbol_name="import statement",
    signature="full import line"
)
```

#### Class Symbols with Inheritance
```python
RepositorySymbol(
    symbol_type="class",
    symbol_metadata=json.dumps({
        "base_classes": ["BaseClass1", "BaseClass2"],
        "interfaces": ["Interface1"],
        "fields": ["field1", "field2"]
    })
)
```

#### Function/Method Symbols
```python
RepositorySymbol(
    symbol_type="function" | "method",
    symbol_metadata=json.dumps({
        "parameters": ["param1", "param2"],
        "decorators": ["@decorator1"],
        "is_async": False
    })
)
```

#### Symbol Hierarchy
```python
RepositorySymbol(
    parent_symbol=parent_uuid,  # Links to parent
    # Class method has parent_symbol = class UUID
)
```

---

## Limitations and Future Work

### Current Limitations:

1. **CALLS Edges**: Not implemented
   - Requires parser enhancement to extract call expressions
   - Need call target resolution

2. **Import Target Resolution**: Placeholder
   - Import edges have self-references
   - Need import resolver to find actual target files/symbols

3. **Inheritance Target Resolution**: Placeholder
   - Base class names extracted but not resolved to actual classes
   - Need symbol resolver

4. **Cross-File References**: Limited
   - Only handles references within symbol metadata
   - Need comprehensive reference tracking

### Future Enhancements:

1. **Import Resolver Integration**
   ```python
   # Resolve import targets
   resolver = ImportResolver(session)
   for edge in import_edges:
       target_node = await resolver.resolve_import(edge)
       edge.target_node_id = target_node.id
   ```

2. **Call Graph Extraction**
   ```python
   # Requires enhanced parsers
   call_edges = await extractor.extract_calls_edges(
       repository_id, nodes, node_by_symbol
   )
   ```

3. **Type Resolution**
   ```python
   # Resolve type annotations to actual types
   type_edges = await extractor.extract_type_edges(
       repository_id, nodes
   )
   ```

---

## Integration with Graph Framework

EdgeExtractor works with the complete extraction pipeline:

```python
from app.services.graph import NodeExtractor, EdgeExtractor

class MyGraphAnalyzer(GraphInterface):
    async def analyze(self, repository_id: UUID) -> dict:
        # 1. Extract nodes
        node_extractor = NodeExtractor(self.session)
        nodes = await node_extractor.extract_repository_nodes(repository_id)
        
        # 2. Extract edges
        edge_extractor = EdgeExtractor(self.session)
        edges = await edge_extractor.extract_all_edges(repository_id, nodes)
        
        # 3. Persist
        self.session.add_all(nodes)
        self.session.add_all(edges)
        await self.session.flush()
        
        # 4. Statistics
        stats = await edge_extractor.get_edge_statistics(edges)
        
        return {
            "nodes_created": len(nodes),
            "edges_created": len(edges),
            **stats
        }
```

---

## Summary

The `EdgeExtractor`:
- ✅ Creates 7 relationship types from parser output
- ✅ Uses existing symbol metadata
- ✅ Returns in-memory edge objects (not persisted)
- ✅ Preserves relationship metadata as JSON
- ✅ No database writes
- ⚠️ Some edge types require target resolution
- ⚠️ CALLS edges require parser enhancement

**Complete Workflow:**
1. **NodeExtractor** → Extract nodes
2. **EdgeExtractor** → Create relationships
3. **Analyzer/Service** → Persist together

**Next Step**: Implement graph analyzers that use both extractors to build and persist complete graphs.
