"""Symbol extraction service for repository files.

This module extracts symbols from parsed source code and stores them
as RepositorySymbol records in the database.
"""

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.repository_file import RepositoryFile
from app.db.models.repository_symbol import RepositorySymbol
from app.services.parser.parser_manager import ParserManager


class SymbolExtractor:
    """Extracts and stores symbols from repository files.

    This service integrates the parsing system with the database layer,
    converting parsed symbols into RepositorySymbol records.
    """

    def __init__(self, session: AsyncSession, parser_manager: ParserManager | None = None) -> None:
        """Initialize the symbol extractor.

        Args:
            session: Database session for storing symbols
            parser_manager: Parser manager instance (creates default if None)
        """
        self.session = session
        self.parser_manager = parser_manager or ParserManager()

    async def extract_and_store_symbols(self, repository_file: RepositoryFile) -> dict[str, Any]:
        """Extract symbols from a file and store them in the database.

        Args:
            repository_file: RepositoryFile model instance to parse

        Returns:
            Dictionary with extraction statistics
        """
        # Check if the file can be parsed
        if not self.parser_manager.can_parse(repository_file.absolute_path):
            return {
                "success": False,
                "reason": "unsupported_language",
                "language": repository_file.language,
                "symbols_extracted": 0,
            }

        # Skip binary files
        if repository_file.is_binary:
            return {
                "success": False,
                "reason": "binary_file",
                "language": repository_file.language,
                "symbols_extracted": 0,
            }

        # Parse the file
        file_path = Path(repository_file.absolute_path)
        if not file_path.exists():
            return {
                "success": False,
                "reason": "file_not_found",
                "language": repository_file.language,
                "symbols_extracted": 0,
            }

        parse_result = self.parser_manager.parse_file(file_path)

        if not parse_result.success:
            return {
                "success": False,
                "reason": "parse_error",
                "error_message": parse_result.error_message,
                "language": repository_file.language,
                "symbols_extracted": 0,
            }

        # Extract symbols and convert to models
        if not parse_result.symbols:
            return {
                "success": True,
                "reason": "no_symbols",
                "language": repository_file.language,
                "symbols_extracted": 0,
            }

        # Convert symbols to database models
        symbol_models = self._convert_symbols_to_models(
            parse_result.symbols,
            repository_file.id,
            repository_file.language,
        )

        # Store symbols in database
        self.session.add_all(symbol_models)
        await self.session.flush()

        return {
            "success": True,
            "language": repository_file.language,
            "symbols_extracted": len(symbol_models),
        }

    def _convert_symbols_to_models(
        self,
        symbols: list[dict[str, Any]],
        repository_file_id: uuid.UUID,
        language: str,
    ) -> list[RepositorySymbol]:
        """Convert parsed symbols to RepositorySymbol models.

        Args:
            symbols: List of symbol dictionaries from parser
            repository_file_id: ID of the RepositoryFile
            language: Programming language of the file

        Returns:
            List of RepositorySymbol model instances
        """
        models: list[RepositorySymbol] = []
        symbol_id_map: dict[str, uuid.UUID] = {}  # Map symbol keys to their IDs

        for symbol in symbols:
            symbol_type = symbol.get("type", "unknown")

            if symbol_type == "import":
                # Handle imports
                models.append(
                    self._create_import_symbol(
                        symbol, repository_file_id, language
                    )
                )
            elif symbol_type == "export":
                # Handle exports
                models.append(
                    self._create_export_symbol(
                        symbol, repository_file_id, language
                    )
                )
            elif symbol_type == "class":
                # Handle classes and their methods
                class_models = self._create_class_symbols(
                    symbol, repository_file_id, language, symbol_id_map
                )
                models.extend(class_models)
            elif symbol_type == "function":
                # Handle top-level functions
                models.append(
                    self._create_function_symbol(
                        symbol, repository_file_id, language, None
                    )
                )
            elif symbol_type in ("interface", "type", "enum"):
                # Handle TypeScript-specific types
                models.append(
                    self._create_type_symbol(
                        symbol, repository_file_id, language
                    )
                )

        return models

    def _create_import_symbol(
        self,
        symbol: dict[str, Any],
        repository_file_id: uuid.UUID,
        language: str,
    ) -> RepositorySymbol:
        """Create a RepositorySymbol for an import statement.

        Args:
            symbol: Import symbol dictionary
            repository_file_id: ID of the RepositoryFile
            language: Programming language

        Returns:
            RepositorySymbol model instance
        """
        import_name = symbol.get("name", "")
        import_kind = symbol.get("kind", "import")

        return RepositorySymbol(
            repository_file_id=repository_file_id,
            symbol_name=import_name,
            symbol_type=import_kind,
            parent_symbol=None,
            start_line=symbol.get("line", 1),
            end_line=symbol.get("end_line", symbol.get("line", 1)),
            start_column=None,
            end_column=None,
            language=language,
            signature=import_name,
            symbol_metadata=None,
            created_at=datetime.utcnow(),
        )

    def _create_export_symbol(
        self,
        symbol: dict[str, Any],
        repository_file_id: uuid.UUID,
        language: str,
    ) -> RepositorySymbol:
        """Create a RepositorySymbol for an export statement.

        Args:
            symbol: Export symbol dictionary
            repository_file_id: ID of the RepositoryFile
            language: Programming language

        Returns:
            RepositorySymbol model instance
        """
        export_name = symbol.get("name", "")
        export_kind = symbol.get("kind", "export")

        return RepositorySymbol(
            repository_file_id=repository_file_id,
            symbol_name=export_name,
            symbol_type=export_kind,
            parent_symbol=None,
            start_line=symbol.get("line", 1),
            end_line=symbol.get("end_line", symbol.get("line", 1)),
            start_column=None,
            end_column=None,
            language=language,
            signature=export_name,
            symbol_metadata=None,
            created_at=datetime.utcnow(),
        )

    def _create_type_symbol(
        self,
        symbol: dict[str, Any],
        repository_file_id: uuid.UUID,
        language: str,
    ) -> RepositorySymbol:
        """Create a RepositorySymbol for TypeScript types (interface, type, enum).

        Args:
            symbol: Type symbol dictionary
            repository_file_id: ID of the RepositoryFile
            language: Programming language

        Returns:
            RepositorySymbol model instance
        """
        type_name = symbol.get("name", "Unknown")
        type_kind = symbol.get("type", "type")  # interface, type, or enum
        signature = symbol.get("signature", "")

        # Build metadata
        metadata = {}
        if "members" in symbol:
            metadata["member_count"] = len(symbol["members"])

        return RepositorySymbol(
            repository_file_id=repository_file_id,
            symbol_name=type_name,
            symbol_type=type_kind,
            parent_symbol=None,
            start_line=symbol.get("line", 1),
            end_line=symbol.get("end_line", symbol.get("line", 1)),
            start_column=None,
            end_column=None,
            language=language,
            signature=signature or f"{type_kind} {type_name}",
            symbol_metadata=json.dumps(metadata) if metadata else None,
            created_at=datetime.utcnow(),
        )

    def _create_class_symbols(
        self,
        symbol: dict[str, Any],
        repository_file_id: uuid.UUID,
        language: str,
        symbol_id_map: dict[str, uuid.UUID],
    ) -> list[RepositorySymbol]:
        """Create RepositorySymbol models for a class and its methods.

        Args:
            symbol: Class symbol dictionary
            repository_file_id: ID of the RepositoryFile
            language: Programming language
            symbol_id_map: Map of symbol keys to their database IDs

        Returns:
            List of RepositorySymbol model instances (class + methods)
        """
        models: list[RepositorySymbol] = []
        class_name = symbol.get("name", "Unknown")
        decorators = symbol.get("decorators", [])

        # Create metadata for class
        metadata = {}
        if decorators:
            metadata["decorators"] = decorators

        # Create the class symbol
        class_id = uuid.uuid4()
        class_symbol = RepositorySymbol(
            id=class_id,
            repository_file_id=repository_file_id,
            symbol_name=class_name,
            symbol_type="class",
            parent_symbol=None,
            start_line=symbol.get("line", 1),
            end_line=symbol.get("end_line", symbol.get("line", 1)),
            start_column=None,
            end_column=None,
            language=language,
            signature=f"class {class_name}",
            symbol_metadata=json.dumps(metadata) if metadata else None,
            created_at=datetime.utcnow(),
        )
        models.append(class_symbol)

        # Store class ID for methods to reference
        symbol_key = f"{class_name}:{symbol.get('line')}"
        symbol_id_map[symbol_key] = class_id

        # Create method symbols (children of the class)
        methods = symbol.get("methods", [])
        for method in methods:
            method_symbol = self._create_function_symbol(
                method, repository_file_id, language, class_id
            )
            models.append(method_symbol)

        return models

    def _create_function_symbol(
        self,
        symbol: dict[str, Any],
        repository_file_id: uuid.UUID,
        language: str,
        parent_symbol_id: uuid.UUID | None,
    ) -> RepositorySymbol:
        """Create a RepositorySymbol for a function or method.

        Args:
            symbol: Function symbol dictionary
            repository_file_id: ID of the RepositoryFile
            language: Programming language
            parent_symbol_id: ID of parent symbol (class) if this is a method

        Returns:
            RepositorySymbol model instance
        """
        func_name = symbol.get("name", "Unknown")
        parameters = symbol.get("parameters", [])
        is_async = symbol.get("is_async", False)
        is_method = symbol.get("is_method", False)
        decorators = symbol.get("decorators", [])

        # Build function signature
        params_str = ", ".join(parameters)
        async_prefix = "async " if is_async else ""
        signature = f"{async_prefix}def {func_name}({params_str})"

        # Build metadata
        metadata = {}
        if decorators:
            metadata["decorators"] = decorators
        if is_async:
            metadata["is_async"] = True
        if parameters:
            metadata["parameters"] = parameters

        # Determine symbol type
        symbol_type = "method" if is_method else "function"

        return RepositorySymbol(
            repository_file_id=repository_file_id,
            symbol_name=func_name,
            symbol_type=symbol_type,
            parent_symbol=parent_symbol_id,
            start_line=symbol.get("line", 1),
            end_line=symbol.get("end_line", symbol.get("line", 1)),
            start_column=None,
            end_column=None,
            language=language,
            signature=signature,
            symbol_metadata=json.dumps(metadata) if metadata else None,
            created_at=datetime.utcnow(),
        )
