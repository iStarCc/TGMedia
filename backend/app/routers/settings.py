from fastapi import APIRouter
from pydantic import BaseModel

from app.config import settings

router = APIRouter(prefix="/api/settings", tags=["settings"])


class SettingsResponse(BaseModel):
    max_concurrent: int
    auto_download: bool
    ws_throttle_ms: int
    data_dir: str
    download_path: str
    download_by_channel: bool
    download_by_media_type: bool
    allowed_extensions: list[str]
    sync_limit: int
    sync_days: int


class SettingsUpdate(BaseModel):
    max_concurrent: int | None = None
    auto_download: bool | None = None
    ws_throttle_ms: int | None = None
    download_path: str | None = None
    download_by_channel: bool | None = None
    download_by_media_type: bool | None = None
    allowed_extensions: list[str] | None = None
    sync_limit: int | None = None
    sync_days: int | None = None


@router.get("")
async def get_settings() -> SettingsResponse:
    return SettingsResponse(
        max_concurrent=settings.max_concurrent,
        auto_download=settings.auto_download,
        ws_throttle_ms=settings.ws_throttle_ms,
        data_dir=settings.data_dir,
        download_path=settings.download_path or settings.data_dir,
        download_by_channel=settings.download_by_channel,
        download_by_media_type=settings.download_by_media_type,
        allowed_extensions=settings.allowed_extensions,
        sync_limit=settings.sync_limit,
        sync_days=settings.sync_days,
    )


@router.put("")
async def update_settings(req: SettingsUpdate):
    if req.max_concurrent is not None:
        settings.max_concurrent = req.max_concurrent
    if req.auto_download is not None:
        settings.auto_download = req.auto_download
    if req.ws_throttle_ms is not None:
        settings.ws_throttle_ms = req.ws_throttle_ms
    if req.download_path is not None:
        settings.download_path = req.download_path
    if req.download_by_channel is not None:
        settings.download_by_channel = req.download_by_channel
    if req.download_by_media_type is not None:
        settings.download_by_media_type = req.download_by_media_type
    if req.allowed_extensions is not None:
        settings.allowed_extensions = req.allowed_extensions
    if req.sync_limit is not None:
        settings.sync_limit = req.sync_limit
    if req.sync_days is not None:
        settings.sync_days = req.sync_days
    settings.save_to_etc()
    return {"ok": True}
