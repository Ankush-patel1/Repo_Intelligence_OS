from fastapi import Request
from fastapi.responses import JSONResponse

from app.core.exceptions.base import AppError


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    status_codes = {
        "resource_not_found": 404,
        "validation_error": 422,
        "unauthorized": 401,
        "forbidden": 403,
        "conflict": 409,
        "upstream_error": 502,
        "service_unavailable": 503,
    }
    status_code = status_codes.get(exc.code, 500)
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "details": exc.details,
            },
            "meta": {
                "request_id": request.headers.get("X-Request-ID", "unknown"),
            },
        },
    )
