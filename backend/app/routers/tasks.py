import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel as _BaseModel
from pytdbot import types

from app.database import get_db
from app.models.task import TaskListResponse, TaskResponse
from app.services.downloader import download_engine
from app.services.file_manager import get_media_type

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


@router.get("")
async def list_tasks(
    status: str | None = None,
    search: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=0, le=10000),
) -> TaskListResponse:
    db = await get_db()
    conditions = []
    params: list = []

    if status:
        conditions.append("status=?")
        params.append(status)
    if search:
        conditions.append("filename LIKE ?")
        params.append(f"%{search}%")

    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    total_row = await db.execute_fetchall(f"SELECT COUNT(*) as cnt FROM tasks {where}", params)
    total = total_row[0]["cnt"]

    offset = (page - 1) * page_size if page_size > 0 else 0
    if page_size > 0:
        rows = await db.execute_fetchall(
            f"SELECT * FROM tasks {where} ORDER BY created_at DESC LIMIT ? OFFSET ?",
            [*params, page_size, offset],
        )
    else:
        rows = await db.execute_fetchall(
            f"SELECT * FROM tasks {where} ORDER BY created_at DESC",
            params,
        )
    tasks = [TaskResponse(**dict(r)) for r in rows]
    return TaskListResponse(tasks=tasks, total=total)


@router.post("/{task_id}/pause")
async def pause_task(task_id: str):
    await download_engine.pause(task_id)
    return {"ok": True}


@router.post("/{task_id}/resume")
async def resume_task(task_id: str):
    """恢复下载：重新获取 Telegram 消息并重新提交下载"""
    db = await get_db()
    rows = await db.execute_fetchall(
        "SELECT * FROM tasks WHERE id=? AND status IN ('paused', 'failed', 'completed')",
        (task_id,),
    )
    if not rows:
        raise HTTPException(404, "任务不存在或状态不可恢复")

    task = dict(rows[0])
    channel_id = task["channel_id"]
    message_id = task["message_id"]
    account_id = task.get("account_id")
    chat_id = task.get("chat_id")
    is_redownload = task["status"] == "completed"

    if not channel_id or not message_id:
        raise HTTPException(400, "缺少频道或消息信息，无法恢复")

    ch_rows = await db.execute_fetchall(
        "SELECT telegram_id, account_id FROM channels WHERE id=?", (channel_id,)
    )
    if not ch_rows:
        raise HTTPException(404, "频道不存在")

    acc_id = account_id or ch_rows[0]["account_id"]
    tg_chat_id = chat_id or ch_rows[0]["telegram_id"]
    from app.services.telegram import tg_manager

    try:
        client = await tg_manager.get_client(acc_id)
        message = await client.getMessage(chat_id=tg_chat_id, message_id=message_id)

        if isinstance(message, types.Error):
            raise HTTPException(400, f"无法获取消息: {message.message}")

        media_type = get_media_type(message)
        if not media_type:
            raise HTTPException(400, "原始消息已被删除或不含媒体")

        await db.execute("DELETE FROM media_files WHERE task_id=?", (task_id,))
        await db.execute("DELETE FROM tasks WHERE id=?", (task_id,))
        await db.commit()

        new_id = await download_engine.submit(
            message, channel_id, task["media_type"],
            account_id=acc_id, force=is_redownload,
        )
        return {"ok": True, "new_task_id": new_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Resume failed for task %s", task_id)
        raise HTTPException(500, f"恢复失败: {e}")


@router.post("/{task_id}/retry")
async def retry_task(task_id: str):
    return await resume_task(task_id)


@router.delete("/{task_id}")
async def delete_task(task_id: str, delete_file: bool = False):
    await download_engine.pause(task_id)
    db = await get_db()
    if delete_file:
        await _delete_task_files(db, task_id)
    await db.execute("DELETE FROM media_files WHERE task_id=?", (task_id,))
    await db.execute("DELETE FROM tasks WHERE id=?", (task_id,))
    await db.commit()
    return {"ok": True}


async def _delete_task_files(db, task_id: str):
    rows = await db.execute_fetchall(
        "SELECT file_path FROM tasks WHERE id=? AND file_path IS NOT NULL", (task_id,)
    )
    media_rows = await db.execute_fetchall(
        "SELECT file_path FROM media_files WHERE task_id=?", (task_id,)
    )
    for r in [*rows, *media_rows]:
        p = Path(r["file_path"]) if r["file_path"] else None
        if p and p.exists():
            p.unlink(missing_ok=True)
            logger.info("Deleted file: %s", p)


class BatchDeleteRequest(_BaseModel):
    task_ids: list[str]
    delete_file: bool = False


@router.post("/batch/pause")
async def batch_pause(task_ids: list[str]):
    for tid in task_ids:
        await download_engine.pause(tid)
    return {"ok": True, "count": len(task_ids)}


@router.post("/batch/delete")
async def batch_delete(req: BatchDeleteRequest):
    db = await get_db()
    for tid in req.task_ids:
        await download_engine.pause(tid)
        if req.delete_file:
            await _delete_task_files(db, tid)
        await db.execute("DELETE FROM media_files WHERE task_id=?", (tid,))
        await db.execute("DELETE FROM tasks WHERE id=?", (tid,))
    await db.commit()
    return {"ok": True, "count": len(req.task_ids)}


@router.post("/batch/retry")
async def batch_retry(task_ids: list[str]):
    results = {"ok": 0, "failed": 0}
    for tid in task_ids:
        try:
            await resume_task(tid)
            results["ok"] += 1
        except Exception:
            results["failed"] += 1
    return results
