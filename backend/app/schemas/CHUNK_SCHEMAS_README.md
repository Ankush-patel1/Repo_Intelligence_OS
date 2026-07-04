# Chunk Schemas - Quick Reference

## Import

```python
from app.schemas.chunk import (
    ChunkContext,
    ChunkMetadata,
    ChunkResult,
    ChunkRelationship,
)
```

## Schema Overview

| Schema | Purpose | Fields | Required Fields |
|--------|---------|--------|-----------------|
| `ChunkContext` | Context information | 8 | 0 (all optional) |
| `ChunkMetadata` | Detailed metadata | 26 | 0 (all optional) |
| `ChunkResult` | Complete chunk | 13 | 8 (core fields) |
| `ChunkRelationship` | Chunk relationships | 7 | 3 (ids + type) |

## Quick Examples

### ChunkContext
```python
context = ChunkContext(
    imports=["from typing import List"],
    parent_definition="class MyClass:",
    docstring="Method documentation",
    decorators=["@staticmethod"],
)
```

### ChunkMetadata
```python
metadata = ChunkMetadata(
    symbol_type="function",
    signature="def foo(x: int) -> str:",
    parameters=["x"],
    return_type="str",
    start_line=10,
    end_line=20,
)
```

### ChunkResult
```python
chunk = ChunkResult(
    repository_id=uuid4(),
    chunk_type="function",  # Validated enum
    chunk_name="my_function",
    language="python",
    content="def my_function():\n    pass",
    token_count=10,
    content_hash="a" * 64,  # SHA256 hex
    metadata=metadata,
    context=context,
)
```

### ChunkRelationship
```python
rel = ChunkRelationship(
    source_chunk_id=uuid4(),
    target_chunk_id=uuid4(),
    relationship_type="calls",  # Validated enum
    relationship_strength=0.95,  # 0.0-1.0
    metadata={"call_count": 5},
)
```

## Allowed Values

### chunk_type (ChunkResult)
- `function`, `method`, `class`, `imports`
- `interface`, `test`, `documentation`, `configuration`

### relationship_type (ChunkRelationship)
- `calls`, `called_by`
- `imports`, `imported_by`
- `inherits`, `inherited_by`
- `implements`, `implemented_by`
- `tests`, `tested_by`
- `documents`, `documented_by`
- `references`, `referenced_by`
- `contains`, `contained_by`
- `similar_to`
- `depends_on`, `depended_by`

## Validation Rules

1. **ChunkResult:**
   - chunk_type must be valid enum value
   - content_hash must be 64-char hex string
   - token_count must be ≥ 0

2. **ChunkMetadata:**
   - end_line must be ≥ start_line
   - Numeric fields validated for appropriate ranges

3. **ChunkRelationship:**
   - relationship_type must be valid enum value
   - source_chunk_id ≠ target_chunk_id
   - relationship_strength must be 0.0-1.0

## Serialization

```python
# To JSON
json_str = chunk.model_dump_json()

# From JSON
chunk = ChunkResult.model_validate_json(json_str)

# To dict
data = chunk.model_dump()

# From dict
chunk = ChunkResult.model_validate(data)

# From ORM model (requires from_attributes=True)
chunk = ChunkResult.model_validate(db_chunk)
```

## Common Patterns

### Creating a function chunk with full context
```python
chunk = ChunkResult(
    repository_id=repo_id,
    repository_file_id=file_id,
    symbol_id=symbol_id,
    chunk_type="function",
    chunk_name="calculate_total",
    language="python",
    content="def calculate_total(items):\n    return sum(items)",
    token_count=25,
    content_hash=hashlib.sha256(content.encode()).hexdigest(),
    metadata=ChunkMetadata(
        symbol_type="function",
        signature="def calculate_total(items):",
        parameters=["items"],
        start_line=10,
        end_line=12,
    ),
    context=ChunkContext(
        imports=["from typing import List"],
        docstring="Calculate sum of items.",
    ),
)
```

### Creating relationships between chunks
```python
# Function A calls Function B
ChunkRelationship(
    source_chunk_id=chunk_a.id,
    target_chunk_id=chunk_b.id,
    relationship_type="calls",
    relationship_strength=0.9,
)

# Test tests function
ChunkRelationship(
    source_chunk_id=test_chunk.id,
    target_chunk_id=func_chunk.id,
    relationship_type="tests",
)
```

## See Also

- Full documentation: `CHUNK_SCHEMAS_IMPLEMENTATION.md`
- Verification script: `verify_chunk_schemas.py`
- Schema definitions: `app/schemas/chunk.py`
