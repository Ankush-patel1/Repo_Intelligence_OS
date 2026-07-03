"""Graph API schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class GraphNodeResponse(BaseModel):
    """Response model for a graph node."""

    id: uuid.UUID
    repository_id: uuid.UUID
    repository_file_id: uuid.UUID | None
    symbol_id: uuid.UUID | None
    node_type: str
    display_name: str
    language: str | None
    metadata: dict | None = Field(None, description="Node metadata as parsed JSON")
    created_at: datetime

    model_config = {"from_attributes": True}


class GraphEdgeResponse(BaseModel):
    """Response model for a graph edge."""

    id: uuid.UUID
    source_node_id: uuid.UUID
    target_node_id: uuid.UUID
    relationship_type: str
    metadata: dict | None = Field(None, description="Edge metadata as parsed JSON")
    created_at: datetime

    model_config = {"from_attributes": True}


class GraphResponse(BaseModel):
    """Response model for complete graph."""

    repository_id: uuid.UUID
    nodes: list[GraphNodeResponse]
    edges: list[GraphEdgeResponse]
    statistics: dict


class GraphStatisticsResponse(BaseModel):
    """Response model for graph statistics."""

    repository_id: uuid.UUID
    total_nodes: int
    nodes_by_type: dict[str, int]
    total_edges: int
    edges_by_type: dict[str, int]
    graph_exists: bool


class GraphBuildResponse(BaseModel):
    """Response model for graph build operation."""

    repository_id: uuid.UUID
    nodes_persisted: int
    edges_persisted: int
    nodes_deleted: int
    edges_deleted: int
    cleanup_performed: bool
    statistics: GraphStatisticsResponse
