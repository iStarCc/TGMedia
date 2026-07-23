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

    async def broadcast_progress(self, task_id: str, data: dict) -> None:
        """节流推送下载进度，避免洪泛"""
        now = time.monotonic()
        throttle = settings.ws_throttle_ms / 1000
        last = self._last_progress.get(task_id, 0)
        if now - last < throttle:
            return
        self._last_progress[task_id] = now
        await self.broadcast("task:progress", data)

    def clear_progress_cache(self, task_id: str) -> None:
        self._last_progress.pop(task_id, None)


ws_manager = WSManager()
