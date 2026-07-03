"""Graph API endpoints."""

import json
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.db.models.repository import Repository
from app.db.models.repository_edge import RepositoryEdge
from app.db.models.repository_node import RepositoryNode
from app.schemas.graph import (
    GraphBuildResponse,
    GraphEdgeResponse,
    GraphNodeResponse,
    GraphResponse,
    GraphStatisticsResponse,
)
from app.services.graph import EdgeExtractor, GraphPersister, NodeExtractor

router = APIRouter(prefix="/repositories", tags=["graph"])
DbSessionDep = Depends(get_db)


def get_node_extractor(session: AsyncSession = DbSessionDep) -> NodeExtractor:
    """Dependency for NodeExtractor service."""
    return NodeExtractor(session=session)


def get_edge_extractor(session: AsyncSession = DbSessionDep) -> EdgeExtractor:
    """Dependency for EdgeExtractor service."""
    return EdgeExtractor(session=session)


def get_graph_persister(session: AsyncSession = DbSessionDep) -> GraphPersister:
    """Dependency for GraphPersister service."""
    return GraphPersister(session=session)


NodeExtractorDep = Depends(get_node_extractor)
EdgeExtractorDep = Depends(get_edge_extractor)
GraphPersisterDep = Depends(get_graph_persister)


async def verify_repository_exists(
    repository_id: uuid.UUID, session: AsyncSession
) -> None:
    """Verify that a repository exists.

    Args:
        repository_id: UUID of the repository
        session: Database session

    Raises:
        HTTPException: If repository not found
    """
    result = await session.execute(
        select(Repository).where(Repository.id == repository_id)
    )
    repository = result.scalar_one_or_none()

    if not repository:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Repository {repository_id} not found",
        )


def parse_node_metadata(node: RepositoryNode) -> dict | None:
    """Parse node metadata from JSON string.

    Args:
        node: RepositoryNode object

    Returns:
        Parsed metadata dict or None
    """
    if not node.node_metadata:
        return None

    try:
        return json.loads(node.node_metadata)
    except (json.JSONDecodeError, TypeError):
        return None


def parse_edge_metadata(edge: RepositoryEdge) -> dict | None:
    """Parse edge metadata from JSON string.

    Args:
        edge: RepositoryEdge object

    Returns:
        Parsed metadata dict or None
    """
    if not edge.edge_metadata:
        return None

    try:
        return json.loads(edge.edge_metadata)
    except (json.JSONDecodeError, TypeError):
        return None


@router.post(
    "/{repository_id}/graph",
    response_model=GraphBuildResponse,
    status_code=status.HTTP_201_CREATED,
)
async def build_repository_graph(
    repository_id: uuid.UUID,
    node_extractor: NodeExtractor = NodeExtractorDep,
    edge_extractor: EdgeExtractor = EdgeExtractorDep,
    graph_persister: GraphPersister = GraphPersisterDep,
    session: AsyncSession = DbSessionDep,
) -> GraphBuildResponse:
    """Build and persist knowledge graph for a repository.

    Extracts nodes from Repository, RepositoryFile, and RepositorySymbol records,
    creates edges representing relationships, and persists the graph to the database.

    This will replace any existing graph data for the repository.

    Args:
        repository_id: UUID of the repository

    Returns:
        GraphBuildResponse with persistence statistics
    """
    # Verify repository exists
    await verify_repository_exists(repository_id, session)

    # Extract nodes
    nodes = await node_extractor.extract_repository_nodes(repository_id)

    if not nodes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No nodes found. Repository may not be indexed yet.",
        )

    # Delete old graph
    nodes_deleted = await graph_persister.delete_repository_graph(repository_id)
    
    # Persist nodes first to get IDs
    await graph_persister.persist_nodes(nodes)
    await session.flush()  # Assign IDs to nodes

    # Extract edges (now that nodes have IDs)
    edges = await edge_extractor.extract_all_edges(repository_id, nodes)

    # Persist edges
    await graph_persister.persist_edges(edges)
    await session.flush()

    # Commit transaction
    await session.commit()

    # Get statistics
    graph_stats = await graph_persister.get_graph_statistics(repository_id)

    return GraphBuildResponse(
        repository_id=repository_id,
        nodes_persisted=len(nodes),
        edges_persisted=len(edges),
        nodes_deleted=nodes_deleted,
        edges_deleted=0,  # Cascade deleted
        cleanup_performed=True,
        statistics=GraphStatisticsResponse(**graph_stats),
    )


@router.get("/{repository_id}/graph", response_model=GraphResponse)
async def get_repository_graph(
    repository_id: uuid.UUID,
    graph_persister: GraphPersister = GraphPersisterDep,
    session: AsyncSession = DbSessionDep,
) -> GraphResponse:
    """Get complete knowledge graph for a repository.

    Returns all nodes and edges in the repository's knowledge graph.

    Args:
        repository_id: UUID of the repository

    Returns:
        GraphResponse with nodes, edges, and statistics
    """
    # Verify repository exists
    await verify_repository_exists(repository_id, session)

    # Check if graph exists
    exists = await graph_persister.graph_exists(repository_id)

    if not exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Graph not found for repository {repository_id}. Build the graph first.",
        )

    # Get nodes
    node_result = await session.execute(
        select(RepositoryNode)
        .where(RepositoryNode.repository_id == repository_id)
        .order_by(RepositoryNode.node_type, RepositoryNode.display_name)
    )
    nodes = list(node_result.scalars().all())

    # Get edges
    edge_result = await session.execute(
        select(RepositoryEdge)
        .join(RepositoryNode, RepositoryEdge.source_node_id == RepositoryNode.id)
        .where(RepositoryNode.repository_id == repository_id)
        .order_by(RepositoryEdge.relationship_type, RepositoryEdge.created_at)
    )
    edges = list(edge_result.scalars().all())

    # Get statistics
    statistics = await graph_persister.get_graph_statistics(repository_id)

    # Convert nodes to response models
    node_responses = [
        GraphNodeResponse(
            id=node.id,
            repository_id=node.repository_id,
            repository_file_id=node.repository_file_id,
            symbol_id=node.symbol_id,
            node_type=node.node_type,
            display_name=node.display_name,
            language=node.language,
            metadata=parse_node_metadata(node),
            created_at=node.created_at,
        )
        for node in nodes
    ]

    # Convert edges to response models
    edge_responses = [
        GraphEdgeResponse(
            id=edge.id,
            source_node_id=edge.source_node_id,
            target_node_id=edge.target_node_id,
            relationship_type=edge.relationship_type,
            metadata=parse_edge_metadata(edge),
            created_at=edge.created_at,
        )
        for edge in edges
    ]

    return GraphResponse(
        repository_id=repository_id,
        nodes=node_responses,
        edges=edge_responses,
        statistics=statistics,
    )


@router.get("/{repository_id}/graph/nodes", response_model=list[GraphNodeResponse])
async def get_repository_graph_nodes(
    repository_id: uuid.UUID,
    node_type: str | None = None,
    language: str | None = None,
    session: AsyncSession = DbSessionDep,
) -> list[GraphNodeResponse]:
    """Get graph nodes for a repository.

    Optionally filter by node type or language.

    Args:
        repository_id: UUID of the repository
        node_type: Optional filter by node type (repository, file, symbol)
        language: Optional filter by programming language

    Returns:
        List of GraphNodeResponse objects
    """
    # Verify repository exists
    await verify_repository_exists(repository_id, session)

    # Build query
    query = select(RepositoryNode).where(RepositoryNode.repository_id == repository_id)

    if node_type:
        query = query.where(RepositoryNode.node_type == node_type)

    if language:
        query = query.where(RepositoryNode.language == language)

    query = query.order_by(RepositoryNode.node_type, RepositoryNode.display_name)

    # Execute query
    result = await session.execute(query)
    nodes = list(result.scalars().all())

    # Convert to response models
    return [
        GraphNodeResponse(
            id=node.id,
            repository_id=node.repository_id,
            repository_file_id=node.repository_file_id,
            symbol_id=node.symbol_id,
            node_type=node.node_type,
            display_name=node.display_name,
            language=node.language,
            metadata=parse_node_metadata(node),
            created_at=node.created_at,
        )
        for node in nodes
    ]


@router.get("/{repository_id}/graph/edges", response_model=list[GraphEdgeResponse])
async def get_repository_graph_edges(
    repository_id: uuid.UUID,
    relationship_type: str | None = None,
    session: AsyncSession = DbSessionDep,
) -> list[GraphEdgeResponse]:
    """Get graph edges for a repository.

    Optionally filter by relationship type.

    Args:
        repository_id: UUID of the repository
        relationship_type: Optional filter by relationship type (CONTAINS, IMPORTS, etc.)

    Returns:
        List of GraphEdgeResponse objects
    """
    # Verify repository exists
    await verify_repository_exists(repository_id, session)

    # Build query
    query = (
        select(RepositoryEdge)
        .join(RepositoryNode, RepositoryEdge.source_node_id == RepositoryNode.id)
        .where(RepositoryNode.repository_id == repository_id)
    )

    if relationship_type:
        query = query.where(RepositoryEdge.relationship_type == relationship_type)

    query = query.order_by(RepositoryEdge.relationship_type, RepositoryEdge.created_at)

    # Execute query
    result = await session.execute(query)
    edges = list(result.scalars().all())

    # Convert to response models
    return [
        GraphEdgeResponse(
            id=edge.id,
            source_node_id=edge.source_node_id,
            target_node_id=edge.target_node_id,
            relationship_type=edge.relationship_type,
            metadata=parse_edge_metadata(edge),
            created_at=edge.created_at,
        )
        for edge in edges
    ]


@router.get("/{repository_id}/graph/node/{node_id}", response_model=GraphNodeResponse)
async def get_graph_node(
    repository_id: uuid.UUID,
    node_id: uuid.UUID,
    session: AsyncSession = DbSessionDep,
) -> GraphNodeResponse:
    """Get a specific graph node.

    Args:
        repository_id: UUID of the repository
        node_id: UUID of the node

    Returns:
        GraphNodeResponse object
    """
    # Verify repository exists
    await verify_repository_exists(repository_id, session)

    # Get node
    result = await session.execute(
        select(RepositoryNode).where(
            RepositoryNode.id == node_id,
            RepositoryNode.repository_id == repository_id,
        )
    )
    node = result.scalar_one_or_none()

    if not node:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Node {node_id} not found in repository {repository_id}",
        )

    return GraphNodeResponse(
        id=node.id,
        repository_id=node.repository_id,
        repository_file_id=node.repository_file_id,
        symbol_id=node.symbol_id,
        node_type=node.node_type,
        display_name=node.display_name,
        language=node.language,
        metadata=parse_node_metadata(node),
        created_at=node.created_at,
    )
