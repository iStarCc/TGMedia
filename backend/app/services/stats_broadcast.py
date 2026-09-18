from app.database import get_db
from app.ws.manager import ws_manager


async def broadcast_task_stats() -> None:
    db = await get_db()
    counts = await db.execute_fetchall("""
        SELECT
            COUNT(*) as total,
            SUM(CASE WHEN status='downloading' THEN 1 ELSE 0 END) as downloading,
            SUM(CASE WHEN status='pending' THEN 1 ELSE 0 END) as pending
        FROM tasks
    """)
    speed_row = await db.execute_fetchall(
        "SELECT COALESCE(SUM(speed), 0) as s FROM tasks WHERE status='downloading'"
    )
    row = dict(counts[0])
    await ws_manager.broadcast("stats:update", {
        "total_tasks": row["total"],
        "downloading": row["downloading"] or 0,
        "pending": row["pending"] or 0,
        "current_speed": speed_row[0]["s"],
    })
