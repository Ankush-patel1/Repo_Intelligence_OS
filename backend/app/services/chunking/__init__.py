"""Chunking services package.

This package provides the framework for intelligent semantic chunking of
repository code. It converts parsed symbols into optimally-sized chunks
suitable for RAG/LLM processing.
"""

from app.services.chunking.chunk_builder import ChunkBuilder
from app.services.chunking.chunk_interface import ChunkInterface, ChunkStrategy
from app.services.chunking.chunk_manager import ChunkManager
from app.services.chunking.chunk_persister import ChunkPersister
from app.services.chunking.chunk_strategy import (
    FileLevelStrategy,
    LogicalUnitStrategy,
    ModuleLevelStrategy,
    SymbolLevelStrategy,
)
from app.services.chunking.class_chunker import ClassChunker
from app.services.chunking.function_chunker import FunctionChunker

__all__ = [
    "ChunkBuilder",
    "ChunkInterface",
    "ChunkStrategy",
    "ChunkManager",
    "ChunkPersister",
    "SymbolLevelStrategy",
    "LogicalUnitStrategy",
    "FileLevelStrategy",
    "ModuleLevelStrategy",
    "ClassChunker",
    "FunctionChunker",
]

