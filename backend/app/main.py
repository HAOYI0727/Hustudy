import logging
from contextlib import asynccontextmanager
from pathlib import Path
from uuid import uuid4
from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from starlette.exceptions import HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from .core.config import get_settings
from .core.database import init_db
from .core.storage import InsufficientStorage
from .routers import question_bank, exam_analysis, connection, mistake_redo
from .routers import (
    assets,
    ai,
    auth,
    courses,
    documents,
    exams,
    health,
    notes,
    note_exports,
    note_organization,
    note_trash,
    note_capture,
    note_ai_config,
    transcripts,
    material_exports,
    remote_ai,
    backups,
)

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s"
)
logger = logging.getLogger("hustudy")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    settings = get_settings()
    Path(settings.storage_root).mkdir(parents=True, exist_ok=True)
    init_db()
    from .services.bank_question_types import upgrade_local_sources

    upgrade_local_sources()
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="Hustudy API", version="0.1.0", lifespan=lifespan)
    app.include_router(connection.router)
    app.include_router(mistake_redo.router)
    app.include_router(question_bank.router)
    app.include_router(exam_analysis.router)
    app.include_router(backups.router)
    app.include_router(note_exports.router)
    app.include_router(note_organization.router)
    app.include_router(note_trash.router)
    app.include_router(note_capture.router)
    app.include_router(note_ai_config.router)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID"],
    )

    @app.middleware("http")
    async def request_id(request: Request, call_next):
        rid = str(uuid4())
        request.state.request_id = rid
        response = await call_next(request)
        response.headers["X-Request-ID"] = rid
        return response

    @app.exception_handler(HTTPException)
    async def http_error(request: Request, exc: HTTPException):
        rid = request.state.request_id
        code = "NOT_FOUND" if exc.status_code == 404 else "HTTP_ERROR"
        return JSONResponse(
            status_code=exc.status_code,
            headers=exc.headers,
            content={
                "error": {
                    "code": code,
                    "message": exc.detail.get("message", "请求失败")
                    if isinstance(exc.detail, dict)
                    else str(exc.detail),
                    "details": exc.detail if isinstance(exc.detail, dict) else {},
                    "request_id": rid,
                }
            },
        )

    @app.exception_handler(InsufficientStorage)
    async def low_storage(request: Request, exc: InsufficientStorage):
        return JSONResponse(
            status_code=507,
            content={
                "error": {
                    "code": "INSUFFICIENT_STORAGE",
                    "message": str(exc),
                    "details": {},
                    "request_id": request.state.request_id,
                }
            },
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError):
        rid = request.state.request_id
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "请求参数校验失败",
                    "details": {
                        "errors": jsonable_encoder(
                            [
                                {
                                    "type": item["type"],
                                    "loc": ["body"],
                                    "msg": "配置参数不合法",
                                }
                                for item in exc.errors()
                            ]
                            if request.url.path == "/api/v1/note-ai/config"
                            else exc.errors(),
                            custom_encoder={ValueError: str},
                        )
                    },
                    "request_id": rid,
                }
            },
        )

    @app.exception_handler(Exception)
    async def unhandled(_request: Request, _exc: Exception):
        rid = _request.state.request_id
        logger.exception("unhandled request error request_id=%s", rid)
        return JSONResponse(
            status_code=500,
            headers={"X-Request-ID": rid},
            content={
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "服务器内部错误",
                    "details": {},
                    "request_id": rid,
                }
            },
        )

    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(courses.router)
    app.include_router(documents.router)
    app.include_router(transcripts.router)
    app.include_router(material_exports.router)
    app.include_router(remote_ai.router)
    app.include_router(assets.router)
    app.include_router(notes.router)
    app.include_router(ai.router)
    app.include_router(exams.router)
    return app


app = create_app()
