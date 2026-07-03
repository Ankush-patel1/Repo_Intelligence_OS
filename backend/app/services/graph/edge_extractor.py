"""Edge extraction service.

Creates RepositoryEdge objects representing relationships between nodes
based on parser output from RepositorySymbol metadata.

No database writes - only edge object generation.
"""

import json
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.repository_edge import RepositoryEdge
from app.db.models.repository_file import RepositoryFile
from app.db.models.repository_node import RepositoryNode
from app.db.models.repository_symbol import RepositorySymbol


class EdgeExtractor:
    """Extracts graph edges from parser output and symbol relationships.

    Creates edges representing:
    - CONTAINS: Repository → File, File → Symbol, Class → Method
    - IMPORTS: File → File, Symbol → Symbol
    - CALLS: Function → Function, Method → Method
    - INHERITS: Class → Class
    - IMPLEMENTS: Class → Interface
    - DECLARES: Function → Variable, Class → Field
    - REFERENCES: Symbol → Symbol (general references)
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the edge extractor.

        Args:
            session: Database session for queries
        """
        self.session = session

    async def extract_all_edges(
        self,
        repository_id: UUID,
        nodes: list[RepositoryNode],
    ) -> list[RepositoryEdge]:
        """Extract all edge types for a repository.

        Args:
            repository_id: UUID of the repository
            nodes: List of RepositoryNode objects for the repository

        Returns:
            List of RepositoryEdge objects (not persisted)
        """
        edges: list[RepositoryEdge] = []

        # Create node lookup maps
        node_by_repo = {n.repository_id: n for n in nodes if n.node_type == "repository"}
        node_by_file = {n.repository_file_id: n for n in nodes if n.repository_file_id}
        node_by_symbol = {n.symbol_id: n for n in nodes if n.symbol_id}

        # Extract CONTAINS edges
        contains_edges = await self.extract_contains_edges(nodes)
        edges.extend(contains_edges)

        # Extract IMPORTS edges
        imports_edges = await self.extract_imports_edges(repository_id, nodes, node_by_symbol)
        edges.extend(imports_edges)

        # Extract CALLS edges (placeholder - requires call analysis)
        # Note: Current parsers don't extract call information
        # This would need enhanced parser output

        # Extract INHERITS edges
        inherits_edges = await self.extract_inherits_edges(repository_id, nodes, node_by_symbol)
        edges.extend(inherits_edges)

        # Extract IMPLEMENTS edges
        implements_edges = await self.extract_implements_edges(repository_id, nodes, node_by_symbol)
        edges.extend(implements_edges)

        # Extract DECLARES edges
        declares_edges = await self.extract_declares_edges(nodes, node_by_symbol)
        edges.extend(declares_edges)

        # Extract REFERENCES edges
        references_edges = await self.extract_references_edges(nodes, node_by_symbol)
        edges.extend(references_edges)

        return edges

    async def extract_contains_edges(
        self, nodes: list[RepositoryNode]
    ) -> list[RepositoryEdge]:
        """Extract CONTAINS relationships.

        Creates edges:
        - Repository CONTAINS File
        - File CONTAINS Symbol
        - Class/Symbol CONTAINS Method/Child Symbol

        Args:
            nodes: List of all repository nodes

        Returns:
            List of RepositoryEdge objects for CONTAINS relationships
        """
        edges: list[RepositoryEdge] = []

        # Get nodes by type
        repo_nodes = [n for n in nodes if n.node_type == "repository"]
        file_nodes = [n for n in nodes if n.node_type == "file"]
        symbol_nodes = [n for n in nodes if n.node_type == "symbol"]

        # Repository CONTAINS Files
        for repo_node in repo_nodes:
            for file_node in file_nodes:
                if file_node.repository_id == repo_node.repository_id:
                    edge = RepositoryEdge(
                        source_node_id=repo_node.id,
                        target_node_id=file_node.id,
                        relationship_type="CONTAINS",
                        edge_metadata=json.dumps({
                            "container_type": "repository",
                            "contained_type": "file",
                        }),
                    )
                    edges.append(edge)

        # File CONTAINS Symbols
        for file_node in file_nodes:
            for symbol_node in symbol_nodes:
                if symbol_node.repository_file_id == file_node.repository_file_id:
                    edge = RepositoryEdge(
                        source_node_id=file_node.id,
                        target_node_id=symbol_node.id,
                        relationship_type="CONTAINS",
                        edge_metadata=json.dumps({
                            "container_type": "file",
                            "contained_type": "symbol",
                        }),
                    )
                    edges.append(edge)

        # Symbol CONTAINS Child Symbols (e.g., Class CONTAINS Method)
        for symbol_node in symbol_nodes:
            metadata = json.loads(symbol_node.node_metadata)
            parent_symbol_id = metadata.get("parent_symbol_id")

            if parent_symbol_id:
                # Find parent node
                parent_node = next(
                    (n for n in symbol_nodes if str(n.symbol_id) == parent_symbol_id),
                    None,
                )

                if parent_node:
                    edge = RepositoryEdge(
                        source_node_id=parent_node.id,
                        target_node_id=symbol_node.id,
                        relationship_type="CONTAINS",
                        edge_metadata=json.dumps({
                            "container_type": metadata.get("symbol_type", "symbol"),
                            "contained_type": metadata.get("symbol_type", "symbol"),
                            "parent_child": True,
                        }),
                    )
                    edges.append(edge)

        return edges

    async def extract_imports_edges(
        self,
        repository_id: UUID,
        nodes: list[RepositoryNode],
        node_by_symbol: dict[UUID, RepositoryNode],
    ) -> list[RepositoryEdge]:
        """Extract IMPORTS relationships from import symbols.

        Args:
            repository_id: UUID of the repository
            nodes: List of all repository nodes
            node_by_symbol: Map of symbol_id to node

        Returns:
            List of RepositoryEdge objects for IMPORTS relationships
        """
        edges: list[RepositoryEdge] = []

        # Query import symbols
        result = await self.session.execute(
            select(RepositorySymbol)
            .join(RepositoryFile, RepositorySymbol.repository_file_id == RepositoryFile.id)
            .where(
                RepositoryFile.repository_id == repository_id,
                RepositorySymbol.symbol_type.in_(["import", "from_import", "import_statement"]),
            )
        )
        import_symbols = result.scalars().all()

        # Create IMPORTS edges
        for import_symbol in import_symbols:
            source_node = node_by_symbol.get(import_symbol.id)
            if not source_node:
                continue

            # Parse import statement from symbol_name or signature
            import_name = import_symbol.symbol_name or import_symbol.signature

            metadata = {
                "import_statement": import_name,
                "import_type": import_symbol.symbol_type,
            }

            # Try to parse original metadata
            if import_symbol.symbol_metadata:
                try:
                    original_meta = json.loads(import_symbol.symbol_metadata)
                    metadata.update(original_meta)
                except (json.JSONDecodeError, TypeError):
                    pass

            # For now, create edge with metadata
            # Actual target resolution would require import resolver
            # This creates a placeholder edge structure
            edge = RepositoryEdge(
                source_node_id=source_node.id,
                target_node_id=source_node.id,  # Self-reference until resolved
                relationship_type="IMPORTS",
                edge_metadata=json.dumps(metadata),
            )
            edges.append(edge)

        return edges

    async def extract_inherits_edges(
        self,
        repository_id: UUID,
        nodes: list[RepositoryNode],
        node_by_symbol: dict[UUID, RepositoryNode],
    ) -> list[RepositoryEdge]:
        """Extract INHERITS relationships from class symbols.

        Args:
            repository_id: UUID of the repository
            nodes: List of all repository nodes
            node_by_symbol: Map of symbol_id to node

        Returns:
            List of RepositoryEdge objects for INHERITS relationships
        """
        edges: list[RepositoryEdge] = []

        # Query class symbols
        result = await self.session.execute(
            select(RepositorySymbol)
            .join(RepositoryFile, RepositorySymbol.repository_file_id == RepositoryFile.id)
            .where(
                RepositoryFile.repository_id == repository_id,
                RepositorySymbol.symbol_type == "class",
            )
        )
        class_symbols = result.scalars().all()

        # Extract inheritance from metadata
        for class_symbol in class_symbols:
            source_node = node_by_symbol.get(class_symbol.id)
            if not source_node:
                continue

            # Check metadata for base classes
            if class_symbol.symbol_metadata:
                try:
                    metadata = json.loads(class_symbol.symbol_metadata)
                    base_classes = metadata.get("base_classes", [])

                    for base_class in base_classes:
                        # Create edge (target resolution needed)
                        edge = RepositoryEdge(
                            source_node_id=source_node.id,
                            target_node_id=source_node.id,  # Placeholder
                            relationship_type="INHERITS",
                            edge_metadata=json.dumps({
                                "base_class": base_class,
                                "derived_class": class_symbol.symbol_name,
                            }),
                        )
                        edges.append(edge)
                except (json.JSONDecodeError, TypeError):
                    pass

        return edges

    async def extract_implements_edges(
        self,
        repository_id: UUID,
        nodes: list[RepositoryNode],
        node_by_symbol: dict[UUID, RepositoryNode],
    ) -> list[RepositoryEdge]:
        """Extract IMPLEMENTS relationships (class implements interface).

        Args:
            repository_id: UUID of the repository
            nodes: List of all repository nodes
            node_by_symbol: Map of symbol_id to node

        Returns:
            List of RepositoryEdge objects for IMPLEMENTS relationships
        """
        edges: list[RepositoryEdge] = []

        # Query class symbols
        result = await self.session.execute(
            select(RepositorySymbol)
            .join(RepositoryFile, RepositorySymbol.repository_file_id == RepositoryFile.id)
            .where(
                RepositoryFile.repository_id == repository_id,
                RepositorySymbol.symbol_type == "class",
            )
        )
        class_symbols = result.scalars().all()

        # Extract interfaces from metadata
        for class_symbol in class_symbols:
            source_node = node_by_symbol.get(class_symbol.id)
            if not source_node:
                continue

            # Check metadata for implemented interfaces
            if class_symbol.symbol_metadata:
                try:
                    metadata = json.loads(class_symbol.symbol_metadata)
                    interfaces = metadata.get("interfaces", []) or metadata.get("implements", [])

                    for interface in interfaces:
                        # Create edge (target resolution needed)
                        edge = RepositoryEdge(
                            source_node_id=source_node.id,
                            target_node_id=source_node.id,  # Placeholder
                            relationship_type="IMPLEMENTS",
                            edge_metadata=json.dumps({
                                "interface": interface,
                                "implementing_class": class_symbol.symbol_name,
                            }),
                        )
                        edges.append(edge)
                except (json.JSONDecodeError, TypeError):
                    pass

        return edges

    async def extract_declares_edges(
        self,
        nodes: list[RepositoryNode],
        node_by_symbol: dict[UUID, RepositoryNode],
    ) -> list[RepositoryEdge]:
        """Extract DECLARES relationships.

        Creates edges for:
        - Function DECLARES Variable
        - Class DECLARES Field

        Args:
            nodes: List of all repository nodes
            node_by_symbol: Map of symbol_id to node

        Returns:
            List of RepositoryEdge objects for DECLARES relationships
        """
        edges: list[RepositoryEdge] = []

        symbol_nodes = [n for n in nodes if n.node_type == "symbol"]

        for symbol_node in symbol_nodes:
            metadata = json.loads(symbol_node.node_metadata)
            symbol_type = metadata.get("symbol_type")

            # Function/Method declares parameters
            if symbol_type in ("function", "method"):
                original_meta = metadata.get("original_metadata", {})
                parameters = original_meta.get("parameters", [])

                for param in parameters:
                    edge = RepositoryEdge(
                        source_node_id=symbol_node.id,
                        target_node_id=symbol_node.id,  # Virtual parameter node
                        relationship_type="DECLARES",
                        edge_metadata=json.dumps({
                            "declaration_type": "parameter",
                            "parameter_name": param,
                            "declared_in": symbol_node.display_name,
                        }),
                    )
                    edges.append(edge)

            # Class declares fields
            elif symbol_type == "class":
                original_meta = metadata.get("original_metadata", {})
                fields = original_meta.get("fields", [])

                for field in fields:
                    edge = RepositoryEdge(
                        source_node_id=symbol_node.id,
                        target_node_id=symbol_node.id,  # Virtual field node
                        relationship_type="DECLARES",
                        edge_metadata=json.dumps({
                            "declaration_type": "field",
                            "field_name": field,
                            "declared_in": symbol_node.display_name,
                        }),
                    )
                    edges.append(edge)

        return edges

    async def extract_references_edges(
        self,
        nodes: list[RepositoryNode],
        node_by_symbol: dict[UUID, RepositoryNode],
    ) -> list[RepositoryEdge]:
        """Extract REFERENCES relationships (general symbol references).

        Args:
            nodes: List of all repository nodes
            node_by_symbol: Map of symbol_id to node

        Returns:
            List of RepositoryEdge objects for REFERENCES relationships
        """
        edges: list[RepositoryEdge] = []

        symbol_nodes = [n for n in nodes if n.node_type == "symbol"]

        for symbol_node in symbol_nodes:
            metadata = json.loads(symbol_node.node_metadata)
            symbol_type = metadata.get("symbol_type")

            # Extract decorators as references
            if symbol_type in ("function", "method", "class"):
                original_meta = metadata.get("original_metadata", {})
                decorators = original_meta.get("decorators", [])

                for decorator in decorators:
                    edge = RepositoryEdge(
                        source_node_id=symbol_node.id,
                        target_node_id=symbol_node.id,  # Placeholder
                        relationship_type="REFERENCES",
                        edge_metadata=json.dumps({
                            "reference_type": "decorator",
                            "decorator_name": decorator,
                            "used_by": symbol_node.display_name,
                        }),
                    )
                    edges.append(edge)

        return edges

    async def extract_calls_edges(
        self,
        repository_id: UUID,
        nodes: list[RepositoryNode],
        node_by_symbol: dict[UUID, RepositoryNode],
    ) -> list[RepositoryEdge]:
        """Extract CALLS relationships (function/method calls).

        Note: This requires enhanced parser output that extracts
        function call expressions from the AST. Current parsers
        do not extract this information.

        Args:
            repository_id: UUID of the repository
            nodes: List of all repository nodes
            node_by_symbol: Map of symbol_id to node

        Returns:
            List of RepositoryEdge objects for CALLS relationships
        """
        edges: list[RepositoryEdge] = []

        # TODO: Implement when parsers extract call information
        # Would need:
        # 1. Enhanced parsers to extract call expressions
        # 2. Call target resolution logic
        # 3. Cross-file call tracking

        return edges

    async def get_edge_statistics(
        self, edges: list[RepositoryEdge]
    ) -> dict[str, Any]:
        """Get statistics about extracted edges.

        Args:
            edges: List of extracted edges

        Returns:
            Dictionary with edge counts by type
        """
        edges_by_type: dict[str, int] = {}

        for edge in edges:
            rel_type = edge.relationship_type
            edges_by_type[rel_type] = edges_by_type.get(rel_type, 0) + 1

        return {
            "total_edges": len(edges),
            "edges_by_type": edges_by_type,
            "unique_relationship_types": len(edges_by_type),
        }
