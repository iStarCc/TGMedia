from pathlib import Path

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse

from app.database import get_db
from app.models.media import MediaFileResponse, MediaListResponse

router = APIRouter(prefix="/api/media", tags=["media"])


_SORT_COLUMNS = {"filename", "file_size", "created_at"}


@router.get("")
async def list_media(
    media_type: str | None = None,
    search: str | None = None,
    sort: str | None = None,
    order: str = "desc",
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
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

    offset = (page - 1) * page_size
    rows = await db.execute_fetchall(
        f"SELECT * FROM media_files {where} ORDER BY {sort_col} {sort_dir} LIMIT ? OFFSET ?",
        [*params, page_size, offset],
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
