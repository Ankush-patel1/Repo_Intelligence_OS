from fastapi import APIRouter

from app.api.v1 import graph, health, repositories

router = APIRouter()

router.include_router(health.router, tags=["health"])

router.include_router(repositories.router)

router.include_router(graph.router)
