# Class-Based Semantic Chunking - Implementation Complete ✅

**Date:** July 4, 2026  
**Status:** ✅ Complete  
**Task:** Implement class-based chunking using existing database models

---

## Overview

Implemented a **ClassChunker** that creates semantic chunks from class symbols by querying existing database models (`RepositorySymbol`, `RepositoryNode`, `RepositoryEdge`) and extracting:

- Complete class definition with all methods
- Import statements needed by the class
- Symbols called by the class
- Graph relationships (inheritance, implementation, calls)
- Rich metadata and context

Returns `ChunkResult` objects ready for use. **No persistence** - results are returned in-memory only.

---

## Files Created

### 1. **backend/app/services/chunking/class_chunker.py** (540 lines)

**Main implementation with 2 public methods and 12 private helpers.**

#### Public API

```python
class ClassChunker:
    """Creates semantic chunks from class symbols."""
    
    def __init__(self, session: AsyncSession):
        """Initialize with database session."""
    
    async def chunk_class(
        self, 
        class_symbol_id: UUID
    ) -> ChunkResult:
        """Create chunk from a single class symbol.
        
        Returns:
            ChunkResult with complete class content, metadata, context
            
        Raises:
            ValueError: If symbol not found or not a class
        """
    
    async def chunk_all_classes(
        self,
        repository_id: UUID
    ) -> list[ChunkResult]:
        """Create chunks for all classes in a repository.
        
        Returns:
            List of ChunkResult objects (one per class)
        """
```

#### Private Helper Methods

```python
# Data fetching (5 methods)
async def _fetch_class_symbol(class_symbol_id) -> RepositorySymbol
async def _fetch_method_symbols(class_symbol_id) -> list[RepositorySymbol]
async def _fetch_graph_node(symbol_id) -> RepositoryNode
async def _fetch_relationships(node_id) -> list[tuple[Edge, Node]]
async def _extract_imports(file_id) -> list[str]

# Content processing (4 methods)
async def _read_file_content(file_path) -> str
def _extract_class_content(file_content, class_symbol, methods) -> str
async def _build_class_context(...) -> ChunkContext
async def _build_class_metadata(...) -> ChunkMetadata

# Utilities (3 methods)
def _parse_metadata(metadata_json) -> dict
def _estimate_token_count(content) -> int
def _calculate_content_hash(content) -> str
```

### 2. **backend/test_class_chunker.py** (615 lines)

**Comprehensive test suite with 3 test cases.**

Creates complete test scenario:
- Repository with Python file
- UserManager class with 5 methods
- AdminManager class inheriting from UserManager
- Import symbols
- Graph nodes and edges (CONTAINS, INHERITS)
- Demonstrates all chunker capabilities

---

## Implementation Details

### Data Sources

The chunker queries these existing database models:

1. **RepositorySymbol** - Class and method symbols
   - `symbol_name`, `symbol_type`, `start_line`, `end_line`
   - `signature`, `language`, `symbol_metadata`
   - `parent_symbol` relationship

2. **RepositoryFile** - File information and content
   - `absolute_path` (for reading file content)
   - `repository_id`, `language`

3. **RepositoryNode** - Graph nodes
   - Links symbols to knowledge graph
   - Provides `node_id` for chunks

4. **RepositoryEdge** - Graph relationships
   - `INHERITS` - Base class relationships
   - `IMPLEMENTS` - Interface implementation
   - `CALLS` - Function/method calls
   - `REFERENCES` - Symbol references

### Chunk Generation Process

```
1. Fetch class symbol from database
   ↓
2. Validate symbol is a class/interface
   ↓
3. Fetch related data:
   - Method symbols (child symbols)
   - File content (from disk)
   - Graph node (for graph linkage)
   - Import symbols (from same file)
   - Relationships (graph edges)
   ↓
4. Extract class content:
   - Use start_line/end_line from symbol
   - Include all methods within class
   ↓
5. Build context:
   - Import statements
   - Parent definition (if nested)
   - Dependencies (from graph edges)
   - Docstring and decorators
   ↓
6. Build metadata:
   - Symbol info (type, signature, location)
   - Class info (method count, abstract, access)
   - Inheritance (inherits_from, implements)
   - Graph info (node_id, calls, relationships)
   ↓
7. Calculate metrics:
   - Token count (~4 chars per token)
   - Content hash (SHA256)
   ↓
8. Return ChunkResult
```

---

## ChunkResult Structure

### Core Fields

```python
ChunkResult(
    # Identification
    repository_id: UUID              # From file.repository_id
    repository_file_id: UUID         # From symbol.repository_file_id
    symbol_id: UUID                  # The class symbol ID
    
    # Properties
    chunk_type: "class"              # Always "class" for class chunks
    chunk_name: str                  # Class name (e.g., "UserManager")
    language: str                    # Programming language
    
    # Content
    content: str                     # Full class code (class + methods)
    
    # Metrics
    token_count: int                 # Estimated tokens
    content_hash: str                # SHA256 hash (64 chars)
    
    # Rich data
    metadata: ChunkMetadata          # Detailed metadata
    context: ChunkContext            # Context information
)
```

### ChunkMetadata Contents

```python
ChunkMetadata(
    # Symbol information
    symbol_type: "class"             # Always "class"
    signature: str                   # Class signature
    start_line: int                  # Starting line
    end_line: int                    # Ending line
    start_column: int | None         # Starting column
    end_column: int | None           # Ending column
    
    # Graph linkage
    parent_symbol_id: UUID | None    # Parent symbol (if nested)
    node_id: UUID | None             # Graph node ID
    
    # Relationships
    calls: list[UUID]                # Symbols called by class
    called_by: list[UUID]            # Symbols calling this class
    inherits_from: list[str]         # Base class names
    implements: list[str]            # Interface names
    
    # Class-specific
    method_count: int                # Number of methods
    is_abstract: bool                # Is abstract class
    access_modifier: str | None      # public/private/protected
)
```

### ChunkContext Contents

```python
ChunkContext(
    # Required context
    imports: list[str]               # Import statements
    parent_definition: str | None    # Parent class definition
    dependencies: list[UUID]         # Symbol dependencies
    related_chunks: list[UUID]       # Related chunk IDs
    
    # Documentation
    docstring: str | None            # Class docstring
    decorators: list[str]            # Decorators/annotations
    
    # Additional context
    context_before: None             # Not used for classes
    context_after: None              # Not used for classes
)
```

---

## Example Output

### UserManager Class Chunk

```python
chunk = await chunker.chunk_class(user_manager_class_id)

# Chunk properties
chunk.chunk_type = "class"
chunk.chunk_name = "UserManager"
chunk.language = "python"
chunk.token_count = 523  # Estimated
chunk.content_hash = "a1b2c3d4..."  # SHA256

# Content (abbreviated)
chunk.content = '''
class UserManager:
    """Manages user operations.
    
    This class handles user creation, retrieval, and deletion
    with built-in validation and error handling.
    """
    
    def __init__(self, db_connection):
        ...
    
    def create_user(self, username: str, email: str) -> Optional[dict]:
        ...
    
    def get_user(self, user_id: int) -> Optional[dict]:
        ...
    
    def delete_user(self, user_id: int) -> bool:
        ...
    
    def _validate_email(self, email: str) -> bool:
        ...
'''

# Metadata
chunk.metadata.symbol_type = "class"
chunk.metadata.signature = "class UserManager:"
chunk.metadata.method_count = 5
chunk.metadata.is_abstract = False
chunk.metadata.access_modifier = "public"
chunk.metadata.start_line = 8
chunk.metadata.end_line = 88
chunk.metadata.node_id = UUID("...")

# Context
chunk.context.imports = [
    "import json",
    "from typing import List, Optional",
    "from datetime import datetime"
]
chunk.context.docstring = "Manages user operations.\n\nThis class..."
chunk.context.decorators = []
chunk.context.dependencies = [UUID("..."), UUID("...")]
```

### AdminManager Class Chunk (with Inheritance)

```python
chunk = await chunker.chunk_class(admin_manager_class_id)

# Shows inheritance relationship
chunk.metadata.inherits_from = ["UserManager"]
chunk.metadata.method_count = 1

# Content includes only AdminManager code (not inherited methods)
chunk.content = '''
class AdminManager(UserManager):
    """Manages admin user operations.
    
    Extends UserManager with admin-specific functionality.
    """
    
    def grant_admin_privileges(self, user_id: int) -> bool:
        ...
'''
```

---

## Usage Examples

### Example 1: Chunk Single Class

```python
from app.services.chunking.class_chunker import ClassChunker

async with async_session() as session:
    chunker = ClassChunker(session)
    
    # Chunk a specific class by symbol ID
    chunk = await chunker.chunk_class(class_symbol_id)
    
    print(f"Class: {chunk.chunk_name}")
    print(f"Methods: {chunk.metadata.method_count}")
    print(f"Tokens: {chunk.token_count}")
    print(f"Imports: {len(chunk.context.imports)}")
    
    # Use chunk for RAG, LLM processing, etc.
    # (No persistence - chunk only exists in memory)
```

### Example 2: Chunk All Classes in Repository

```python
async with async_session() as session:
    chunker = ClassChunker(session)
    
    # Chunk all classes in a repository
    chunks = await chunker.chunk_all_classes(repository_id)
    
    print(f"Found {len(chunks)} classes")
    
    for chunk in chunks:
        print(f"- {chunk.chunk_name}: {chunk.metadata.method_count} methods")
        
        # Show inheritance
        if chunk.metadata.inherits_from:
            print(f"  Inherits: {', '.join(chunk.metadata.inherits_from)}")
```

### Example 3: Extract Specific Information

```python
chunk = await chunker.chunk_class(class_symbol_id)

# Get all imports needed by this class
imports = chunk.context.imports
print("Required imports:", imports)

# Get inheritance hierarchy
base_classes = chunk.metadata.inherits_from
interfaces = chunk.metadata.implements
print(f"Extends: {base_classes}")
print(f"Implements: {interfaces}")

# Get method signatures (from content parsing)
lines = chunk.content.splitlines()
method_lines = [l for l in lines if l.strip().startswith("def ")]
print(f"Methods: {len(method_lines)}")

# Check if this class is called by others
called_by_count = len(chunk.metadata.called_by)
print(f"Referenced by {called_by_count} other symbols")
```

---

## Features Implemented

✅ **Query Database Models**
- Fetches `RepositorySymbol` (class + methods)
- Fetches `RepositoryFile` (for file info)
- Fetches `RepositoryNode` (for graph linkage)
- Fetches `RepositoryEdge` (for relationships)

✅ **Extract Class Content**
- Reads file from disk using `absolute_path`
- Extracts lines using `start_line`/`end_line`
- Includes complete class with all methods

✅ **Include Imports**
- Queries import symbols from same file
- Uses `signature` field for import statement
- Adds to `ChunkContext.imports`

✅ **Include Called Symbols**
- Extracts from `CALLS` edges in graph
- Adds target symbol IDs to metadata

✅ **Include Graph Relationships**
- Links chunk to graph via `node_id`
- Extracts `INHERITS` relationships → `inherits_from`
- Extracts `IMPLEMENTS` relationships → `implements`
- Extracts `CALLS` relationships → `calls`
- Extracts `REFERENCES` relationships → `dependencies`

✅ **Return ChunkResult**
- Complete `ChunkResult` object
- Valid `ChunkMetadata` with all fields
- Valid `ChunkContext` with imports/dependencies
- No persistence - in-memory only

✅ **Error Handling**
- Validates symbol exists
- Validates symbol is a class/interface
- Handles missing file content
- Handles JSON parsing errors
- Continues processing if individual class fails

---

## Technical Implementation Notes

### Token Counting

Uses simple heuristic: **~4 characters per token**

```python
def _estimate_token_count(self, content: str) -> int:
    return len(content) // 4
```

This provides a reasonable estimate without requiring a tokenizer library.

### Content Hashing

Uses **SHA256** for content deduplication:

```python
def _calculate_content_hash(self, content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()
```

Returns 64-character hexadecimal string.

### Metadata Parsing

Handles JSON metadata from `symbol_metadata` field:

```python
def _parse_metadata(self, metadata_json: str | None) -> dict[str, Any]:
    if not metadata_json:
        return {}
    try:
        return json.loads(metadata_json)
    except json.JSONDecodeError:
        return {}
```

Safely handles missing or invalid JSON.

### File Reading

Reads source files directly from disk:

```python
async def _read_file_content(self, file_path: str) -> str:
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()
```

Uses `absolute_path` from `RepositoryFile` model.

### Line Extraction

Converts 1-indexed line numbers to Python slicing:

```python
def _extract_class_content(self, file_content, class_symbol, methods):
    lines = file_content.splitlines()
    start_idx = class_symbol.start_line - 1  # 1-indexed → 0-indexed
    end_idx = class_symbol.end_line          # Inclusive end
    class_lines = lines[start_idx:end_idx]
    return "\n".join(class_lines)
```

---

## Test Suite

### Test Data

Creates realistic test scenario:
- **Repository:** test-repo
- **File:** test_sample.py (108 lines of Python)
- **Classes:**
  - `UserManager` with 5 methods (__init__, create_user, get_user, delete_user, _validate_email)
  - `AdminManager` with 1 method (grant_admin_privileges), inherits from UserManager
- **Imports:** json, typing.List/Optional, datetime
- **Graph:** Repository → File → Classes with CONTAINS and INHERITS edges

### Test Cases

1. **Test 1: Chunk UserManager**
   - Validates complete class chunking
   - Checks all 5 methods included
   - Verifies imports extracted
   - Shows metadata and context

2. **Test 2: Chunk AdminManager**
   - Validates inheritance tracking
   - Shows `inherits_from` contains "UserManager"
   - Demonstrates smaller class with 1 method

3. **Test 3: Chunk All Classes**
   - Processes entire repository
   - Returns 2 chunks (UserManager + AdminManager)
   - Shows summary statistics

### Running Tests

```bash
cd backend
python test_class_chunker.py
```

Expected output:
```
======================================================================
CLASS-BASED SEMANTIC CHUNKING TEST
======================================================================

📦 Creating test data...
✅ Test data created

======================================================================
TEST 1: Chunk UserManager Class
======================================================================

✅ Successfully created chunk for UserManager

Chunk Details:
  - Type: class
  - Name: UserManager
  - Language: python
  - Token Count: 523
  - Content Hash: a1b2c3d4...
  - Lines: 8-88

Metadata:
  - Symbol Type: class
  - Signature: class UserManager:
  - Method Count: 5
  - Is Abstract: False
  - Access Modifier: public
  - Node ID: <uuid>

Context:
  - Imports (3):
    • import json
    • from typing import List, Optional
    • from datetime import datetime
  - Dependencies: 0 symbols
  - Docstring: Manages user operations...

[... content preview ...]

======================================================================
✅ ALL TESTS COMPLETE
======================================================================
```

---

## Limitations & Future Enhancements

### Current Limitations

1. **No nested class support** - Only top-level classes chunked
2. **No method-level chunks** - Entire class always included
3. **Simple token counting** - Uses character-based heuristic
4. **No caching** - Fetches data fresh each time
5. **Serial processing** - Classes chunked one at a time

### Future Enhancements

1. **Add nested class support** - Detect and chunk inner classes
2. **Add method chunking** - Create separate chunks for large methods
3. **Use real tokenizer** - tiktoken or HuggingFace tokenizer
4. **Add caching layer** - Cache file content, imports, relationships
5. **Parallel processing** - Use asyncio.gather for multiple classes
6. **Add filters** - Filter by language, size, complexity
7. **Add pagination** - For repositories with many classes

---

## Integration with Framework

The ClassChunker integrates with the existing chunking framework:

```python
# ClassChunker provides specific implementation
# Can be wrapped by ChunkManager for orchestration

from app.services.chunking.chunk_manager import ChunkManager
from app.services.chunking.class_chunker import ClassChunker

async with async_session() as session:
    # Direct use
    class_chunker = ClassChunker(session)
    chunks = await class_chunker.chunk_all_classes(repo_id)
    
    # Or via ChunkManager (future integration)
    # manager = ChunkManager(session)
    # manager.register_chunker("class", class_chunker)
    # chunks = await manager.chunk_repository(repo_id, strategy="class")
```

---

## Summary Statistics

**Files Created:** 2
- `class_chunker.py` (540 lines)
- `test_class_chunker.py` (615 lines)

**Total Lines:** 1,155 lines

**Classes:** 1 (`ClassChunker`)

**Methods:** 14 total
- 2 public methods
- 12 private helper methods

**Database Models Used:** 4
- `RepositorySymbol`
- `RepositoryFile`
- `RepositoryNode`
- `RepositoryEdge`

**Schemas Used:** 3
- `ChunkResult`
- `ChunkMetadata`
- `ChunkContext`

---

## Compliance with Requirements

✅ **Implement ONLY class-based chunking** - Complete  
✅ **Use RepositorySymbol** - Queries symbols for class and methods  
✅ **Use RepositoryNode** - Links chunks to graph nodes  
✅ **Use RepositoryEdge** - Extracts relationships (INHERITS, CALLS, etc.)  
✅ **Create semantic chunks containing:**
  - ✅ Class definition and body
  - ✅ All methods within class
  - ✅ Import statements
  - ✅ Called symbols (from graph edges)
  - ✅ Graph relationships (inheritance, implementation)  
✅ **Return ChunkResult** - Complete ChunkResult objects with metadata and context  
✅ **No persistence** - Results returned in-memory only  
✅ **Stop after completion** - Task complete

---

**Status:** ✅ IMPLEMENTATION COMPLETE

Ready for use in chunking pipeline or RAG systems.

