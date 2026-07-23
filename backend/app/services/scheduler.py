import asyncio
import logging

from pytdbot import Client, types

from app.config import settings
from app.database import get_db
from app.services.downloader import download_engine
from app.services.file_manager import get_filename, get_file_size, get_media_type
from app.services.telegram import tg_manager
from app.ws.manager import ws_manager

logger = logging.getLogger(__name__)

_listening_accounts: set[int] = set()


async def _get_subscribed_channels(account_id: int) -> dict[int, int]:
    """获取某账户下已订阅且开启自动下载的频道 {telegram_id: db_id}"""
    db = await get_db()
    rows = await db.execute_fetchall(
        "SELECT id, telegram_id FROM channels WHERE account_id=? AND auto_download=1",
        (account_id,),
    )
    return {r["telegram_id"]: r["id"] for r in rows}


async def _should_download(message, channel_id: int, media_type: str) -> bool:
    import json as _json

    db = await get_db()
    rows = await db.execute_fetchall(
        "SELECT filter_type, max_file_size, allowed_extensions FROM channels WHERE id=?",
        (channel_id,),
    )
    if not rows:
        return True

    channel = dict(rows[0])

    if channel["filter_type"] != "all" and media_type != channel["filter_type"]:
        return False

    if channel["max_file_size"] > 0:
        file_size = get_file_size(message)
        if file_size > channel["max_file_size"]:
            return False

    ext_str = channel.get("allowed_extensions", "")
    exts = _json.loads(ext_str) if ext_str else settings.allowed_extensions
    if exts:
        fname = get_filename(message)
        if not fname:
            return False
        ext = fname.rsplit(".", 1)[-1].lower() if "." in fname else ""
        if not ext or ext not in exts:
            return False

    return True


async def _setup_listener_for_account(account_id: int) -> None:
    """为单个账户设置事件监听"""
    if account_id in _listening_accounts:
        return

    try:
        client = await tg_manager.get_client(account_id)
        if not client.is_authenticated:
            logger.warning("Account %d not authorized, skipping", account_id)
            return
    except Exception as e:
        logger.error("Cannot connect account %d: %s", account_id, e)
        return

    _listening_accounts.add(account_id)
    logger.info("Event listener started for account %d", account_id)

    async def on_new_message(_c: Client, update: types.UpdateNewMessage):
        message = update.message
        if not message or not hasattr(message, "content"):
            return

        media_type = get_media_type(message)
        if not media_type:
            return

        chat_id = message.chat_id

        subscribed = await _get_subscribed_channels(account_id)
        if chat_id not in subscribed:
            return

        channel_db_id = subscribed[chat_id]

        if not await _should_download(message, channel_db_id, media_type):
            return

        task_id = await download_engine.submit(
            message, channel_db_id, media_type, account_id=account_id
        )
        if not task_id:
            return

        logger.info(
            "Auto-downloading msg %d from chat %d via account %d (type: %s)",
            message.id, chat_id, account_id, media_type,
        )
        await ws_manager.broadcast("channel:new_message", {
            "channel_id": channel_db_id,
            "message_id": message.id,
            "media_type": media_type,
        })

    client.add_handler("updateNewMessage", on_new_message)


async def start_event_listener() -> None:
    """为所有已登录账户启动事件监听"""
    db = await get_db()
    rows = await db.execute_fetchall("SELECT id FROM accounts WHERE is_active=1")
    for row in rows:
        await _setup_listener_for_account(row["id"])


async def stop_event_listener() -> None:
    _listening_accounts.clear()
    logger.info("All event listeners stopped")


async def start_stats_broadcaster() -> None:
    """定期广播统计数据到 WebSocket 客户端"""
    while True:
        await asyncio.sleep(5)
        if not ws_manager.connections:
            continue
        try:
            db = await get_db()
            speed_row = await db.execute_fetchall(
                "SELECT COALESCE(SUM(speed), 0) as s FROM tasks WHERE status='downloading'"
            )
            count_row = await db.execute_fetchall(
                "SELECT COUNT(*) as c FROM tasks WHERE status='downloading'"
            )
            await ws_manager.broadcast("stats:update", {
                "current_speed": speed_row[0]["s"],
                "downloading": count_row[0]["c"],
            })
        except Exception:
            pass


async def start_cache_cleaner(interval_hours: int = 6) -> None:
    """定期清理 TDLib 缓存文件"""
    await asyncio.sleep(60)
    while True:
        try:
            await _cleanup_tdlib_cache()
        except Exception as e:
            logger.error("Cache cleanup failed: %s", e)
        await asyncio.sleep(interval_hours * 3600)


async def _cleanup_tdlib_cache() -> None:
    """调用各客户端的 optimizeStorage 清理过期缓存"""
    from pathlib import Path

    clients = tg_manager.get_all_clients()
    if not clients:
        return

    for account_id, client in clients.items():
        try:
            result = await client.optimizeStorage(
                size=-1,
                ttl=3600,
                count=-1,
                immunity_delay=3600,
                chat_ids=[],
                exclude_chat_ids=[],
                return_deleted_file_statistics=False,
                chat_limit=0,
            )
            if isinstance(result, types.Error):
                logger.warning("optimizeStorage error for account %d: %s", account_id, result.message)
            else:
                logger.info("TDLib cache cleanup for account %d completed", account_id)
        except Exception as e:
            logger.warning("optimizeStorage failed for account %d, fallback to manual cleanup: %s", account_id, e)
            _manual_cleanup(account_id)


def _manual_cleanup(account_id: int) -> None:
    """手动清理 TDLib 缓存目录中超过 1 小时的文件"""
    import time
    from pathlib import Path

    cache_dir = Path(settings.var_dir) / f"tdlib_{account_id}"
    if not cache_dir.exists():
        return

    cutoff = time.time() - 3600
    cleaned = 0
    for sub in ("documents", "photos", "videos", "music", "animations", "voice"):
        d = cache_dir / sub
        if not d.is_dir():
            continue
        for f in d.iterdir():
            if f.is_file() and f.stat().st_mtime < cutoff:
                f.unlink(missing_ok=True)
                cleaned += 1

    if cleaned:
        logger.info("Manual cleanup for account %d: removed %d cached files", account_id, cleaned)
