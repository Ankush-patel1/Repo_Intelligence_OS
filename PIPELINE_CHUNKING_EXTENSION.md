# Pipeline Extension: Semantic Chunking

## Overview

The repository analysis pipeline has been extended to include semantic chunking as the final stage.

## Pipeline Flow

### Before
```
Import → Index → Parse → Knowledge Graph
```

### After
```
Import → Index → Parse → Knowledge Graph → Semantic Chunks
```

## Changes Made

### 1. Updated `backend/app/services/orchestration/repository_pipeline.py`

#### Added Services
- `ClassChunker` - Generates class-based semantic chunks
- `FunctionChunker` - Generates function/method-based semantic chunks  
- `ChunkPersister` - Persists chunks to database with deduplication

#### New Methods

**`generate_chunks(repository_id, include_classes=True, include_functions=True, include_methods=True)`**
- Generates semantic chunks from parsed symbols and graph data
- Uses ClassChunker and FunctionChunker
- Persists with automatic deduplication and update logic
- Returns statistics: total_chunks, created, updated, deleted, unchanged, by_type

**`regenerate_chunks(repository_id)`**
- Regenerates chunks without re-running other pipeline stages
- Useful when chunking logic has been updated

#### Updated Methods

**`run_full_pipeline(repository_id, skip_indexing=False, skip_graph=False, skip_chunking=False)`**
- Added `skip_chunking` parameter (default: False)
- Now runs chunking as Step 3 after graph building
- Returns chunking statistics in results dictionary

**`get_pipeline_status(repository_id)`**
- Added `chunks_generated` boolean field
- Added `chunking_stats` dictionary with chunk statistics
- Reports complete pipeline status including chunking

**`run_index_and_graph(repository_id)`**
- Updated to skip chunking by default (legacy compatibility)
- Use `run_full_pipeline` for complete analysis including chunking

**`run_graph_only(repository_id)`**
- Updated to skip chunking (legacy compatibility)

### 2. Updated `backend/app/services/chunking/__init__.py`

Added exports for:
- `ClassChunker`
- `FunctionChunker`
- `ChunkPersister`

### 3. Updated `backend/app/schemas/repository.py`

**RepositoryPipelineResponse schema**
- Added `chunking: dict | None = None` field
- Maintains backward compatibility (field is optional)

### 4. Updated `backend/app/api/v1/repositories.py`

**analyze_repository endpoint**
- Updated docstring to reflect new Step 4: Generate Chunks
- No code changes needed (automatically uses extended pipeline)

## Usage

### Run Complete Pipeline (Including Chunking)
```python
from app.services.orchestration import RepositoryPipeline

pipeline = RepositoryPipeline(session)
results = await pipeline.run_full_pipeline(repository_id)

# Results include:
# {
#     "repository_id": str,
#     "indexing": {...},
#     "graph": {...},
#     "chunking": {
#         "total_chunks": int,
#         "created": int,
#         "updated": int,
#         "deleted": int,
#         "unchanged": int,
#         "by_type": {...}
#     },
#     "pipeline_complete": True
# }
```

### Run Without Chunking (Legacy)
```python
results = await pipeline.run_full_pipeline(
    repository_id,
    skip_chunking=True
)
```

### Regenerate Chunks Only
```python
results = await pipeline.regenerate_chunks(repository_id)
```

### Check Pipeline Status
```python
status = await pipeline.get_pipeline_status(repository_id)

# Status includes:
# {
#     "repository_id": str,
#     "indexed": bool,
#     "graph_built": bool,
#     "chunks_generated": bool,  # NEW
#     "indexing_stats": {...},
#     "graph_stats": {...},
#     "chunking_stats": {...}  # NEW
# }
```

## API Integration

The existing repository analysis endpoint will now include chunking:

**POST `/repositories/{id}/analyze`**
- Automatically runs full pipeline including chunking
- No breaking changes to API contract
- Response now includes chunking statistics

The chunking step is also available independently via:

**POST `/repositories/{id}/chunk`**
- Runs only chunking (assumes repository already analyzed)
- See `backend/app/api/v1/chunks.py` for details

## Backward Compatibility

✅ **No breaking changes**
- Existing methods work as before
- `skip_chunking=False` is opt-in for full pipeline
- Legacy methods (`run_index_and_graph`) skip chunking by default
- API responses are extended, not changed

## Testing

All tests passing:
- ✅ Pipeline initialization with chunking services
- ✅ Skip flags work correctly
- ✅ Pipeline status includes chunking information
- ✅ All method signatures correct
- ✅ Docstrings updated

Test files:
- `backend/test_pipeline_syntax.py` - Structure and syntax validation
- `backend/test_pipeline_chunking.py` - Integration tests (requires DB)

## Files Modified

1. `backend/app/services/orchestration/repository_pipeline.py` - Extended with chunking
2. `backend/app/services/chunking/__init__.py` - Added exports
3. `backend/app/schemas/repository.py` - Added chunking field to response
4. `backend/app/api/v1/repositories.py` - Updated analyze endpoint docstring

## Files Created

1. `backend/test_pipeline_syntax.py` - Validation tests
2. `backend/test_pipeline_chunking.py` - Integration tests  
3. `PIPELINE_CHUNKING_EXTENSION.md` - This document

## Next Steps

The pipeline is ready for use. No further changes needed. The existing `/repositories/{id}/analyze` endpoint will now automatically generate semantic chunks as part of the complete repository analysis workflow.
