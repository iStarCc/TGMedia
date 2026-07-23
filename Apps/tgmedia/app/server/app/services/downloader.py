import asyncio
import logging
import shutil
import time
import uuid
from collections import deque
from pathlib import Path

from pytdbot import types as td_types

from app.config import settings
from app.database import get_db
from app.services.file_manager import get_file_from_message, get_file_size, make_download_filename, resolve_download_dir
from app.ws.manager import ws_manager

logger = logging.getLogger(__name__)


class SpeedTracker:
    """滑动窗口速度计算器"""

    def __init__(self, window_size: int = 10):
        self._samples: deque[tuple[float, int]] = deque(maxlen=window_size)

    def update(self, current_bytes: int) -> float:
        now = time.monotonic()
        self._samples.append((now, current_bytes))
        if len(self._samples) < 2:
            return 0.0
        dt = self._samples[-1][0] - self._samples[0][0]
        db = self._samples[-1][1] - self._samples[0][1]
        return db / dt if dt > 0 else 0.0


class DownloadEngine:
    def __init__(self):
        self._semaphore: asyncio.Semaphore | None = None
        self._active_tasks: dict[str, asyncio.Task] = {}

    @property
    def semaphore(self) -> asyncio.Semaphore:
        if self._semaphore is None:
            self._semaphore = asyncio.Semaphore(settings.max_concurrent)
        return self._semaphore

    async def submit(
        self, message, channel_id: int, media_type: str,
        account_id: int | None = None, force: bool = False,
    ) -> str | None:
        """提交下载任务，force=False 时跳过已有任务"""
        db = await get_db()
        msg_id = message.id if hasattr(message, "id") else 0
        chat_id = message.chat_id if hasattr(message, "chat_id") else 0

        if msg_id and channel_id:
            rows = await db.execute_fetchall(
                "SELECT id, status FROM tasks WHERE channel_id=? AND message_id=?",
                (channel_id, msg_id),
            )
            if rows:
                if force:
                    task_ids = [r["id"] for r in rows]
                    for tid in task_ids:
                        t = self._active_tasks.pop(tid, None)
                        if t and not t.done():
                            t.cancel()
                    ph = ",".join("?" * len(task_ids))
                    file_rows = await db.execute_fetchall(
                        f"SELECT file_path FROM media_files WHERE task_id IN ({ph})", task_ids,
                    )
                    old_paths = await db.execute_fetchall(
                        f"SELECT file_path FROM tasks WHERE id IN ({ph}) AND file_path IS NOT NULL", task_ids,
                    )
                    for r in [*file_rows, *old_paths]:
                        p = Path(r["file_path"]) if r["file_path"] else None
                        if p and p.exists():
                            p.unlink(missing_ok=True)
                            logger.info("Deleted old file: %s", p)
                    await db.execute(f"DELETE FROM media_files WHERE task_id IN ({ph})", task_ids)
                    await db.execute("DELETE FROM tasks WHERE channel_id=? AND message_id=?", (channel_id, msg_id))
                    await db.commit()
                    logger.info("Force re-download: channel=%d msg=%d (removed %d old tasks + files)", channel_id, msg_id, len(rows))
                else:
                    logger.info("Skip duplicate: channel=%d msg=%d (task %s, %s)", channel_id, msg_id, rows[0]["id"], rows[0]["status"])
                    return None

        task_id = uuid.uuid4().hex[:12]
        filename = make_download_filename(message, media_type)
        file_size = get_file_size(message)

        await db.execute(
            """INSERT INTO tasks (id, account_id, channel_id, message_id, chat_id, filename, file_size, media_type, status)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pending')""",
            (task_id, account_id, channel_id, msg_id, chat_id, filename, file_size, media_type),
        )
        await db.commit()

        await ws_manager.broadcast("task:created", {
            "task_id": task_id,
            "filename": filename,
            "file_size": file_size,
            "media_type": media_type,
            "status": "pending",
        })

        task = asyncio.create_task(
            self._download(task_id, message, filename, media_type, account_id, force)
        )
        self._active_tasks[task_id] = task
        return task_id

    async def pause(self, task_id: str) -> None:
        task = self._active_tasks.get(task_id)
        if task and not task.done():
            task.cancel()
        db = await get_db()
        await db.execute(
            "UPDATE tasks SET status='paused', updated_at=datetime('now') WHERE id=?",
            (task_id,),
        )
        await db.commit()
        await ws_manager.broadcast("task:paused", {"task_id": task_id})

    async def _download(
        self, task_id: str, message, filename: str, media_type: str,
        account_id: int | None = None, force: bool = False,
    ) -> None:
        from app.services.telegram import tg_manager

        async with self.semaphore:
            db = await get_db()
            await db.execute(
                "UPDATE tasks SET status='downloading', started_at=datetime('now'), updated_at=datetime('now') WHERE id=?",
                (task_id,),
            )
            await db.commit()

            tracker = SpeedTracker()

            task_row = await db.execute_fetchall(
                "SELECT channel_id FROM tasks WHERE id=?", (task_id,),
            )
            channel_id = task_row[0]["channel_id"] if task_row else None
            sub_dir = await resolve_download_dir(channel_id, media_type)
            dest = sub_dir / filename

            handler_ref = None

            try:
                if account_id:
                    client = await tg_manager.get_client(account_id)
                else:
                    clients = tg_manager.get_all_clients()
                    if not clients:
                        raise RuntimeError("No Telegram accounts connected")
                    client = next(iter(clients.values()))

                tdlib_file = get_file_from_message(message)
                if not tdlib_file:
                    raise RuntimeError("Message has no downloadable file")

                file_id = tdlib_file.id
                total_size = tdlib_file.expected_size or tdlib_file.size or 0

                if force:
                    del_result = await client.deleteFile(file_id=file_id)
                    if isinstance(del_result, td_types.Error):
                        logger.warning("deleteFile failed for file %d: %s", file_id, del_result.message)

                download_done = asyncio.Event()
                completed_path: list[str] = []

                async def on_file_update(_c, update: td_types.UpdateFile):
                    f = update.file
                    if f.id != file_id:
                        return
                    local = f.local
                    if not local:
                        return

                    current = getattr(local, "downloaded_size", 0) or 0
                    total = f.expected_size or total_size or 1

                    if local.is_downloading_completed:
                        completed_path.clear()
                        if local.path:
                            completed_path.append(local.path)
                        await ws_manager.broadcast_progress(task_id, {
                            "task_id": task_id,
                            "filename": filename,
                            "progress": 1.0,
                            "downloaded": total,
                            "file_size": total,
                            "speed": 0,
                            "eta": 0,
                        })
                        download_done.set()
                        return

                    if getattr(local, "is_downloading_active", False):
                        speed = tracker.update(current)
                        eta = int((total - current) / speed) if speed > 0 else 0
                        await ws_manager.broadcast_progress(task_id, {
                            "task_id": task_id,
                            "filename": filename,
                            "progress": current / total if total else 0,
                            "downloaded": current,
                            "file_size": total,
                            "speed": speed,
                            "eta": eta,
                        })
                        await db.execute(
                            "UPDATE tasks SET downloaded=?, speed=?, updated_at=datetime('now') WHERE id=?",
                            (current, speed, task_id),
                        )
                        await db.commit()

                client.add_handler("updateFile", on_file_update)
                handler_ref = on_file_update

                result = await client.downloadFile(
                    file_id=file_id, priority=32, synchronous=False
                )

                if isinstance(result, td_types.Error):
                    raise RuntimeError(f"Download failed: {result.message}")

                if result.local and result.local.is_downloading_completed:
                    if result.local.path:
                        completed_path.append(result.local.path)
                    download_done.set()

                await asyncio.wait_for(download_done.wait(), timeout=7200)

                src_path = completed_path[0] if completed_path else None
                if not src_path:
                    refreshed = await client.getFile(file_id=file_id)
                    if not isinstance(refreshed, td_types.Error) and refreshed.local:
                        src_path = refreshed.local.path

                if src_path and Path(src_path).exists():
                    shutil.copy2(src_path, str(dest))
                    try:
                        await client.deleteFile(file_id=file_id)
                    except Exception:
                        Path(src_path).unlink(missing_ok=True)
                else:
                    raise RuntimeError("Download completed but file not found in TDLib storage")

                file_size = dest.stat().st_size if dest.exists() else 0
                await db.execute(
                    """UPDATE tasks SET status='completed', downloaded=?, file_size=?,
                       file_path=?, speed=0, updated_at=datetime('now') WHERE id=?""",
                    (file_size, file_size, str(dest), task_id),
                )
                await db.execute(
                    """INSERT INTO media_files (task_id, channel_id, filename, file_path, file_size, media_type)
                       SELECT ?, channel_id, ?, ?, ?, ? FROM tasks WHERE id=?""",
                    (task_id, filename, str(dest), file_size, media_type, task_id),
                )
                await db.commit()

                ws_manager.clear_progress_cache(task_id)
                task_row = await db.execute_fetchall(
                    "SELECT started_at, updated_at FROM tasks WHERE id=?", (task_id,)
                )
                await ws_manager.broadcast("task:completed", {
                    "task_id": task_id,
                    "filename": filename,
                    "file_size": file_size,
                    "started_at": task_row[0]["started_at"] if task_row else None,
                    "updated_at": task_row[0]["updated_at"] if task_row else None,
                })

            except asyncio.CancelledError:
                logger.info("Task %s cancelled (paused)", task_id)
            except Exception as e:
                logger.exception("Task %s failed", task_id)
                await db.execute(
                    "UPDATE tasks SET status='failed', error=?, speed=0, updated_at=datetime('now') WHERE id=?",
                    (str(e), task_id),
                )
                await db.commit()
                ws_manager.clear_progress_cache(task_id)
                await ws_manager.broadcast("task:failed", {
                    "task_id": task_id,
                    "filename": filename,
                    "error": str(e),
                })
            finally:
                if handler_ref:
                    try:
                        client.remove_handler(handler_ref)
                    except Exception:
                        pass
                self._active_tasks.pop(task_id, None)


download_engine = DownloadEngine()
