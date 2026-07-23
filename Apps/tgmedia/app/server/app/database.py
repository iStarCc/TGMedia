import aiosqlite

from app.config import settings

_db: aiosqlite.Connection | None = None

SCHEMA = """
CREATE TABLE IF NOT EXISTS accounts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    phone TEXT UNIQUE NOT NULL,
    api_id INTEGER NOT NULL,
    api_hash TEXT NOT NULL,
    telegram_id INTEGER,
    first_name TEXT DEFAULT '',
    last_name TEXT DEFAULT '',
    username TEXT DEFAULT '',
    session_file TEXT NOT NULL,
    is_active INTEGER DEFAULT 1,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS channels (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id INTEGER REFERENCES accounts(id) ON DELETE CASCADE,
    telegram_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    username TEXT,
    photo_url TEXT,
    auto_download INTEGER DEFAULT 0,
    filter_type TEXT DEFAULT 'all',
    max_file_size INTEGER DEFAULT 0,
    allowed_extensions TEXT DEFAULT '',
    download_path TEXT DEFAULT '',
    sync_limit INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now')),
    UNIQUE(account_id, telegram_id)
);

CREATE TABLE IF NOT EXISTS tasks (
    id TEXT PRIMARY KEY,
    account_id INTEGER REFERENCES accounts(id),
    channel_id INTEGER REFERENCES channels(id),
    message_id INTEGER,
    chat_id INTEGER DEFAULT 0,
    filename TEXT NOT NULL,
    file_size INTEGER DEFAULT 0,
    downloaded INTEGER DEFAULT 0,
    media_type TEXT NOT NULL,
    status TEXT DEFAULT 'pending',
    speed REAL DEFAULT 0,
    error TEXT,
    file_path TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS media_files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id TEXT REFERENCES tasks(id),
    channel_id INTEGER REFERENCES channels(id),
    filename TEXT NOT NULL,
    file_path TEXT NOT NULL,
    file_size INTEGER DEFAULT 0,
    media_type TEXT NOT NULL,
    thumbnail_path TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_tasks_channel ON tasks(channel_id);
CREATE INDEX IF NOT EXISTS idx_tasks_account ON tasks(account_id);
CREATE INDEX IF NOT EXISTS idx_media_type ON media_files(media_type);
CREATE INDEX IF NOT EXISTS idx_media_channel ON media_files(channel_id);
CREATE INDEX IF NOT EXISTS idx_channels_account ON channels(account_id);
"""


_MIGRATIONS = [
    ("channels", "allowed_extensions", "TEXT DEFAULT ''"),
    ("channels", "download_path", "TEXT DEFAULT ''"),
    ("channels", "sync_limit", "INTEGER DEFAULT 0"),
    ("accounts", "api_id", "INTEGER NOT NULL DEFAULT 0"),
    ("accounts", "api_hash", "TEXT NOT NULL DEFAULT ''"),
    ("tasks", "chat_id", "INTEGER DEFAULT 0"),
    ("tasks", "started_at", "TEXT"),
]


async def _run_migrations(db: aiosqlite.Connection) -> None:
    for table, column, col_type in _MIGRATIONS:
        try:
            await db.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")
            await db.commit()
        except Exception:
            pass


async def get_db() -> aiosqlite.Connection:
    global _db
    if _db is None:
        settings.db_path.parent.mkdir(parents=True, exist_ok=True)
        _db = await aiosqlite.connect(str(settings.db_path))
        _db.row_factory = aiosqlite.Row
        await _db.execute("PRAGMA journal_mode=WAL")
        await _db.execute("PRAGMA foreign_keys=ON")
        for stmt in SCHEMA.split(";"):
            stmt = stmt.strip()
            if stmt:
                await _db.execute(stmt)
        await _db.commit()
        await _run_migrations(_db)
    return _db


async def close_db() -> None:
    global _db
    if _db is not None:
        await _db.close()
        _db = None
