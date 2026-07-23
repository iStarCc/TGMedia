import asyncio
import logging
import shutil
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel as _BaseModel
from pytdbot import types

from app.config import settings
from app.database import get_db
from app.models.channel import ChannelCreate, ChannelResponse, ChannelUpdate
from app.services.file_manager import get_caption, get_file_size, get_filename, get_media_type
from app.services.telegram import tg_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/channels", tags=["channels"])


class ChannelCreateWithAccount(ChannelCreate):
    account_id: int


@router.get("")
async def list_channels(account_id: int | None = None):
    db = await get_db()
    query = """
        SELECT c.*, a.phone as account_phone, a.first_name as account_name, a.username as account_username
        FROM channels c
        LEFT JOIN accounts a ON c.account_id = a.id
    """
    params: list = []
    if account_id:
        query += " WHERE c.account_id=?"
        params.append(account_id)
    query += " ORDER BY c.created_at DESC"
    rows = await db.execute_fetchall(query, params)
    result = []
    for r in rows:
        d = dict(r)
        account_phone = d.pop("account_phone", None)
        account_name = d.pop("account_name", None)
        account_username = d.pop("account_username", None)
        ch = ChannelResponse(**d)
        ch_dict = ch.model_dump()
        ch_dict["account_label"] = account_name or account_phone or ""
        ch_dict["account_username"] = account_username or ""
        result.append(ch_dict)
    return result


def _channel_photo_path(channel_id: int) -> Path:
    return Path(settings.var_dir) / f"channel_{channel_id}.jpg"


async def _download_channel_photo(client, chat, channel_id: int) -> None:
    try:
        if not chat.photo:
            return
        small_file = chat.photo.small
        if not small_file:
            return
        local_path = await tg_manager.download_file(client, small_file.id)
        if local_path and Path(local_path).exists():
            dest = _channel_photo_path(channel_id)
            shutil.copy2(local_path, str(dest))
    except Exception as e:
        logger.warning("Failed to download channel photo for %d: %s", channel_id, e)


def _parse_channel_link(link: str) -> str:
    """从链接/用户名中提取 username"""
    link = link.strip()
    if link.startswith("https://t.me/"):
        link = link.removeprefix("https://t.me/")
    elif link.startswith("http://t.me/"):
        link = link.removeprefix("http://t.me/")
    if link.startswith("@"):
        link = link[1:]
    return link.split("/")[0].split("?")[0]


@router.post("")
async def add_channel(req: ChannelCreateWithAccount):
    client = await tg_manager.get_client(req.account_id)
    username = _parse_channel_link(req.link)

    chat = await client.searchPublicChat(username=username)
    if isinstance(chat, types.Error):
        raise HTTPException(400, f"无法找到频道: {chat.message}")

    title = chat.title or username
    chat_username = ""
    if hasattr(chat, "type"):
        ct = chat.type
        if isinstance(ct, types.ChatTypeSupergroup) and ct.supergroup_id:
            sg = await client.getSupergroup(supergroup_id=ct.supergroup_id)
            if not isinstance(sg, types.Error) and sg.usernames:
                chat_username = sg.usernames.editable_username or ""

    db = await get_db()
    try:
        await db.execute(
            """INSERT INTO channels (account_id, telegram_id, title, username)
               VALUES (?, ?, ?, ?)""",
            (req.account_id, chat.id, title, chat_username or username),
        )
        await db.commit()
    except Exception:
        raise HTTPException(409, "该频道已在此账户下订阅")

    row = await db.execute_fetchall(
        "SELECT * FROM channels WHERE account_id=? AND telegram_id=?",
        (req.account_id, chat.id),
    )
    channel = ChannelResponse(**dict(row[0]))
    await _download_channel_photo(client, chat, channel.id)
    return channel


@router.get("/{channel_id}/photo")
async def get_channel_photo(channel_id: int):
    path = _channel_photo_path(channel_id)
    if not path.exists():
        raise HTTPException(404, "频道头像未找到")
    return FileResponse(path, media_type="image/jpeg")


@router.put("/{channel_id}")
async def update_channel(channel_id: int, req: ChannelUpdate):
    db = await get_db()

    should_catchup = False
    if req.auto_download is True:
        row = await db.execute_fetchall(
            "SELECT auto_download FROM channels WHERE id=?", (channel_id,)
        )
        if row and not row[0]["auto_download"]:
            should_catchup = True

    updates = []
    params = []
    for field, value in req.model_dump(exclude_none=True).items():
        updates.append(f"{field}=?")
        params.append(value if not isinstance(value, bool) else int(value))
    if not updates:
        raise HTTPException(400, "没有需要更新的字段")
    params.append(channel_id)
    await db.execute(
        f"UPDATE channels SET {', '.join(updates)}, updated_at=datetime('now') WHERE id=?",
        params,
    )
    await db.commit()

    if should_catchup:
        asyncio.create_task(_catchup_download(channel_id))

    return {"ok": True}


async def _catchup_download(channel_id: int):
    """开启自动下载时，补下载符合条件的历史消息"""
    from app.services.downloader import download_engine

    try:
        channel, client = await _get_channel_and_client(channel_id)
        chat_id = channel["telegram_id"]
        import json as _json
        from datetime import datetime, timedelta, timezone

        ch_sync_limit = channel.get("sync_limit", 0)
        media_limit = ch_sync_limit or settings.sync_limit or 100

        offset_date = 0
        if settings.sync_days > 0:
            dt = datetime.now(timezone.utc) - timedelta(days=settings.sync_days)
            offset_date = int(dt.timestamp())

        ext_str = channel.get("allowed_extensions", "")
        allowed_exts = _json.loads(ext_str) if ext_str else settings.allowed_extensions
        ch_filter = channel.get("filter_type", "all")

        open_result = await client.openChat(chat_id=chat_id)
        if isinstance(open_result, types.Error):
            logger.warning("catchup openChat failed for %d: %s", chat_id, open_result.message)

        try:
            from_message_id = 0
            max_raw_batches = media_limit * 5
            batch_idx = 0
            submitted = 0

            while submitted < media_limit and max_raw_batches > 0:
                result = await client.getChatHistory(
                    chat_id=chat_id,
                    from_message_id=from_message_id,
                    offset=0,
                    limit=100,
                    only_local=False,
                )
                if isinstance(result, types.Error) or not result.messages:
                    break

                for msg in result.messages:
                    if offset_date and hasattr(msg, "date") and msg.date and msg.date < offset_date:
                        return

                    matched = _match_media_filter(msg, ch_filter, allowed_exts)
                    if matched:
                        media_type, _ = matched
                        if channel.get("max_file_size", 0) > 0:
                            fsize = get_file_size(msg)
                            if fsize > channel["max_file_size"]:
                                continue
                        task_id = await download_engine.submit(
                            msg, channel_id, media_type,
                            account_id=channel["acc_id"], force=False,
                        )
                        if task_id:
                            submitted += 1
                        if submitted >= media_limit:
                            break

                from_message_id = result.messages[-1].id
                max_raw_batches -= len(result.messages)
                batch_idx += 1
                if len(result.messages) < 100:
                    break
        finally:
            await client.closeChat(chat_id=chat_id)

        logger.info("Catchup download for channel %d: submitted %d tasks", channel_id, submitted)
    except Exception as e:
        logger.error("Catchup download failed for channel %d: %s", channel_id, e)


@router.delete("/{channel_id}")
async def delete_channel(channel_id: int):
    db = await get_db()
    await db.execute("DELETE FROM channels WHERE id=?", (channel_id,))
    await db.commit()
    return {"ok": True}


async def _get_channel_and_client(channel_id: int):
    db = await get_db()
    rows = await db.execute_fetchall(
        "SELECT c.*, a.id as acc_id FROM channels c JOIN accounts a ON c.account_id=a.id WHERE c.id=?",
        (channel_id,),
    )
    if not rows:
        raise HTTPException(404, "频道不存在")
    channel = dict(rows[0])
    client = await tg_manager.get_client(channel["acc_id"])
    return channel, client


def _match_media_filter(msg, ch_filter: str, allowed_exts: list[str]) -> tuple[str, str] | None:
    """检查消息是否符合媒体过滤条件，返回 (media_type, filename) 或 None"""
    media_type = get_media_type(msg)
    if not media_type:
        return None
    if ch_filter != "all" and media_type != ch_filter:
        return None
    fname = get_filename(msg)
    if allowed_exts:
        if not fname:
            return None
        ext = fname.rsplit(".", 1)[-1].lower() if "." in fname else ""
        if not ext or ext not in allowed_exts:
            return None
    return media_type, fname or f"{media_type}_{msg.id}"


async def _get_chat_history_batch(
    client,
    chat_id: int,
    from_message_id: int = 0,
    limit: int = 100,
):
    result = await client.getChatHistory(
        chat_id=chat_id,
        from_message_id=from_message_id,
        offset=0,
        limit=limit,
        only_local=False,
    )
    if isinstance(result, types.Error):
        logger.warning("getChatHistory error for chat %d: %s", chat_id, result.message)
        return result
    return result


async def _warmup_chat_history(
    client,
    chat_id: int,
    from_message_id: int = 0,
    limit: int = 100,
    *,
    min_messages: int = 50,
    max_attempts: int = 6,
):
    """冷缓存预热：多次重试直到拿到足够消息"""
    best_result = None
    best_count = 0

    for attempt in range(max_attempts):
        result = await _get_chat_history_batch(client, chat_id, from_message_id, limit)
        if isinstance(result, types.Error):
            if attempt < max_attempts - 1:
                await asyncio.sleep(2 + attempt)
                continue
            return result

        count = len(result.messages) if result.messages else 0
        if count > best_count:
            best_result = result
            best_count = count

        if count >= min(min_messages, limit):
            logger.info("Chat %d warmup ok: %d messages on attempt %d", chat_id, count, attempt)
            return result

        if count == 0 and attempt >= 2:
            break

        logger.info(
            "Chat %d cold cache: attempt %d got %d messages, retrying...",
            chat_id, attempt, count,
        )
        await asyncio.sleep(2 + attempt)

    return best_result


def _match_search_message(msg, req: "SearchRequest", keyword_lower: str) -> dict | None:
    from datetime import datetime, timezone

    media_type = get_media_type(msg)
    if not media_type:
        return None
    if req.media_type != "all" and media_type != req.media_type:
        return None

    fname = get_filename(msg)
    caption = get_caption(msg)

    if req.extensions:
        ext = fname.rsplit(".", 1)[-1].lower() if fname and "." in fname else ""
        if not ext or ext not in req.extensions:
            return None

    if keyword_lower:
        display_name = (fname or f"{media_type}_{msg.id}").lower()
        if keyword_lower not in display_name:
            return None

    return {
        "message_id": msg.id,
        "date": datetime.fromtimestamp(msg.date, tz=timezone.utc).isoformat() if msg.date else "",
        "media_type": media_type,
        "filename": fname or f"{media_type}_{msg.id}",
        "file_size": get_file_size(msg),
        "text": caption,
    }


async def _scan_channel_messages(
    client,
    channel: dict,
    req: "SearchRequest",
    keyword_lower: str,
    from_msg_id: int = 0,
):
    """扫描频道最近 N 条消息并筛选媒体，返回 (matched, last_msg_id, exhausted, raw_scanned)"""
    chat_id = channel["telegram_id"]
    ch_id = channel["id"]
    matched: list[dict] = []
    current_from = from_msg_id
    message_limit = req.per_channel_limit
    last_msg_id = from_msg_id
    exhausted = False
    raw_scanned = 0
    batch_idx = 0

    while raw_scanned < message_limit:
        if batch_idx == 0 and current_from == 0:
            result = await _warmup_chat_history(client, chat_id, current_from)
        else:
            result = await _get_chat_history_batch(client, chat_id, current_from)

        if isinstance(result, types.Error) or not result.messages:
            exhausted = True
            break

        raw_count = len(result.messages)

        for msg in result.messages:
            raw_scanned += 1
            item = _match_search_message(msg, req, keyword_lower)
            if item:
                item["channel_id"] = ch_id
                item["channel_title"] = channel["title"]
                matched.append(item)
            if raw_scanned >= message_limit:
                break

        last_msg_id = result.messages[-1].id
        current_from = last_msg_id
        batch_idx += 1

        if raw_count < 100:
            exhausted = True
            break

    return matched, last_msg_id, exhausted, raw_scanned


@router.post("/{channel_id}/sync")
async def sync_channel(channel_id: int, limit: int | None = None):
    """同步频道消息并返回过滤后的媒体预览列表"""
    import json as _json
    from datetime import datetime, timedelta, timezone

    channel, client = await _get_channel_and_client(channel_id)
    chat_id = channel["telegram_id"]

    ch_sync_limit = channel.get("sync_limit", 0)
    media_limit = limit if limit is not None else (ch_sync_limit or settings.sync_limit or 100)

    offset_date = 0
    if settings.sync_days > 0:
        dt = datetime.now(timezone.utc) - timedelta(days=settings.sync_days)
        offset_date = int(dt.timestamp())

    ext_str = channel.get("allowed_extensions", "")
    allowed_exts = _json.loads(ext_str) if ext_str else settings.allowed_extensions
    ch_filter = channel.get("filter_type", "all")

    open_result = await client.openChat(chat_id=chat_id)
    if isinstance(open_result, types.Error):
        logger.warning("openChat failed for %d: %s", chat_id, open_result.message)

    try:
        messages = []
        from_message_id = 0
        max_raw_batches = media_limit * 5
        batch_idx = 0

        while len(messages) < media_limit and max_raw_batches > 0:
            result = await client.getChatHistory(
                chat_id=chat_id,
                from_message_id=from_message_id,
                offset=0,
                limit=100,
                only_local=False,
            )
            if isinstance(result, types.Error):
                logger.warning("getChatHistory error for chat %d: %s", chat_id, result.message)
                break
            if not result.messages:
                if batch_idx == 0:
                    logger.info("Cold cache detected, retrying after delay...")
                    await asyncio.sleep(2)
                    result = await client.getChatHistory(
                        chat_id=chat_id,
                        from_message_id=0,
                        offset=0,
                        limit=100,
                        only_local=False,
                    )
                    if isinstance(result, types.Error) or not result.messages:
                        break
                else:
                    break

            raw_count = len(result.messages)

            if batch_idx == 0 and raw_count < 10:
                logger.info("Cold cache: only %d messages, retrying after delay...", raw_count)
                await asyncio.sleep(2)
                retry = await client.getChatHistory(
                    chat_id=chat_id,
                    from_message_id=0,
                    offset=0,
                    limit=100,
                    only_local=False,
                )
                if not isinstance(retry, types.Error) and retry.messages and len(retry.messages) > raw_count:
                    result = retry
                    raw_count = len(result.messages)
                    logger.info("Retry got %d messages", raw_count)

            media_in_batch = 0
            for msg in result.messages:
                if offset_date and hasattr(msg, "date") and msg.date and msg.date < offset_date:
                    logger.info("Reached offset_date limit, stopping")
                    return {"total": len(messages), "messages": messages}

                matched = _match_media_filter(msg, ch_filter, allowed_exts)
                if matched:
                    media_type, fname = matched
                    messages.append({
                        "message_id": msg.id,
                        "date": datetime.fromtimestamp(msg.date, tz=timezone.utc).isoformat() if msg.date else "",
                        "media_type": media_type,
                        "filename": fname,
                        "file_size": get_file_size(msg),
                        "text": get_caption(msg),
                    })
                    media_in_batch += 1
                    if len(messages) >= media_limit:
                        break

            logger.info(
                "getChatHistory batch %d: raw=%d, media_matched=%d, total_media=%d",
                batch_idx, raw_count, media_in_batch, len(messages),
            )

            from_message_id = result.messages[-1].id
            max_raw_batches -= raw_count
            batch_idx += 1
            if raw_count < 100:
                break
    finally:
        await client.closeChat(chat_id=chat_id)

    if messages:
        msg_ids = [m["message_id"] for m in messages]
        placeholders = ",".join("?" * len(msg_ids))
        db = await get_db()
        rows = await db.execute_fetchall(
            f"SELECT message_id, status FROM tasks WHERE channel_id=? AND message_id IN ({placeholders})",
            [channel_id, *msg_ids],
        )
        downloaded_set = {r["message_id"] for r in rows}
        for m in messages:
            m["downloaded"] = m["message_id"] in downloaded_set

    return {"total": len(messages), "messages": messages}


class SearchRequest(_BaseModel):
    keyword: str = ""
    media_type: str = "all"
    extensions: list[str] = []
    account_id: int | None = None
    channel_id: int | None = None
    per_channel_limit: int = 50
    cursors: dict[str, int] = {}


@router.post("/search")
async def search_channels(req: SearchRequest):
    """跨所有订阅频道搜索媒体消息"""
    db = await get_db()
    query = (
        "SELECT c.id, c.telegram_id, c.title, c.account_id, a.id as acc_id "
        "FROM channels c JOIN accounts a ON c.account_id=a.id"
    )
    conditions: list[str] = []
    params: list = []
    if req.channel_id:
        conditions.append("c.id=?")
        params.append(req.channel_id)
    elif req.account_id:
        conditions.append("c.account_id=?")
        params.append(req.account_id)
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    rows = await db.execute_fetchall(query, params)
    if not rows:
        return {"results": [], "cursors": {}, "has_more": False}

    results: list[dict] = []
    new_cursors: dict[str, int] = {}
    has_more = False
    keyword_lower = req.keyword.strip().lower()

    by_account: dict[int, list[dict]] = {}
    for row in rows:
        ch = dict(row)
        acc_id = ch["acc_id"]
        cursor_val = req.cursors.get(str(ch["id"]), 0)
        if cursor_val == -1:
            new_cursors[str(ch["id"])] = -1
            continue
        by_account.setdefault(acc_id, []).append(ch)

    for acc_id, channels in by_account.items():
        try:
            client = await tg_manager.get_client(acc_id)
        except Exception as e:
            logger.warning("Search: failed to get client for account %d: %s", acc_id, e)
            continue

        for channel in channels:
            ch_id = channel["id"]
            chat_id = channel["telegram_id"]
            from_msg_id = req.cursors.get(str(ch_id), 0)

            try:
                await client.openChat(chat_id=chat_id)
            except Exception:
                pass

            try:
                matched, last_msg_id, exhausted, raw_scanned = await _scan_channel_messages(
                    client, channel, req, keyword_lower, from_msg_id,
                )

                if not matched and from_msg_id == 0 and raw_scanned < 100:
                    logger.info(
                        "Search channel %d: 0 matches with %d raw messages, rescanning after warmup...",
                        ch_id, raw_scanned,
                    )
                    await asyncio.sleep(3)
                    matched, last_msg_id, exhausted, raw_scanned = await _scan_channel_messages(
                        client, channel, req, keyword_lower, 0,
                    )

                new_cursors[str(ch_id)] = -1 if exhausted else last_msg_id
                if not exhausted:
                    has_more = True

                results.extend(matched)
            except Exception as e:
                logger.warning("Search: error scanning channel %d: %s", ch_id, e)
            finally:
                try:
                    await client.closeChat(chat_id=chat_id)
                except Exception:
                    pass

    if results:
        by_ch: dict[int, list[int]] = {}
        for r in results:
            by_ch.setdefault(r["channel_id"], []).append(r["message_id"])

        downloaded_set: set[tuple[int, int]] = set()
        for c_id, msg_ids in by_ch.items():
            placeholders = ",".join("?" * len(msg_ids))
            task_rows = await db.execute_fetchall(
                f"SELECT message_id FROM tasks WHERE channel_id=? AND message_id IN ({placeholders})",
                [c_id, *msg_ids],
            )
            for r in task_rows:
                downloaded_set.add((c_id, r["message_id"]))

        for r in results:
            r["downloaded"] = (r["channel_id"], r["message_id"]) in downloaded_set

    results.sort(key=lambda x: x.get("date", ""), reverse=True)

    return {"results": results, "cursors": new_cursors, "has_more": has_more}


class DownloadRequest(_BaseModel):
    message_ids: list[int]
    force: bool = False


@router.post("/{channel_id}/download")
async def download_messages(channel_id: int, req: DownloadRequest):
    """下载指定消息到本地"""
    from app.services.downloader import download_engine

    channel, client = await _get_channel_and_client(channel_id)
    chat_id = channel["telegram_id"]

    submitted = 0
    skipped = 0
    for msg_id in req.message_ids:
        try:
            message = await client.getMessage(chat_id=chat_id, message_id=msg_id)
            if isinstance(message, types.Error):
                continue
            media_type = get_media_type(message)
            if not media_type:
                continue
            task_id = await download_engine.submit(
                message, channel_id, media_type,
                account_id=channel["acc_id"], force=req.force,
            )
            if task_id:
                submitted += 1
            else:
                skipped += 1
        except Exception as e:
            logger.warning("Failed to submit msg %d: %s", msg_id, e)

    return {"submitted": submitted, "skipped": skipped}
