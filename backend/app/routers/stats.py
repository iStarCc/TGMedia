from fastapi import APIRouter

from app.database import get_db

router = APIRouter(prefix="/api/stats", tags=["stats"])


@router.get("")
async def get_stats():
    db = await get_db()

    counts = await db.execute_fetchall("""
        SELECT
            COUNT(*) as total,
            SUM(CASE WHEN status='downloading' THEN 1 ELSE 0 END) as downloading,
            SUM(CASE WHEN status='completed' THEN 1 ELSE 0 END) as completed,
            SUM(CASE WHEN status='failed' THEN 1 ELSE 0 END) as failed,
            SUM(CASE WHEN status='paused' THEN 1 ELSE 0 END) as paused,
            SUM(CASE WHEN status='pending' THEN 1 ELSE 0 END) as pending
        FROM tasks
    """)

    size_row = await db.execute_fetchall(
        "SELECT COALESCE(SUM(file_size), 0) as total_size FROM media_files"
    )

    speed_row = await db.execute_fetchall(
        "SELECT COALESCE(SUM(speed), 0) as total_speed FROM tasks WHERE status='downloading'"
    )

    channel_count = await db.execute_fetchall("SELECT COUNT(*) as cnt FROM channels")
    account_count = await db.execute_fetchall("SELECT COUNT(*) as cnt FROM accounts WHERE is_active=1")

    row = dict(counts[0])
    return {
        "total_tasks": row["total"],
        "downloading": row["downloading"] or 0,
        "completed": row["completed"] or 0,
        "failed": row["failed"] or 0,
        "paused": row["paused"] or 0,
        "pending": row["pending"] or 0,
        "total_size": size_row[0]["total_size"],
        "current_speed": speed_row[0]["total_speed"],
        "channel_count": channel_count[0]["cnt"],
        "account_count": account_count[0]["cnt"],
    }
