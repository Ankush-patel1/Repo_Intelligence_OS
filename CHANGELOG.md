# Changelog

## v0.3.0 - 2026-07-03

### Added - Tree-sitter Code Parsing System

#### Parser Infrastructure
- ParserInterface base class for consistent parser architecture
- ParserFactory for language-based parser selection
- ParserManager for high-level parsing operations
- GenericParser for graceful handling of unsupported languages

#### Language Parsers (8 Total)
- **Python**: PythonTreeSitterParser (imports, classes, functions, methods, decorators, parameters)
- **JavaScript**: JavaScriptTreeSitterParser (imports, exports, functions, classes, arrow functions)
- **TypeScript**: TypeScriptTreeSitterParser (interfaces, type aliases, enums, all JS features)
- **Java**: JavaTreeSitterParser (packages, imports, classes, interfaces, enums, methods, annotations)
- **C**: CTreeSitterParser (includes, macros, functions, structs, enums, typedefs, globals)
- **C++**: CppTreeSitterParser (namespaces, classes, templates, using, destructors)
- **Go**: GoTreeSitterParser (packages, structs, interfaces, functions, methods with receivers)
- **Rust**: RustTreeSitterParser (modules, structs, enums, traits, impl blocks)

#### Database
- RepositorySymbol model for storing parsed symbol metadata
- Symbol relationships (parent-child hierarchies)
- Location tracking (line and column numbers)
- Signature and metadata storage
- Optimized indexes for symbol queries

#### Features
- 22 file extensions supported (.py, .js, .ts, .java, .c, .cpp, .go, .rs, etc.)
- Automatic symbol extraction during repository indexing
- AST-based parsing using tree-sitter libraries
- Symbol type classification (function, class, method, import, etc.)
- Cross-language parser consistency
- Graceful error handling for syntax errors

#### Testing
- 41 Java parser tests
- 9 C parser tests  
- 11 C++ parser tests
- 7 Go parser tests
- 7 Rust parser tests
- 128/130 tests passing (98.5%)

#### Dependencies
- tree-sitter>=0.23.0
- tree-sitter-python>=0.23.0
- tree-sitter-javascript>=0.23.0
- tree-sitter-typescript>=0.23.0
- tree-sitter-java>=0.23.0
- tree-sitter-c>=0.23.0
- tree-sitter-cpp>=0.23.0
- tree-sitter-go>=0.23.0
- tree-sitter-rust>=0.23.0

---

## v0.2.0

### Added

- GitHub Repository Import
- Repository Synchronization
- Repository Indexing
- Automatic Indexing
- File Metadata Storage
- Repository Statistics
- File Listing APIs

---

## v0.1.0

### Added

- Docker Infrastructure
- FastAPI
- React
- PostgreSQL
- Redis
- Celery

