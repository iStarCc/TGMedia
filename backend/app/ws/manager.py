import asyncio
import json
import time
from dataclasses import dataclass, field

from fastapi import WebSocket

from app.config import settings


@dataclass
class WSManager:
    """WebSocket 连接管理器，带事件广播和进度节流"""

    connections: set[WebSocket] = field(default_factory=set)
    _last_progress: dict[str, float] = field(default_factory=dict)
    _pending_progress: dict[str, dict] = field(default_factory=dict)
    _flush_tasks: dict[str, asyncio.Task] = field(default_factory=dict)

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        self.connections.add(ws)

    def disconnect(self, ws: WebSocket) -> None:
        self.connections.discard(ws)

    async def broadcast(self, event: str, data: dict) -> None:
        if not self.connections:
            return
        message = json.dumps({"event": event, "data": data}, default=str)
        dead: list[WebSocket] = []
        for ws in self.connections:
            try:
                await ws.send_text(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.connections.discard(ws)

    async def _flush_progress(self, task_id: str) -> None:
        data = self._pending_progress.pop(task_id, None)
        if not data:
            return
        self._last_progress[task_id] = time.monotonic()
        await self.broadcast("task:progress", data)

    async def broadcast_progress(self, task_id: str, data: dict) -> None:
        """节流推送下载进度，合并期间最新状态并在窗口结束时补发"""
        self._pending_progress[task_id] = data
        now = time.monotonic()
        throttle = settings.ws_throttle_ms / 1000
        last = self._last_progress.get(task_id, 0)

        if now - last >= throttle:
            await self._flush_progress(task_id)
            return

        existing = self._flush_tasks.get(task_id)
        if existing and not existing.done():
            return

        delay = max(throttle - (now - last), 0)

        async def _delayed_flush() -> None:
            await asyncio.sleep(delay)
            await self._flush_progress(task_id)
            self._flush_tasks.pop(task_id, None)

        self._flush_tasks[task_id] = asyncio.create_task(_delayed_flush())

    def clear_progress_cache(self, task_id: str) -> None:
        self._last_progress.pop(task_id, None)
        self._pending_progress.pop(task_id, None)
        flush_task = self._flush_tasks.pop(task_id, None)
        if flush_task and not flush_task.done():
            flush_task.cancel()


ws_manager = WSManager()
