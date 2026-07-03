# Pipeline Quick Reference

## Complete Analysis Pipeline

### One-Step Analysis (Recommended)

```bash
# Import repository
curl -X POST http://localhost:8000/api/v1/repositories/import \
  -H "Content-Type: application/json" \
  -d '{"repository": "owner/repo", "branch": "main"}'

# Get repository ID from response
REPO_ID="<uuid-from-response>"

# Run complete analysis (Index + Parse + Build Graph)
curl -X POST http://localhost:8000/api/v1/repositories/$REPO_ID/analyze
```

**Result:** Repository fully analyzed with knowledge graph built.

---

## Pipeline Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/repositories/{id}/analyze` | POST | **Full pipeline** - Index + Parse + Build Graph |
| `/repositories/{id}/rebuild-graph` | POST | Rebuild graph from existing data |
| `/repositories/{id}/pipeline-status` | GET | Check pipeline completion status |
| `/repositories/{id}/index` | POST | Index only (manual) |
| `/repositories/{id}/graph` | POST | Build graph only (manual) |

---

## Workflow Options

### Option 1: One-Step (Recommended)
```bash
POST /repositories/import          # Import
POST /repositories/{id}/analyze    # Index + Parse + Graph
```

### Option 2: Manual Steps
```bash
POST /repositories/import          # Import
POST /repositories/{id}/index      # Index + Parse
POST /repositories/{id}/graph      # Build Graph
```

### Option 3: Rebuild Graph
```bash
# If repository already indexed
POST /repositories/{id}/rebuild-graph
```

---

## Response Structure

### Analyze Response
```json
{
  "repository_id": "uuid",
  "indexing": {
    "total_files": 45,
    "symbols": {
      "total_symbols": 340,
      "files_parsed": 45
    }
  },
  "graph": {
    "nodes_persisted": 386,
    "edges_persisted": 920,
    "statistics": {
      "total_nodes": 386,
      "total_edges": 920
    }
  },
  "pipeline_complete": true
}
```

### Pipeline Status Response
```json
{
  "repository_id": "uuid",
  "indexed": true,
  "graph_built": true,
  "indexing_stats": {...},
  "graph_stats": {...}
}
```

---

## Querying the Graph

After analysis, query the knowledge graph:

```bash
# Get complete graph
GET /repositories/{id}/graph

# Get nodes (filterable)
GET /repositories/{id}/graph/nodes?node_type=symbol&language=python

# Get edges (filterable)
GET /repositories/{id}/graph/edges?relationship_type=INHERITS

# Get specific node
GET /repositories/{id}/graph/node/{node_id}
```

---

## Pipeline Flow

```
1. Import     → Repository created, code cloned
2. Index      → Files scanned, metadata stored
3. Parse      → Symbols extracted, AST analyzed
4. Build Graph→ Nodes created, relationships mapped
```

---

## Check Status

```bash
# Check what's been completed
curl http://localhost:8000/api/v1/repositories/{id}/pipeline-status

# Response shows:
# - indexed: true/false
# - graph_built: true/false
# - Statistics for each stage
```

---

## Use Cases

### Full Analysis
```bash
POST /repositories/{id}/analyze
```
**When:** First-time analysis of a repository

### Rebuild Graph
```bash
POST /repositories/{id}/rebuild-graph
```
**When:** 
- Graph logic updated
- Need to regenerate relationships
- Data already indexed

### Check Progress
```bash
GET /repositories/{id}/pipeline-status
```
**When:** 
- Verify what's been completed
- Check before running operations
- Get current statistics

---

## Error Handling

- **404 Not Found**: Repository doesn't exist
- **400 Bad Request**: Repository not indexed (run analyze first)
- **500 Server Error**: Processing error (check logs)

---

## Performance

| Repository Size | Analysis Time |
|----------------|---------------|
| Small (<100 files) | ~5-10 seconds |
| Medium (100-1000 files) | ~30-60 seconds |
| Large (>1000 files) | Several minutes |

---

## Summary

**Simplest workflow:**
1. Import: `POST /repositories/import`
2. Analyze: `POST /repositories/{id}/analyze`
3. Query: `GET /repositories/{id}/graph/nodes`

Done! ✅
