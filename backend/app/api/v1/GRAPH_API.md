# Graph API Documentation

## Overview

The Graph API provides endpoints for building and querying the repository knowledge graph. The knowledge graph represents relationships between repositories, files, and code symbols.

## Endpoints

### 1. Build Repository Graph

**POST** `/repositories/{repository_id}/graph`

Builds and persists the knowledge graph for a repository. Extracts nodes from existing repository data and creates edges representing relationships.

**Path Parameters:**
- `repository_id` (UUID): Repository identifier

**Response:** `GraphBuildResponse`
```json
{
  "repository_id": "uuid",
  "nodes_persisted": 1250,
  "edges_persisted": 3400,
  "nodes_deleted": 1100,
  "edges_deleted": 0,
  "cleanup_performed": true,
  "statistics": {
    "repository_id": "uuid",
    "total_nodes": 1250,
    "nodes_by_type": {
      "repository": 1,
      "file": 45,
      "symbol": 1204
    },
    "total_edges": 3400,
    "edges_by_type": {
      "CONTAINS": 1249,
      "IMPORTS": 150,
      "INHERITS": 45,
      "DECLARES": 1956
    },
    "graph_exists": true
  }
}
```

**Status Codes:**
- `201 Created`: Graph built successfully
- `404 Not Found`: Repository not found
- `400 Bad Request`: No nodes found (repository may not be indexed)

**Notes:**
- Replaces existing graph data for the repository
- Repository must be indexed first (use `POST /repositories/{id}/index`)
- Automatically commits the transaction

---

### 2. Get Complete Graph

**GET** `/repositories/{repository_id}/graph`

Retrieves the complete knowledge graph including all nodes and edges.

**Path Parameters:**
- `repository_id` (UUID): Repository identifier

**Response:** `GraphResponse`
```json
{
  "repository_id": "uuid",
  "nodes": [
    {
      "id": "uuid",
      "repository_id": "uuid",
      "repository_file_id": "uuid",
      "symbol_id": "uuid",
      "node_type": "symbol",
      "display_name": "MyClass.my_method",
      "language": "python",
      "metadata": {
        "symbol_type": "method",
        "signature": "def my_method(self, x: int) -> str:",
        "start_line": 42,
        "end_line": 58
      },
      "created_at": "2026-07-03T12:00:00Z"
    }
  ],
  "edges": [
    {
      "id": "uuid",
      "source_node_id": "uuid",
      "target_node_id": "uuid",
      "relationship_type": "CONTAINS",
      "metadata": {
        "container_type": "class",
        "contained_type": "method",
        "parent_child": true
      },
      "created_at": "2026-07-03T12:00:00Z"
    }
  ],
  "statistics": {
    "repository_id": "uuid",
    "total_nodes": 1250,
    "nodes_by_type": {...},
    "total_edges": 3400,
    "edges_by_type": {...},
    "graph_exists": true
  }
}
```

**Status Codes:**
- `200 OK`: Graph retrieved successfully
- `404 Not Found`: Repository or graph not found

**Notes:**
- Returns all nodes and edges (can be large for big repositories)
- Consider using filtered endpoints for specific queries
- Metadata is parsed from JSON to dict

---

### 3. Get Graph Nodes

**GET** `/repositories/{repository_id}/graph/nodes`

Retrieves graph nodes with optional filtering.

**Path Parameters:**
- `repository_id` (UUID): Repository identifier

**Query Parameters:**
- `node_type` (string, optional): Filter by node type (`repository`, `file`, `symbol`)
- `language` (string, optional): Filter by programming language (`python`, `javascript`, etc.)

**Response:** `list[GraphNodeResponse]`

**Example Queries:**
- Get all symbol nodes: `?node_type=symbol`
- Get Python nodes: `?language=python`
- Get Python symbols: `?node_type=symbol&language=python`

**Status Codes:**
- `200 OK`: Nodes retrieved successfully
- `404 Not Found`: Repository not found

---

### 4. Get Graph Edges

**GET** `/repositories/{repository_id}/graph/edges`

Retrieves graph edges with optional filtering.

**Path Parameters:**
- `repository_id` (UUID): Repository identifier

**Query Parameters:**
- `relationship_type` (string, optional): Filter by relationship type

**Relationship Types:**
- `CONTAINS`: Container relationships (Repository→File, File→Symbol, Class→Method)
- `IMPORTS`: Import relationships
- `CALLS`: Function/method call relationships
- `INHERITS`: Class inheritance
- `IMPLEMENTS`: Interface implementation
- `DECLARES`: Declaration relationships (Function→Parameter, Class→Field)
- `REFERENCES`: General symbol references (decorators, types)
- `EXPORTS`: Export relationships
- `DEFINES`: Definition relationships
- `DEPENDS_ON`: Dependency relationships
- `BELONGS_TO`: Membership relationships

**Response:** `list[GraphEdgeResponse]`

**Example Queries:**
- Get inheritance edges: `?relationship_type=INHERITS`
- Get all import relationships: `?relationship_type=IMPORTS`

**Status Codes:**
- `200 OK`: Edges retrieved successfully
- `404 Not Found`: Repository not found

---

### 5. Get Single Node

**GET** `/repositories/{repository_id}/graph/node/{node_id}`

Retrieves a specific graph node.

**Path Parameters:**
- `repository_id` (UUID): Repository identifier
- `node_id` (UUID): Node identifier

**Response:** `GraphNodeResponse`

**Status Codes:**
- `200 OK`: Node retrieved successfully
- `404 Not Found`: Repository or node not found

---

## Data Models

### GraphNodeResponse

Represents a node in the knowledge graph.

**Fields:**
- `id` (UUID): Unique node identifier
- `repository_id` (UUID): Repository this node belongs to
- `repository_file_id` (UUID | null): Associated file (if applicable)
- `symbol_id` (UUID | null): Associated symbol (if applicable)
- `node_type` (string): Type of node (`repository`, `file`, `symbol`)
- `display_name` (string): Human-readable name
- `language` (string | null): Programming language
- `metadata` (dict | null): Type-specific metadata
- `created_at` (datetime): Node creation timestamp

**Node Types:**
- `repository`: Root node representing the entire repository
- `file`: File/module node
- `symbol`: Code symbol (function, class, method, variable, etc.)

### GraphEdgeResponse

Represents an edge (relationship) in the knowledge graph.

**Fields:**
- `id` (UUID): Unique edge identifier
- `source_node_id` (UUID): Source node of the relationship
- `target_node_id` (UUID): Target node of the relationship
- `relationship_type` (string): Type of relationship
- `metadata` (dict | null): Relationship-specific metadata
- `created_at` (datetime): Edge creation timestamp

### GraphResponse

Complete graph representation.

**Fields:**
- `repository_id` (UUID): Repository identifier
- `nodes` (list[GraphNodeResponse]): All graph nodes
- `edges` (list[GraphEdgeResponse]): All graph edges
- `statistics` (dict): Graph statistics

### GraphBuildResponse

Response from graph build operation.

**Fields:**
- `repository_id` (UUID): Repository identifier
- `nodes_persisted` (int): Number of nodes created
- `edges_persisted` (int): Number of edges created
- `nodes_deleted` (int): Number of old nodes removed
- `edges_deleted` (int): Number of old edges removed
- `cleanup_performed` (bool): Whether old data was cleaned up
- `statistics` (GraphStatisticsResponse): Final graph statistics

### GraphStatisticsResponse

Statistics about the graph.

**Fields:**
- `repository_id` (UUID): Repository identifier
- `total_nodes` (int): Total number of nodes
- `nodes_by_type` (dict[str, int]): Node counts by type
- `total_edges` (int): Total number of edges
- `edges_by_type` (dict[str, int]): Edge counts by relationship type
- `graph_exists` (bool): Whether graph data exists

---

## Workflow

### Building a Knowledge Graph

1. **Import Repository**
   ```bash
   POST /repositories/import
   {
     "repository": "owner/repo",
     "branch": "main"
   }
   ```

2. **Index Repository**
   ```bash
   POST /repositories/{id}/index
   ```

3. **Build Graph**
   ```bash
   POST /repositories/{id}/graph
   ```

### Querying the Graph

**Get All Nodes:**
```bash
GET /repositories/{id}/graph/nodes
```

**Get Python Classes:**
```bash
GET /repositories/{id}/graph/nodes?node_type=symbol&language=python
```

**Get Inheritance Relationships:**
```bash
GET /repositories/{id}/graph/edges?relationship_type=INHERITS
```

**Get Complete Graph:**
```bash
GET /repositories/{id}/graph
```

---

## Implementation Notes

### Graph Building Process

1. **Node Extraction**: Converts Repository, RepositoryFile, and RepositorySymbol records into graph nodes
2. **Edge Extraction**: Creates relationships based on parser metadata
3. **Persistence**: Stores nodes and edges to database with cleanup

### Metadata

Node and edge metadata is stored as JSON and automatically parsed to dictionaries in API responses.

**Example Node Metadata (Symbol):**
```json
{
  "symbol_type": "method",
  "signature": "def my_method(self, x: int) -> str:",
  "start_line": 42,
  "end_line": 58,
  "start_column": 4,
  "end_column": 0,
  "parent_symbol_id": "uuid",
  "original_metadata": {
    "parameters": ["self", "x"],
    "return_type": "str",
    "decorators": ["@property"]
  }
}
```

**Example Edge Metadata (CONTAINS):**
```json
{
  "container_type": "class",
  "contained_type": "method",
  "parent_child": true
}
```

### Performance Considerations

- Large repositories may have thousands of nodes and edges
- Use filtered endpoints (`/nodes`, `/edges`) for specific queries
- Consider pagination for production use (not currently implemented)
- Graph building is synchronous and may take time for large repositories

### Error Handling

- All endpoints validate repository existence
- Graph build requires indexed repository (files and symbols must exist)
- 404 errors returned for missing resources
- 400 errors returned for invalid operations

---

## Future Enhancements

Potential improvements:

1. **Pagination**: Add pagination for large result sets
2. **Graph Traversal**: Add endpoints for path finding and neighbor queries
3. **Incremental Updates**: Support updating graph without full rebuild
4. **Graph Analytics**: Add endpoints for graph metrics and analysis
5. **Export**: Support exporting graph to standard formats (GraphML, DOT)
6. **Search**: Add full-text search across nodes
7. **Filtering**: Advanced filtering with multiple criteria
