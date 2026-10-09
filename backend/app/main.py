import logging
from contextlib import asynccontextmanager
from pathlib import Path
from uuid import uuid4
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from .core.config import get_settings
from .core.database import init_db
from .routers import ai, auth, courses, documents, exams, health, notes
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("hustudy")
@asynccontextmanager
async def lifespan(_app: FastAPI):
    settings = get_settings(); Path(settings.storage_root).mkdir(parents=True, exist_ok=True); init_db(); yield
def create_app() -> FastAPI:
    settings = get_settings(); app = FastAPI(title="Hustudy API", version="0.1.0", lifespan=lifespan)
    app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origin_list, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
    @app.middleware("http")
    async def request_id(request: Request, call_next):
        rid = request.headers.get("X-Request-ID", str(uuid4())); response = await call_next(request); response.headers["X-Request-ID"] = rid; return response
    @app.exception_handler(HTTPException)
    async def http_error(request: Request, exc: HTTPException):
        rid = request.headers.get("X-Request-ID", str(uuid4()))
        code = "NOT_FOUND" if exc.status_code == 404 else "HTTP_ERROR"
        return JSONResponse(status_code=exc.status_code, content={"error": {"code": code, "message": str(exc.detail), "details": {}, "request_id": rid}})

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError):
        rid = request.headers.get("X-Request-ID", str(uuid4()))
        return JSONResponse(status_code=422, content={"error": {"code": "VALIDATION_ERROR", "message": "请求参数校验失败", "details": {"errors": exc.errors()}, "request_id": rid}})

    @app.exception_handler(Exception)
    async def unhandled(_request: Request, _exc: Exception):
        rid = str(uuid4()); logger.exception("unhandled request error request_id=%s", rid)
        return JSONResponse(status_code=500, content={"error": {"code": "INTERNAL_ERROR", "message": "服务器内部错误", "details": {}, "request_id": rid}})
    app.include_router(health.router); app.include_router(auth.router); app.include_router(courses.router)
    app.include_router(documents.router); app.include_router(notes.router); app.include_router(ai.router); app.include_router(exams.router)
    return app
app = create_app()
