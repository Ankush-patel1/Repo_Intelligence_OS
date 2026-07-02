import time

from fastapi import APIRouter, FastAPI
from fastapi.responses import JSONResponse

from app.api.errors import app_error_handler
from app.api.router import router
from app.core.exceptions.base import AppError
from app.core.logging.correlation import CorrelationIDMiddleware
from app.core.logging.setup import setup_logging
from app.core.middleware.cors import setup_cors
from app.core.middleware.request_id import RequestIDMiddleware

app = FastAPI(
    title="Repo Intelligence OS API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

setup_logging()
setup_cors(app)

app.add_middleware(CorrelationIDMiddleware)
app.add_middleware(RequestIDMiddleware)

health_router = APIRouter(tags=["health"])


@health_router.get("/health")
async def root_health():
    return {"status": "healthy"}


app.add_exception_handler(AppError, app_error_handler)

app.include_router(health_router)
app.include_router(router, prefix="/api/v1")


@app.exception_handler(Exception)
async def global_exception_handler(request, _exc):
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "internal_error",
                "message": "An unexpected error occurred",
                "details": {},
            },
            "meta": {
                "request_id": request.headers.get("X-Request-ID", "unknown"),
                "timestamp": time.time(),
            },
        },
    )
