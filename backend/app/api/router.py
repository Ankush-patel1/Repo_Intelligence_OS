from fastapi import APIRouter

from app.api.v1 import chunks, graph, health, repositories

router = APIRouter()

router.include_router(health.router, tags=["health"])

router.include_router(repositories.router)

router.include_router(graph.router)

router.include_router(chunks.router, tags=["chunks"])
