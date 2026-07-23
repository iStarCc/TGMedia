import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from starlette.staticfiles import StaticFiles
from starlette.responses import FileResponse

from app.config import settings
from app.database import close_db, get_db
from app.version import APP_VERSION
from app.routers import auth, channels, media, settings as settings_router, stats, tasks
from app.services.file_manager import ensure_dirs
from app.services.scheduler import start_cache_cleaner, start_event_listener, start_stats_broadcaster, stop_event_listener
from app.services.telegram import tg_manager
from app.ws.manager import ws_manager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

_bg_tasks: list[asyncio.Task] = []


def _cleanup_telethon_sessions() -> None:
    """清理旧的 Telethon session 文件（迁移到 TDLib 后不再需要）"""
    var_dir = Path(settings.var_dir)
    if not var_dir.exists():
        return
    for f in var_dir.glob("account_*.session"):
        f.unlink(missing_ok=True)
        logger.info("Removed legacy Telethon session: %s", f.name)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("TGMedia starting up...")
    _cleanup_telethon_sessions()
    await get_db()
    ensure_dirs()
    logger.info("Database initialized, media dirs ready")

    await start_event_listener()
    _bg_tasks.append(asyncio.create_task(start_stats_broadcaster()))
    _bg_tasks.append(asyncio.create_task(start_cache_cleaner()))
    logger.info("Background services started")

    yield

    logger.info("TGMedia shutting down...")
    await stop_event_listener()
    for t in _bg_tasks:
        t.cancel()
    await tg_manager.stop_all()
    await close_db()


_root_path = settings.root_path.rstrip("/") if settings.root_path else ""

_fastapi = FastAPI(
    title="TGMedia",
    version=APP_VERSION,
    lifespan=lifespan,
)

_fastapi.include_router(auth.router)
_fastapi.include_router(channels.router)
_fastapi.include_router(tasks.router)
_fastapi.include_router(media.router)
_fastapi.include_router(stats.router)
_fastapi.include_router(settings_router.router)


@_fastapi.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws_manager.connect(ws)
    try:
        while True:
            data = await ws.receive_text()
            if data == "ping":
                await ws.send_text('{"event":"pong","data":{}}')
    except WebSocketDisconnect:
        ws_manager.disconnect(ws)


@_fastapi.get("/api/health")
async def health():
    return {"status": "ok", "version": APP_VERSION}


class SPAStaticFiles(StaticFiles):
    """index.html 禁止缓存，带 hash 的 assets 长期缓存"""

    async def get_response(self, path: str, scope):
        response = await super().get_response(path, scope)
        if isinstance(response, FileResponse):
            if path.startswith("assets/"):
                response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
            elif (response.media_type or "").startswith("text/html") or not path or "." not in Path(path).name:
                response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
                response.headers["Pragma"] = "no-cache"
        return response


www_dir = Path(__file__).parent.parent / "www"
if www_dir.exists():
    _fastapi.mount("/", SPAStaticFiles(directory=str(www_dir), html=True), name="static")


if _root_path:
    from starlette.types import ASGIApp, Receive, Scope, Send

    class _StripPrefixMiddleware:
        """剥离网关前缀，使内部路由无需感知部署路径"""

        def __init__(self, inner: ASGIApp, prefix: str):
            self._inner = inner
            self._prefix = prefix

        async def __call__(self, scope: Scope, receive: Receive, send: Send):
            if scope["type"] in ("http", "websocket"):
                path: str = scope.get("path", "")
                if path.startswith(self._prefix):
                    scope["path"] = path[len(self._prefix):] or "/"
                    scope["root_path"] = self._prefix + scope.get("root_path", "")
            await self._inner(scope, receive, send)

    app = _StripPrefixMiddleware(_fastapi, _root_path)  # type: ignore[assignment]
else:
    app = _fastapi  # type: ignore[assignment]
