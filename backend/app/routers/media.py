from pathlib import Path

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.database import get_db
from app.models.media import MediaFileResponse, MediaListResponse
from app.services.file_manager import get_caption, get_file_size, get_filename, get_media_type

router = APIRouter(prefix="/api/media", tags=["media"])


class MediaMessageResponse(BaseModel):
    message_id: int
    channel_id: int | None = None
    channel_title: str = ""
    media_type: str
    filename: str
    file_size: int = 0
    text: str = ""
    date: str = ""


_SORT_COLUMNS = {"filename", "file_size", "created_at"}


@router.get("")
async def list_media(
    media_type: str | None = None,
    search: str | None = None,
    sort: str | None = None,
    order: str = "desc",
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=0, le=10000),
) -> MediaListResponse:
    db = await get_db()
    conditions = []
    params: list = []

    if media_type and media_type != "all":
        conditions.append("media_type=?")
        params.append(media_type)
    if search:
        conditions.append("filename LIKE ?")
        params.append(f"%{search}%")

    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    total_row = await db.execute_fetchall(
        f"SELECT COUNT(*) as cnt FROM media_files {where}", params
    )
    total = total_row[0]["cnt"]

    sort_col = sort if sort in _SORT_COLUMNS else "created_at"
    sort_dir = "ASC" if order == "asc" else "DESC"

    offset = (page - 1) * page_size if page_size > 0 else 0
    if page_size > 0:
        rows = await db.execute_fetchall(
            f"SELECT * FROM media_files {where} ORDER BY {sort_col} {sort_dir} LIMIT ? OFFSET ?",
            [*params, page_size, offset],
        )
    else:
        rows = await db.execute_fetchall(
            f"SELECT * FROM media_files {where} ORDER BY {sort_col} {sort_dir}",
            params,
        )
    files = [MediaFileResponse(**dict(r)) for r in rows]
    return MediaListResponse(files=files, total=total)


_MIME_MAP = {
    ".mp4": "video/mp4", ".mkv": "video/x-matroska", ".avi": "video/x-msvideo",
    ".webm": "video/webm", ".mov": "video/quicktime",
    ".mp3": "audio/mpeg", ".flac": "audio/flac", ".ogg": "audio/ogg",
    ".wav": "audio/wav", ".aac": "audio/aac", ".m4a": "audio/mp4",
    ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png",
    ".gif": "image/gif", ".webp": "image/webp", ".svg": "image/svg+xml",
    ".txt": "text/plain", ".log": "text/plain", ".md": "text/markdown",
    ".json": "application/json", ".xml": "text/xml", ".csv": "text/csv",
    ".html": "text/html", ".css": "text/css", ".js": "text/javascript",
    ".pdf": "application/pdf",
}


@router.get("/{media_id}/message")
async def get_media_message(media_id: int) -> MediaMessageResponse:
    from datetime import datetime, timezone

    from pytdbot import types

    from app.services.telegram import tg_manager

    db = await get_db()
    rows = await db.execute_fetchall(
        """
        SELECT m.filename AS stored_filename, m.media_type AS stored_media_type,
               m.file_size AS stored_file_size, m.channel_id,
               t.message_id, t.chat_id, t.account_id AS task_account_id,
               c.title AS channel_title, c.telegram_id, c.account_id AS channel_account_id
        FROM media_files m
        LEFT JOIN tasks t ON t.id = m.task_id
        LEFT JOIN channels c ON c.id = m.channel_id
        WHERE m.id=?
        """,
        (media_id,),
    )
    if not rows:
        raise HTTPException(404, "文件不存在")

    row = dict(rows[0])
    message_id = row.get("message_id")
    if not message_id:
        raise HTTPException(404, "该文件未关联 Telegram 消息")

    account_id = row.get("task_account_id") or row.get("channel_account_id")
    chat_id = row.get("chat_id") or row.get("telegram_id")
    if not account_id or not chat_id:
        raise HTTPException(404, "缺少频道或账号信息，无法获取消息")

    try:
        client = await tg_manager.get_client(account_id)
        message = await client.getMessage(chat_id=chat_id, message_id=message_id)
    except Exception as e:
        raise HTTPException(502, f"获取消息失败: {e}") from e

    if isinstance(message, types.Error):
        raise HTTPException(404, f"无法获取消息: {message.message}")

    media_type = get_media_type(message) or row["stored_media_type"]
    fname = get_filename(message) or row["stored_filename"]
    file_size = get_file_size(message) or row["stored_file_size"] or 0
    caption = get_caption(message)
    msg_date = ""
    if hasattr(message, "date") and message.date:
        msg_date = datetime.fromtimestamp(message.date, tz=timezone.utc).isoformat()

    return MediaMessageResponse(
        message_id=message.id,
        channel_id=row.get("channel_id"),
        channel_title=row.get("channel_title") or "",
        media_type=media_type,
        filename=fname,
        file_size=file_size,
        text=caption,
        date=msg_date,
    )


@router.get("/{media_id}/preview")
async def preview_media(media_id: int):
    db = await get_db()
    rows = await db.execute_fetchall(
        "SELECT file_path, filename FROM media_files WHERE id=?", (media_id,)
    )
    if not rows:
        raise HTTPException(404, "文件不存在")
    file_path = Path(rows[0]["file_path"])
    if not file_path.exists():
        raise HTTPException(404, "文件已被删除")
    ext = file_path.suffix.lower()
    mime = _MIME_MAP.get(ext, "application/octet-stream")
    return FileResponse(path=str(file_path), media_type=mime)


@router.get("/{media_id}/download")
async def download_media(media_id: int):
    db = await get_db()
    rows = await db.execute_fetchall(
        "SELECT file_path, filename FROM media_files WHERE id=?", (media_id,)
    )
    if not rows:
        raise HTTPException(404, "文件不存在")
    file_path = Path(rows[0]["file_path"])
    if not file_path.exists():
        raise HTTPException(404, "文件已被删除")
    return FileResponse(
        path=str(file_path),
        filename=rows[0]["filename"],
        media_type="application/octet-stream",
    )


@router.delete("/{media_id}")
async def delete_media(media_id: int):
    db = await get_db()
    rows = await db.execute_fetchall("SELECT file_path FROM media_files WHERE id=?", (media_id,))
    if rows:
        path = Path(rows[0]["file_path"])
        if path.exists():
            path.unlink()
    await db.execute("DELETE FROM media_files WHERE id=?", (media_id,))
    await db.commit()
    return {"ok": True}
