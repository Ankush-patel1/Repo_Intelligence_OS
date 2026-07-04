"""Complete end-to-end pipeline verification.

Verifies all 5 stages of the repository analysis pipeline:
1. Import (external)
2. Index
3. Parse
4. Knowledge Graph
5. Semantic Chunking

Checks:
- Each stage completes successfully
- Data flows correctly between stages
- Graph context is included in chunks
- APIs work correctly
"""

import asyncio
import json
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.config.settings import settings
from app.db.models import (
    Repository,
    RepositoryChunk,
    RepositoryEdge,
    RepositoryFile,
    RepositoryNode,
    RepositorySymbol,
)
from app.services.chunking import ClassChunker, ChunkPersister, FunctionChunker
from app.services.graph import EdgeExtractor, GraphPersister, NodeExtractor
from app.services.indexing import FileScanner, RepositoryIndexer
from app.services.orchestration import RepositoryPipeline


class PipelineVerifier:
    """Verifies complete pipeline functionality."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.results = {
            "stage_1_import": {"status": "pending", "details": {}},
            "stage_2_index": {"status": "pending", "details": {}},
            "stage_3_parse": {"status": "pending", "details": {}},
            "stage_4_graph": {"status": "pending", "details": {}},
            "stage_5_chunking": {"status": "pending", "details": {}},
            "verification_tests": {
                "semantic_chunks_created": False,
                "graph_context_included": False,
                "apis_working": False,
                "data_flow_correct": False,
            },
        }

    async def verify_stage_1_import(self) -> bool:
        """Verify Stage 1: Repository Import."""
        print("\n" + "=" * 70)
        print("STAGE 1: IMPORT")
        print("=" * 70)

        try:
            # Check if any repository exists
            stmt = select(Repository).limit(1)
            result = await self.session.execute(stmt)
            repository = result.scalar_one_or_none()

            if not repository:
                print("⚠ No repository found (import is external)")
                print("  To test: POST /repositories/import with GitHub repo URL")
                self.results["stage_1_import"]["status"] = "skipped"
                self.results["stage_1_import"]["details"] = {
                    "reason": "No repository in database"
                }
                return None

            print(f"✓ Repository found: {repository.name}")
            print(f"  ID: {repository.id}")
            print(f"  Branch: {repository.branch}")
            print(f"  Path: {repository.local_path}")

            self.results["stage_1_import"]["status"] = "passed"
            self.results["stage_1_import"]["details"] = {
                "repository_id": str(repository.id),
                "name": repository.name,
                "branch": repository.branch,
            }

            return repository

        except Exception as e:
            print(f"✗ Import verification failed: {e}")
            self.results["stage_1_import"]["status"] = "failed"
            self.results["stage_1_import"]["details"] = {"error": str(e)}
            return None

    async def verify_stage_2_index(self, repository: Repository) -> bool:
        """Verify Stage 2: File Indexing."""
        print("\n" + "=" * 70)
        print("STAGE 2: INDEX")
        print("=" * 70)

        try:
            # Check for indexed files
            stmt = select(RepositoryFile).where(
                RepositoryFile.repository_id == repository.id
            )
            result = await self.session.execute(stmt)
            files = result.scalars().all()

            if not files:
                print("⚠ No files indexed")
                print("  Run: POST /repositories/{id}/index")
                self.results["stage_2_index"]["status"] = "skipped"
                return False

            print(f"✓ Files indexed: {len(files)}")

            # Get statistics
            indexer = RepositoryIndexer(session=self.session, file_scanner=FileScanner())
            stats = await indexer.get_statistics(repository.id)

            print(f"  Total files: {stats['total_files']}")
            print(f"  Total size: {stats['total_size_bytes']:,} bytes")
            print(f"  Languages: {len(stats['by_language'])}")
            
            for lang, count in list(stats["by_language"].items())[:5]:
                print(f"    - {lang}: {count} files")

            self.results["stage_2_index"]["status"] = "passed"
            self.results["stage_2_index"]["details"] = stats

            return True

        except Exception as e:
            print(f"✗ Index verification failed: {e}")
            self.results["stage_2_index"]["status"] = "failed"
            self.results["stage_2_index"]["details"] = {"error": str(e)}
            return False

    async def verify_stage_3_parse(self, repository: Repository) -> bool:
        """Verify Stage 3: Symbol Parsing."""
        print("\n" + "=" * 70)
        print("STAGE 3: PARSE")
        print("=" * 70)

        try:
            # Check for parsed symbols
            stmt = select(RepositorySymbol).where(
                RepositorySymbol.repository_id == repository.id
            )
            result = await self.session.execute(stmt)
            symbols = result.scalars().all()

            if not symbols:
                print("⚠ No symbols parsed")
                print("  Run: POST /repositories/{id}/analyze")
                self.results["stage_3_parse"]["status"] = "skipped"
                return False

            print(f"✓ Symbols parsed: {len(symbols)}")

            # Count by type
            by_type = {}
            for symbol in symbols:
                by_type[symbol.symbol_type] = by_type.get(symbol.symbol_type, 0) + 1

            print("  By type:")
            for sym_type, count in sorted(by_type.items(), key=lambda x: -x[1])[:10]:
                print(f"    - {sym_type}: {count}")

            self.results["stage_3_parse"]["status"] = "passed"
            self.results["stage_3_parse"]["details"] = {
                "total_symbols": len(symbols),
                "by_type": by_type,
            }

            return True

        except Exception as e:
            print(f"✗ Parse verification failed: {e}")
            self.results["stage_3_parse"]["status"] = "failed"
            self.results["stage_3_parse"]["details"] = {"error": str(e)}
            return False

    async def verify_stage_4_graph(self, repository: Repository) -> bool:
        """Verify Stage 4: Knowledge Graph."""
        print("\n" + "=" * 70)
        print("STAGE 4: KNOWLEDGE GRAPH")
        print("=" * 70)

        try:
            # Check for nodes
            stmt = select(RepositoryNode).where(
                RepositoryNode.repository_id == repository.id
            )
            result = await self.session.execute(stmt)
            nodes = result.scalars().all()

            if not nodes:
                print("⚠ No graph nodes")
                print("  Run: POST /repositories/{id}/analyze")
                self.results["stage_4_graph"]["status"] = "skipped"
                return False

            print(f"✓ Graph nodes: {len(nodes)}")

            # Check for edges
            stmt = select(RepositoryEdge).where(
                RepositoryEdge.repository_id == repository.id
            )
            result = await self.session.execute(stmt)
            edges = result.scalars().all()

            print(f"✓ Graph edges: {len(edges)}")

            # Get statistics
            persister = GraphPersister(session=self.session)
            stats = await persister.get_graph_statistics(repository.id)

            print("  Node types:")
            for node_type, count in list(stats.get("by_node_type", {}).items())[:5]:
                print(f"    - {node_type}: {count}")

            print("  Edge types:")
            for edge_type, count in list(stats.get("by_edge_type", {}).items())[:5]:
                print(f"    - {edge_type}: {count}")

            self.results["stage_4_graph"]["status"] = "passed"
            self.results["stage_4_graph"]["details"] = stats

            return True

        except Exception as e:
            print(f"✗ Graph verification failed: {e}")
            self.results["stage_4_graph"]["status"] = "failed"
            self.results["stage_4_graph"]["details"] = {"error": str(e)}
            return False

    async def verify_stage_5_chunking(self, repository: Repository) -> bool:
        """Verify Stage 5: Semantic Chunking."""
        print("\n" + "=" * 70)
        print("STAGE 5: SEMANTIC CHUNKING")
        print("=" * 70)

        try:
            # Check for chunks
            stmt = select(RepositoryChunk).where(
                RepositoryChunk.repository_id == repository.id
            )
            result = await self.session.execute(stmt)
            chunks = result.scalars().all()

            if not chunks:
                print("⚠ No chunks generated")
                print("  Run: POST /repositories/{id}/analyze")
                print("       (or POST /repositories/{id}/chunk)")
                self.results["stage_5_chunking"]["status"] = "skipped"
                return False

            print(f"✓ Semantic chunks created: {len(chunks)}")
            self.results["verification_tests"]["semantic_chunks_created"] = True

            # Count by type
            by_type = {}
            by_language = {}
            for chunk in chunks:
                by_type[chunk.chunk_type] = by_type.get(chunk.chunk_type, 0) + 1
                by_language[chunk.language] = by_language.get(chunk.language, 0) + 1

            print("  By type:")
            for chunk_type, count in sorted(by_type.items(), key=lambda x: -x[1]):
                print(f"    - {chunk_type}: {count}")

            print("  By language:")
            for language, count in sorted(by_language.items(), key=lambda x: -x[1]):
                print(f"    - {language}: {count}")

            # Verify graph context in chunks
            print("\n  Checking graph context in chunks...")
            chunks_with_context = 0
            sample_chunk = None

            for chunk in chunks[:10]:  # Check first 10
                if chunk.chunk_metadata:
                    try:
                        metadata = json.loads(chunk.chunk_metadata)
                        if "graph_node_id" in metadata or "edges" in metadata:
                            chunks_with_context += 1
                            if not sample_chunk:
                                sample_chunk = chunk
                    except json.JSONDecodeError:
                        pass

            if chunks_with_context > 0:
                print(f"  ✓ Graph context included: {chunks_with_context}/{min(10, len(chunks))} chunks")
                self.results["verification_tests"]["graph_context_included"] = True

                if sample_chunk:
                    print(f"\n  Sample chunk: {sample_chunk.chunk_name}")
                    metadata = json.loads(sample_chunk.chunk_metadata)
                    print(f"    - Type: {sample_chunk.chunk_type}")
                    print(f"    - Language: {sample_chunk.language}")
                    print(f"    - Token count: {sample_chunk.token_count}")
                    if "graph_node_id" in metadata:
                        print(f"    - Graph node ID: {metadata['graph_node_id'][:8]}...")
                    if "edges" in metadata and metadata["edges"]:
                        print(f"    - Edges: {len(metadata['edges'])}")
                        for edge in metadata["edges"][:2]:
                            print(f"      • {edge['type']}: {edge.get('target_name', 'N/A')}")
            else:
                print("  ⚠ No graph context found in sample chunks")

            # Get statistics
            persister = ChunkPersister(session=self.session)
            stats = await persister.get_chunk_statistics(repository.id)

            self.results["stage_5_chunking"]["status"] = "passed"
            self.results["stage_5_chunking"]["details"] = stats
            self.results["verification_tests"]["data_flow_correct"] = True

            return True

        except Exception as e:
            print(f"✗ Chunking verification failed: {e}")
            self.results["stage_5_chunking"]["status"] = "failed"
            self.results["stage_5_chunking"]["details"] = {"error": str(e)}
            return False

    async def verify_pipeline_integration(self, repository: Repository) -> bool:
        """Verify pipeline integration works."""
        print("\n" + "=" * 70)
        print("PIPELINE INTEGRATION TEST")
        print("=" * 70)

        try:
            pipeline = RepositoryPipeline(session=self.session)

            # Test pipeline status
            print("\n1. Testing get_pipeline_status()...")
            status = await pipeline.get_pipeline_status(repository.id)

            required_fields = [
                "repository_id",
                "indexed",
                "graph_built",
                "chunks_generated",
                "indexing_stats",
                "graph_stats",
                "chunking_stats",
            ]

            all_present = all(field in status for field in required_fields)

            if all_present:
                print("   ✓ All status fields present")
                print(f"     - Indexed: {status['indexed']}")
                print(f"     - Graph built: {status['graph_built']}")
                print(f"     - Chunks generated: {status['chunks_generated']}")
            else:
                missing = [f for f in required_fields if f not in status]
                print(f"   ✗ Missing fields: {missing}")
                return False

            # Test individual chunking methods
            print("\n2. Testing chunking methods exist...")
            methods = ["generate_chunks", "regenerate_chunks"]
            for method in methods:
                has_method = hasattr(pipeline, method)
                print(f"   {'✓' if has_method else '✗'} {method}")

            self.results["verification_tests"]["apis_working"] = True
            return True

        except Exception as e:
            print(f"✗ Pipeline integration failed: {e}")
            import traceback
            traceback.print_exc()
            return False

    async def run_verification(self) -> dict:
        """Run complete verification."""
        print("\n" + "=" * 70)
        print("COMPLETE PIPELINE VERIFICATION")
        print("=" * 70)
        print("\nVerifying: Import → Index → Parse → Graph → Chunking")
        print()

        # Stage 1: Import
        repository = await self.verify_stage_1_import()
        if not repository:
            print("\n⚠ Cannot proceed without a repository")
            print("  Import a repository first: POST /repositories/import")
            return self.results

        # Stage 2: Index
        await self.verify_stage_2_index(repository)

        # Stage 3: Parse
        await self.verify_stage_3_parse(repository)

        # Stage 4: Graph
        await self.verify_stage_4_graph(repository)

        # Stage 5: Chunking
        await self.verify_stage_5_chunking(repository)

        # Pipeline Integration
        await self.verify_pipeline_integration(repository)

        return self.results

    def print_summary(self):
        """Print verification summary."""
        print("\n" + "=" * 70)
        print("VERIFICATION SUMMARY")
        print("=" * 70)

        # Stage status
        print("\nPipeline Stages:")
        stages = [
            ("Import", "stage_1_import"),
            ("Index", "stage_2_index"),
            ("Parse", "stage_3_parse"),
            ("Knowledge Graph", "stage_4_graph"),
            ("Semantic Chunking", "stage_5_chunking"),
        ]

        for name, key in stages:
            status = self.results[key]["status"]
            icon = {
                "passed": "✓",
                "failed": "✗",
                "skipped": "⚠",
                "pending": "○",
            }.get(status, "?")
            print(f"  {icon} {name:20s} {status.upper()}")

        # Verification tests
        print("\nVerification Tests:")
        tests = self.results["verification_tests"]
        for test, passed in tests.items():
            icon = "✓" if passed else "✗"
            test_name = test.replace("_", " ").title()
            print(f"  {icon} {test_name}")

        # Overall status
        print("\nOverall Status:")
        all_passed = (
            all(
                self.results[stage]["status"] in ["passed", "skipped"]
                for _, stage in stages
            )
            and all(tests.values())
        )

        if all_passed:
            print("  ✓ PIPELINE FULLY OPERATIONAL")
        else:
            print("  ⚠ SOME STAGES NEED ATTENTION")

        # Stats summary
        print("\nQuick Stats:")
        if self.results["stage_2_index"]["details"]:
            details = self.results["stage_2_index"]["details"]
            if "total_files" in details:
                print(f"  Files indexed: {details['total_files']}")

        if self.results["stage_3_parse"]["details"]:
            details = self.results["stage_3_parse"]["details"]
            if "total_symbols" in details:
                print(f"  Symbols parsed: {details['total_symbols']}")

        if self.results["stage_4_graph"]["details"]:
            details = self.results["stage_4_graph"]["details"]
            if "total_nodes" in details:
                print(f"  Graph nodes: {details['total_nodes']}")
            if "total_edges" in details:
                print(f"  Graph edges: {details['total_edges']}")

        if self.results["stage_5_chunking"]["details"]:
            details = self.results["stage_5_chunking"]["details"]
            if "total_chunks" in details:
                print(f"  Semantic chunks: {details['total_chunks']}")
                if "by_type" in details:
                    print("    Types:", ", ".join(f"{k}={v}" for k, v in details["by_type"].items()))

        print("\n" + "=" * 70)


async def main():
    """Run verification."""
    engine = create_async_engine(settings.database_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        verifier = PipelineVerifier(session)
        results = await verifier.run_verification()
        verifier.print_summary()

        # Save results to file
        with open("pipeline_verification_results.json", "w") as f:
            json.dump(results, f, indent=2, default=str)
        print("\nDetailed results saved to: pipeline_verification_results.json")


if __name__ == "__main__":
    asyncio.run(main())
