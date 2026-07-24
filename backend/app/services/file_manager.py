from datetime import datetime
import re
from pathlib import Path

from pytdbot import types

from app.config import settings


def get_media_type(message) -> str | None:
    """从 TDLib message 推断媒体类型"""
    content = message.content if hasattr(message, "content") else None
    if not content:
        return None
    if isinstance(content, types.MessagePhoto):
        return "photo"
    if isinstance(content, types.MessageVideo):
        return "video"
    if isinstance(content, types.MessageAudio):
        return "audio"
    if isinstance(content, types.MessageAnimation):
        return "document"
    if isinstance(content, types.MessageDocument):
        mime = content.document.mime_type or "" if content.document else ""
        if mime.startswith("video"):
            return "video"
        if mime.startswith("audio"):
            return "audio"
        return "document"
    if isinstance(content, types.MessageVoiceNote):
        return "audio"
    if isinstance(content, types.MessageVideoNote):
        return "video"
    return None


def get_file_from_message(message) -> types.File | None:
    """从 TDLib message 提取 File 对象"""
    content = message.content if hasattr(message, "content") else None
    if not content:
        return None
    if isinstance(content, types.MessagePhoto) and content.photo:
        sizes = content.photo.sizes
        if sizes:
            return sizes[-1].photo
    if isinstance(content, types.MessageVideo) and content.video:
        return content.video.video
    if isinstance(content, types.MessageAudio) and content.audio:
        return content.audio.audio
    if isinstance(content, types.MessageDocument) and content.document:
        return content.document.document
    if isinstance(content, types.MessageAnimation) and content.animation:
        return content.animation.animation
    if isinstance(content, types.MessageVoiceNote) and content.voice_note:
        return content.voice_note.voice
    if isinstance(content, types.MessageVideoNote) and content.video_note:
        return content.video_note.video
    return None


def get_filename(message) -> str:
    """从 TDLib message 提取文件名"""
    content = message.content if hasattr(message, "content") else None
    if not content:
        return ""
    if isinstance(content, types.MessageDocument) and content.document:
        return content.document.file_name or ""
    if isinstance(content, types.MessageVideo) and content.video:
        return content.video.file_name or ""
    if isinstance(content, types.MessageAudio) and content.audio:
        return content.audio.file_name or ""
    if isinstance(content, types.MessageAnimation) and content.animation:
        return content.animation.file_name or ""
    return ""


def get_caption(message) -> str:
    """从 TDLib message 提取 caption 文本"""
    content = message.content if hasattr(message, "content") else None
    if not content:
        return ""
    caption = getattr(content, "caption", None)
    if caption and hasattr(caption, "text"):
        return caption.text or ""
    return ""


def get_file_size(message) -> int:
    """从 TDLib message 提取文件大小"""
    f = get_file_from_message(message)
    if f:
        return f.expected_size or f.size or 0
    return 0


def make_download_filename(message, media_type: str) -> str:
    """生成下载文件名，追加时间戳后缀防止重复"""
    name = get_filename(message)
    if not name:
        ext_map = {"photo": ".jpg", "video": ".mp4", "audio": ".mp3", "document": ""}
        ext = ext_map.get(media_type, "")
        msg_id = message.id if hasattr(message, "id") else 0
        name = f"{media_type}_{msg_id}{ext}"

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = Path(name)
    return f"{path.stem}_{ts}{path.suffix}"


def sanitize_dirname(name: str) -> str:
    """将频道名转为安全的目录名"""
    cleaned = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", name.strip())
    cleaned = re.sub(r"\s+", " ", cleaned).strip(". ")
    return (cleaned or "unknown")[:100]


async def resolve_download_dir(channel_id: int | None, media_type: str) -> Path:
    """解析下载目录，支持频道自定义路径与按频道分子目录"""
    from app.config import settings
    from app.database import get_db

    base = settings.download_dir
    channel_title = ""

    if channel_id:
        db = await get_db()
        rows = await db.execute_fetchall(
            "SELECT title, download_path, download_by_channel, download_by_media_type FROM channels WHERE id=?",
            (channel_id,),
        )
        if rows:
            channel_title = rows[0]["title"] or ""
            ch_path = rows[0]["download_path"] or ""
            if ch_path:
                base = Path(ch_path)
                base.mkdir(parents=True, exist_ok=True)
            ch_by_channel = rows[0]["download_by_channel"] or 0
            if ch_by_channel == 1:
                use_channel_dir = True
            elif ch_by_channel == 2:
                use_channel_dir = False
            else:
                use_channel_dir = settings.download_by_channel
            ch_by_media = rows[0]["download_by_media_type"] or 0
            if ch_by_media == 1:
                use_media_dir = True
            elif ch_by_media == 2:
                use_media_dir = False
            else:
                use_media_dir = settings.download_by_media_type
        else:
            use_channel_dir = settings.download_by_channel
            use_media_dir = settings.download_by_media_type
    else:
        use_channel_dir = settings.download_by_channel
        use_media_dir = settings.download_by_media_type

    if use_channel_dir and channel_id:
        folder = sanitize_dirname(channel_title or f"channel_{channel_id}")
        base = base / folder

    if use_media_dir:
        sub_dir = base / media_type
        sub_dir.mkdir(parents=True, exist_ok=True)
        return sub_dir

    base.mkdir(parents=True, exist_ok=True)
    return base


def ensure_dirs() -> None:
    """确保媒体子目录存在"""
    if not settings.download_by_media_type:
        settings.download_dir.mkdir(parents=True, exist_ok=True)
        return
    for sub in ("photo", "video", "audio", "document"):
        (settings.download_dir / sub).mkdir(parents=True, exist_ok=True)
