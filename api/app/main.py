import logging
import time
import uuid

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.auth import CurrentUser, get_current_user
from app.config import settings
from app.routers import (
    appliances,
    bills,
    catalog,
    checkin,
    chat,
    detect,
    fault,
    forecast,
    homes,
    models,
    recommendations,
    sizing,
    whatif,
)

app = FastAPI(title="Solar Care AI API", version="0.1.0")
logger = logging.getLogger("solar_care.api")

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(
        dict.fromkeys(
            [
                settings.web_origin,
                "http://localhost:3000",
                "http://127.0.0.1:3000",
            ]
        )
    ),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["Authorization", "Content-Type"],
)


@app.middleware("http")
async def log_request(request: Request, call_next):
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    started_at = time.perf_counter()
    response = None
    try:
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response
    finally:
        duration_ms = round((time.perf_counter() - started_at) * 1000, 2)
        logger.info(
            "request_id=%s user_id=%s method=%s path=%s status=%s duration_ms=%s",
            request_id,
            getattr(request.state, "user_id", None),
            request.method,
            request.url.path,
            response.status_code if response else "error",
            duration_ms,
        )


@app.exception_handler(HTTPException)
async def http_exception_handler(
    request: Request, exc: HTTPException
) -> JSONResponse:
    code = {
        401: "UNAUTHORIZED",
        403: "FORBIDDEN",
        404: "NOT_FOUND",
        413: "PAYLOAD_TOO_LARGE",
        415: "UNSUPPORTED_MEDIA_TYPE",
        422: "VALIDATION_ERROR",
        429: "RATE_LIMITED",
        502: "UPSTREAM_ERROR",
        503: "SERVICE_UNAVAILABLE",
    }.get(exc.status_code, "REQUEST_ERROR")
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": str(exc.detail), "code": code},
        headers=exc.headers,
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    errors = [
        {
            "location": list(error["loc"]),
            "message": error["msg"],
            "type": error["type"],
        }
        for error in exc.errors()
    ]
    return JSONResponse(
        status_code=422,
        content={
            "error": "Request validation failed",
            "code": "VALIDATION_ERROR",
            "details": errors,
        },
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(
    request: Request, exc: Exception
) -> JSONResponse:
    request_id = getattr(request.state, "request_id", "unknown")
    logger.exception("request_id=%s unhandled API error", request_id)
    return JSONResponse(
        status_code=500,
        content={
            "error": "An unexpected server error occurred",
            "code": "INTERNAL_ERROR",
            "request_id": request_id,
        },
    )


app.include_router(homes.router)
app.include_router(appliances.router)
app.include_router(bills.router)
app.include_router(forecast.router)
app.include_router(checkin.router)
app.include_router(chat.router)
app.include_router(fault.router)
app.include_router(recommendations.router)
app.include_router(catalog.router)
app.include_router(detect.router)
app.include_router(models.router)
app.include_router(sizing.router)
app.include_router(whatif.router)


@app.get("/health", tags=["health"])
async def health() -> dict[str, bool]:
    return {"ok": True}


@app.get("/me", tags=["auth"])
async def me(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    return user
