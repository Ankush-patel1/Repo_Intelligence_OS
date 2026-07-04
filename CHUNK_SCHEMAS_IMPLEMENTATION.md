# Chunk Schemas Implementation - Summary

**Date:** July 4, 2026  
**Status:** ✅ COMPLETED

---

## Implementation Complete

All shared chunk schemas have been successfully implemented as Pydantic models with full validation, serialization, and type safety.

---

## Files Created

### 1. Schema Definitions
**File:** `backend/app/schemas/chunk.py`

**Schemas Implemented:**
1. `ChunkContext` - Context information for chunks
2. `ChunkMetadata` - Detailed metadata for chunks
3. `ChunkResult` - Complete chunk representation
4. `ChunkRelationship` - Relationships between chunks

### 2. Verification Script
**File:** `backend/verify_chunk_schemas.py`

Comprehensive test suite covering:
- Schema creation and validation
- Serialization/deserialization
- Field validation rules
- Integration testing
- JSON schema generation

---

## Schema Details

### 1. ChunkContext

**Purpose:** Represents surrounding context needed to understand a chunk

**Fields (8):**
- `imports` (list[str]) - Import statements needed by chunk
- `parent_definition` (str | None) - Parent class/module definition
- `dependencies` (list[UUID]) - Symbol dependencies
- `related_chunks` (list[UUID]) - Related chunk references
- `docstring` (str | None) - Documentation string
- `decorators` (list[str]) - Applied decorators/annotations
- `context_before` (str | None) - Code before chunk
- `context_after` (str | None) - Code after chunk

**Features:**
- All fields optional with sensible defaults
- UUID references for graph linkage
- JSON serializable

**Example:**
```python
context = ChunkContext(
    imports=["from typing import List", "import json"],
    parent_definition="class MyClass:",
    docstring="Calculate the total of all items.",
    decorators=["@staticmethod", "@lru_cache"],
)
```

---

### 2. ChunkMetadata

**Purpose:** Type-specific metadata varying by chunk_type

**Fields (26):**

**Symbol Information:**
- `symbol_type` (str | None) - function, method, class, etc.
- `signature` (str | None) - Function/method signature
- `parameters` (list[str]) - Function parameters
- `return_type` (str | None) - Return type annotation

**Location:**
- `start_line` (int | None) - Starting line (≥1)
- `end_line` (int | None) - Ending line (≥1)
- `start_column` (int | None) - Starting column (≥0)
- `end_column` (int | None) - Ending column (≥0)

**Relationships:**
- `parent_symbol_id` (UUID | None) - Parent symbol reference
- `node_id` (UUID | None) - Knowledge graph node
- `calls` (list[UUID]) - Called symbols
- `called_by` (list[UUID]) - Calling symbols

**Class-Specific:**
- `inherits_from` (list[str]) - Base classes
- `implements` (list[str]) - Interfaces
- `method_count` (int | None) - Number of methods
- `is_abstract` (bool) - Abstract class/method flag

**Test-Specific:**
- `test_framework` (str | None) - pytest, jest, junit, etc.
- `tests_symbol_id` (UUID | None) - Symbol being tested
- `assertion_count` (int | None) - Number of assertions

**Access & Modifiers:**
- `access_modifier` (str | None) - public, private, protected
- `is_static` (bool) - Static flag
- `is_async` (bool) - Async flag

**Additional:**
- `complexity_score` (float | None) - Complexity metric (≥0.0)
- `has_examples` (bool) - Has code examples
- `tags` (list[str]) - Custom categorization tags
- `custom` (dict[str, Any]) - Language-specific metadata

**Validation:**
- `end_line` must be ≥ `start_line`
- Numeric fields validated for appropriate ranges

**Example:**
```python
metadata = ChunkMetadata(
    symbol_type="method",
    signature="def calculate(self, items: List[float]) -> float:",
    parameters=["self", "items"],
    return_type="float",
    start_line=42,
    end_line=58,
    parent_symbol_id=UUID("..."),
    access_modifier="public",
    is_async=True,
    complexity_score=3.5,
    tags=["business-logic", "calculations"],
)
```

---

### 3. ChunkResult

**Purpose:** Complete chunk representation with all properties

**Fields (13):**

**Identification:**
- `id` (UUID | None) - Unique identifier (populated after persistence)
- `repository_id` (UUID) - Repository reference (REQUIRED)
- `repository_file_id` (UUID | None) - File reference
- `symbol_id` (UUID | None) - Symbol reference

**Properties:**
- `chunk_type` (str) - Type of chunk (REQUIRED, validated)
- `chunk_name` (str) - Human-readable name (REQUIRED, 1-512 chars)
- `language` (str) - Programming language (REQUIRED, 1-32 chars)

**Content:**
- `content` (str) - Actual chunk content (REQUIRED, ≥1 char)

**Metrics:**
- `token_count` (int) - Token count (REQUIRED, ≥0)
- `content_hash` (str) - SHA256 hash (REQUIRED, 64 hex chars)

**Rich Data:**
- `metadata` (ChunkMetadata) - Detailed metadata (REQUIRED)
- `context` (ChunkContext | None) - Context information

**Timestamps:**
- `created_at` (datetime | None) - Creation timestamp

**Validation Rules:**

1. **chunk_type validation:**
   - Must be one of: function, method, class, imports, interface, test, documentation, configuration
   - Raises ValueError for invalid types

2. **content_hash validation:**
   - Must be exactly 64 characters
   - Must be valid hexadecimal (0-9, a-f)
   - Automatically lowercased

3. **Field constraints:**
   - chunk_name: 1-512 characters
   - language: 1-32 characters
   - content: minimum 1 character
   - token_count: ≥ 0

**Configuration:**
- `from_attributes = True` - Can create from ORM models
- Full JSON schema with examples

**Example:**
```python
chunk = ChunkResult(
    id=UUID("..."),
    repository_id=UUID("..."),
    repository_file_id=UUID("..."),
    symbol_id=UUID("..."),
    chunk_type="function",
    chunk_name="calculate_total",
    language="python",
    content="def calculate_total(items):\n    return sum(items)",
    token_count=25,
    content_hash="a" * 64,
    metadata=ChunkMetadata(...),
    context=ChunkContext(...),
)
```

---

### 4. ChunkRelationship

**Purpose:** Relationships between chunks for context expansion

**Fields (7):**
- `id` (UUID | None) - Unique identifier
- `source_chunk_id` (UUID) - Source chunk (REQUIRED)
- `target_chunk_id` (UUID) - Target chunk (REQUIRED)
- `relationship_type` (str) - Type of relationship (REQUIRED, validated)
- `relationship_strength` (float) - Strength 0.0-1.0 (default: 1.0)
- `metadata` (dict[str, Any]) - Additional metadata
- `created_at` (datetime | None) - Creation timestamp

**Relationship Types (19 allowed):**
- `calls` / `called_by` - Function/method calls
- `imports` / `imported_by` - Import relationships
- `inherits` / `inherited_by` - Class inheritance
- `implements` / `implemented_by` - Interface implementation
- `tests` / `tested_by` - Test relationships
- `documents` / `documented_by` - Documentation
- `references` / `referenced_by` - Symbol references
- `contains` / `contained_by` - Containment
- `similar_to` - Similarity
- `depends_on` / `depended_by` - Dependencies

**Validation Rules:**

1. **relationship_type validation:**
   - Must be one of the 19 allowed types
   - Raises ValueError for invalid types

2. **Different chunks validation:**
   - source_chunk_id ≠ target_chunk_id
   - Prevents self-references

3. **Strength bounds:**
   - Must be between 0.0 and 1.0 inclusive
   - Default value is 1.0

**Configuration:**
- `from_attributes = True` - Can create from ORM models
- Full JSON schema with examples

**Example:**
```python
relationship = ChunkRelationship(
    id=UUID("..."),
    source_chunk_id=UUID("..."),
    target_chunk_id=UUID("..."),
    relationship_type="calls",
    relationship_strength=0.95,
    metadata={
        "call_count": 5,
        "is_direct": True,
        "call_type": "method_call",
    },
)
```

---

## Type Aliases

Two convenience type aliases are provided:

```python
ChunkMetadataDict = dict[str, Any]
ChunkContextDict = dict[str, Any]
```

These can be used for raw dictionary operations when full Pydantic validation isn't needed.

---

## Validation Features

### Automatic Validation

All schemas include comprehensive validation:

1. **Type Checking:**
   - UUID fields validated as proper UUIDs
   - String fields checked for length constraints
   - Numeric fields validated for ranges

2. **Business Logic:**
   - end_line ≥ start_line
   - source_chunk_id ≠ target_chunk_id
   - Enum validation for chunk_type and relationship_type
   - Hash format validation (hexadecimal)

3. **Default Values:**
   - Empty lists for collection fields
   - Sensible defaults (relationship_strength=1.0)
   - Optional fields with None defaults

### Custom Validators

Implemented using Pydantic's `@field_validator`:

- `ChunkMetadata.end_line_after_start` - Ensures logical line ordering
- `ChunkResult.validate_chunk_type` - Enforces allowed chunk types
- `ChunkResult.validate_hash_format` - Validates SHA256 format
- `ChunkRelationship.validate_relationship_type` - Enforces allowed types
- `ChunkRelationship.validate_different_chunks` - Prevents self-references

---

## Serialization Support

### JSON Serialization

All schemas support full JSON serialization:

```python
# To JSON string
json_str = chunk.model_dump_json()

# To JSON with formatting
json_str = chunk.model_dump_json(indent=2)

# From JSON string
chunk = ChunkResult.model_validate_json(json_str)
```

### Dictionary Conversion

```python
# To dictionary
chunk_dict = chunk.model_dump()

# From dictionary
chunk = ChunkResult.model_validate(chunk_dict)
```

### ORM Integration

With `from_attributes = True`, schemas can be created from database models:

```python
# From database model
db_chunk = session.get(RepositoryChunk, chunk_id)
chunk_result = ChunkResult.model_validate(db_chunk)
```

---

## JSON Schema Generation

All schemas can generate JSON Schema for API documentation:

```python
schema = ChunkResult.model_json_schema()
```

Each schema includes:
- Property definitions
- Required fields
- Field descriptions
- Type constraints
- Examples

---

## Integration Points

### With Database Layer

Schemas work seamlessly with `RepositoryChunk` model:

```python
# Create from database model
db_chunk = await session.get(RepositoryChunk, chunk_id)
chunk_result = ChunkResult.model_validate(db_chunk)

# Metadata as JSON
metadata_dict = json.loads(db_chunk.chunk_metadata)
metadata = ChunkMetadata.model_validate(metadata_dict)
```

### With Services (Future)

Schemas ready for service layer:

```python
# Service returns schema
async def get_chunk(chunk_id: UUID) -> ChunkResult:
    db_chunk = await fetch_from_db(chunk_id)
    return ChunkResult.model_validate(db_chunk)
```

### With APIs (Future)

Schemas ready for FastAPI endpoints:

```python
@router.get("/chunks/{chunk_id}", response_model=ChunkResult)
async def get_chunk(chunk_id: UUID) -> ChunkResult:
    return await chunk_service.get_chunk(chunk_id)

@router.post("/chunks", response_model=ChunkResult)
async def create_chunk(chunk: ChunkResult) -> ChunkResult:
    return await chunk_service.create_chunk(chunk)
```

---

## Verification Results

### Test Coverage

All tests passed successfully:

✅ **ChunkContext Tests**
- Minimal creation
- Full creation with all fields
- JSON serialization/deserialization
- Data preservation

✅ **ChunkMetadata Tests**
- Minimal creation
- Function metadata
- Class metadata
- Test metadata
- Line number validation
- JSON serialization

✅ **ChunkResult Tests**
- Full chunk creation
- Chunk type validation (prevents invalid types)
- Hash validation (prevents invalid formats)
- JSON serialization/deserialization
- Dictionary conversion
- All validations working

✅ **ChunkRelationship Tests**
- Minimal creation
- Full creation with metadata
- Multiple relationship types
- Type validation (prevents invalid types)
- Self-reference prevention (prevents same source/target)
- Strength bounds validation
- JSON serialization

✅ **Schema Integration Tests**
- Complete chunk with context and metadata
- Full serialization/deserialization cycle
- Data integrity verification
- Nested schema preservation

✅ **JSON Schema Generation**
- All schemas generate valid JSON Schema
- Properties correctly defined
- Required fields marked
- Examples included

### Verification Command

```bash
cd backend
python verify_chunk_schemas.py
```

**Expected Output:** All 6 test suites pass ✅

---

## Usage Examples

### Creating a Function Chunk

```python
from uuid import uuid4
from app.schemas.chunk import ChunkContext, ChunkMetadata, ChunkResult

# Build context
context = ChunkContext(
    imports=["from typing import List"],
    docstring="Calculate the sum of items.",
)

# Build metadata
metadata = ChunkMetadata(
    symbol_type="function",
    signature="def calculate_sum(items: List[float]) -> float:",
    parameters=["items"],
    return_type="float",
    start_line=10,
    end_line=15,
)

# Build chunk
chunk = ChunkResult(
    repository_id=uuid4(),
    repository_file_id=uuid4(),
    symbol_id=uuid4(),
    chunk_type="function",
    chunk_name="calculate_sum",
    language="python",
    content="def calculate_sum(items: List[float]) -> float:\n    return sum(items)",
    token_count=25,
    content_hash="a" * 64,
    metadata=metadata,
    context=context,
)
```

### Creating a Method Chunk

```python
metadata = ChunkMetadata(
    symbol_type="method",
    signature="def process_data(self, data: dict) -> None:",
    parameters=["self", "data"],
    parent_symbol_id=uuid4(),
    access_modifier="public",
    is_async=False,
)

context = ChunkContext(
    parent_definition="class DataProcessor:",
    imports=["from typing import Dict"],
    decorators=["@validate_input"],
)

chunk = ChunkResult(
    repository_id=repo_id,
    chunk_type="method",
    chunk_name="DataProcessor.process_data",
    language="python",
    content="@validate_input\ndef process_data(self, data: dict) -> None:\n    ...",
    token_count=35,
    content_hash="b" * 64,
    metadata=metadata,
    context=context,
)
```

### Creating Chunk Relationships

```python
from app.schemas.chunk import ChunkRelationship

# Function A calls Function B
relationship = ChunkRelationship(
    source_chunk_id=chunk_a_id,
    target_chunk_id=chunk_b_id,
    relationship_type="calls",
    relationship_strength=0.9,
    metadata={"call_count": 3, "is_direct": True},
)

# Class inherits from base class
inheritance = ChunkRelationship(
    source_chunk_id=derived_class_id,
    target_chunk_id=base_class_id,
    relationship_type="inherits",
    relationship_strength=1.0,
)

# Test tests function
test_rel = ChunkRelationship(
    source_chunk_id=test_chunk_id,
    target_chunk_id=function_chunk_id,
    relationship_type="tests",
    metadata={"test_framework": "pytest"},
)
```

---

## Design Decisions

### Why Pydantic?
- Automatic validation
- JSON serialization built-in
- Type safety with Python type hints
- FastAPI integration
- JSON Schema generation
- ORM compatibility

### Why Nested Schemas?
- Clean separation of concerns
- Reusable components
- Type-specific metadata
- Extensible design

### Why So Many Fields in ChunkMetadata?
- Support for multiple languages
- Flexibility for different chunk types
- All fields optional - use what you need
- Better than multiple metadata schemas

### Why Validate chunk_type and relationship_type?
- Type safety at runtime
- Clear error messages
- Prevent invalid data early
- Self-documenting allowed values

### Why relationship_strength as float?
- Enables weighted relationships
- Useful for ranking related chunks
- Simple 0.0-1.0 scale is intuitive
- Future ML/similarity scoring ready

---

## Files Created/Modified

### Created (2 files):
1. `backend/app/schemas/chunk.py` - All chunk schemas (435 lines)
2. `backend/verify_chunk_schemas.py` - Verification script (464 lines)

### Modified (1 file):
1. `backend/app/schemas/__init__.py` - Added exports

**Total:** 899 lines of code + documentation

---

## Next Steps (NOT Implemented)

The following are **NOT** implemented as per requirements:

### Services (Future)
- ChunkingService
- ChunkStrategyService
- ContextBuilderService
- ChunkMetadataService
- ChunkPersistenceService
- ChunkQueryService
- ChunkValidationService

### APIs (Future)
- POST /repositories/{id}/chunks
- GET /repositories/{id}/chunks
- GET /repositories/{id}/chunks/{chunk_id}
- Chunk relationship endpoints
- Chunk search endpoints

---

## Success Criteria

✅ **Schemas Created**
- ChunkContext with 8 fields
- ChunkMetadata with 26 fields
- ChunkResult with 13 fields
- ChunkRelationship with 7 fields

✅ **Validation Implemented**
- Type validation
- Business logic validation
- Custom validators
- Error messages

✅ **Serialization Support**
- JSON serialization
- Dictionary conversion
- ORM integration
- JSON Schema generation

✅ **Integration Ready**
- Can create from database models
- Ready for service layer
- Ready for API layer
- Full type safety

✅ **Testing Complete**
- All 6 test suites pass
- Validation rules verified
- Integration tested
- Documentation complete

---

## Completion Status

**✅ IMPLEMENTATION COMPLETE**

All shared chunk schemas are fully implemented with:
- ✅ Complete field definitions
- ✅ Comprehensive validation rules
- ✅ Full serialization support
- ✅ JSON Schema generation
- ✅ ORM compatibility
- ✅ Extensive testing
- ✅ Complete documentation

The schemas are production-ready and can be used immediately by services and APIs.

**No services or APIs implemented** as per requirements.

---

**End of Implementation Summary**
