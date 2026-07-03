# Symbol Extraction Integration

## Overview

Symbol extraction has been integrated into the Repository Indexing pipeline. After a repository is indexed and files are scanned, the system now automatically parses supported files and extracts symbols (functions, classes, methods, imports, etc.) into the database.

## Integration Flow

```
Repository Import → File Scanning → File Indexing → Symbol Extraction → Database Storage
```

### Detailed Flow

1. **File Scanning**: `FileScanner` scans the repository and identifies all files
2. **File Indexing**: `RepositoryIndexer` creates `RepositoryFile` records in the database
3. **Symbol Extraction**: For each indexed file:
   - Check if language is supported (Python, JavaScript, TypeScript)
   - Skip binary files
   - Parse the file using tree-sitter
   - Extract symbols (functions, classes, methods, imports, exports, types)
   - Convert symbols to `RepositorySymbol` records
   - Store in database with parent-child relationships

## Supported Languages

- **Python** (.py)
  - Functions (regular and async)
  - Classes and methods
  - Imports
  - Decorators

- **JavaScript** (.js, .jsx, .mjs, .cjs)
  - Functions (regular, async, arrow)
  - Classes and methods
  - Imports and exports
  - ES6+ syntax

- **TypeScript** (.ts, .tsx)
  - All JavaScript features
  - Interfaces
  - Type aliases
  - Enums

## Files Created

### `backend/app/services/indexing/symbol_extractor.py`

Core service that:
- Takes a `RepositoryFile` and parses it
- Converts parsed symbols into `RepositorySymbol` models
- Handles parent-child relationships (e.g., class → methods)
- Supports all three language parsers
- Stores symbols in the database

Key methods:
- `extract_and_store_symbols()`: Main entry point
- `_convert_symbols_to_models()`: Converts parser output to DB models
- `_create_class_symbols()`: Creates class and method records with relationships
- `_create_function_symbol()`: Creates function/method records
- `_create_import_symbol()`: Creates import records
- `_create_export_symbol()`: Creates export records
- `_create_type_symbol()`: Creates TypeScript type records

## Files Modified

### `backend/app/services/indexing/repository_indexer.py`

Changes:
- Added `symbol_extractor` parameter to constructor
- Integrated `_extract_symbols_from_files()` into the indexing pipeline
- Returns symbol extraction statistics in the indexing result

New statistics returned:
```python
{
    "total_files": 150,
    "files_per_language": {"Python": 80, "JavaScript": 70},
    "total_bytes": 1500000,
    "largest_files": [...],
    "binary_file_count": 5,
    "symbols": {  # NEW
        "total_symbols": 450,
        "files_parsed": 140,
        "files_skipped": 5,
        "parse_errors": 0,
        "symbols_by_language": {
            "Python": 250,
            "JavaScript": 200
        }
    }
}
```

### `backend/app/services/indexing/__init__.py`

Changes:
- Exported `SymbolExtractor` for external use

## Database Schema

Symbols are stored in the `repository_symbols` table with:
- Reference to parent file (`repository_file_id`)
- Symbol identification (name, type)
- Parent-child relationships (`parent_symbol` for methods)
- Location information (line numbers)
- Metadata (decorators, parameters, etc. as JSON)

## Usage Example

```python
from app.services.indexing import RepositoryIndexer

# Indexer automatically extracts symbols
indexer = RepositoryIndexer(session)
stats = await indexer.index_repository(repository)

# Check symbol extraction results
print(f"Total symbols extracted: {stats['symbols']['total_symbols']}")
print(f"Files parsed: {stats['symbols']['files_parsed']}")
print(f"By language: {stats['symbols']['symbols_by_language']}")
```

## Behavior

### Supported Files
- Files in supported languages (Python, JavaScript, TypeScript)
- Non-binary files only
- Files that exist on disk

### Skipped Files
- Unsupported languages (Java, Go, Rust - placeholders exist)
- Binary files
- Files with syntax errors (logged as parse errors)

### Error Handling
- Parse errors are tracked but don't stop the indexing process
- Missing files are handled gracefully
- Unsupported languages are silently skipped

## Performance Considerations

- Symbol extraction happens synchronously during indexing
- Each file is parsed once immediately after being indexed
- Database writes are batched using `flush()` rather than `commit()`
- Parent-child relationships are resolved in memory before writing

## Future Enhancements

1. Add support for remaining languages (Java, Go, Rust)
2. Implement incremental symbol updates (only re-parse changed files)
3. Add symbol search and query APIs
4. Extract additional metadata (return types, visibility modifiers)
5. Add symbol cross-references (find all usages)
