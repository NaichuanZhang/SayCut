"""Async SQLite database layer."""

import uuid
from datetime import datetime, timezone

import aiosqlite

_ALLOWED_SCENE_FIELDS = frozenset({
    "title", "narration_text", "visual_description",
    "image_path", "video_path", "audio_path", "status",
})

_CREATE_TABLES_SQL = """
CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS storybooks (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES sessions(id),
    title TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS scenes (
    id TEXT PRIMARY KEY,
    storybook_id TEXT NOT NULL REFERENCES storybooks(id),
    idx INTEGER NOT NULL,
    title TEXT NOT NULL DEFAULT '',
    narration_text TEXT NOT NULL DEFAULT '',
    visual_description TEXT NOT NULL DEFAULT '',
    image_path TEXT,
    video_path TEXT,
    audio_path TEXT,
    status TEXT NOT NULL DEFAULT 'empty',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS messages (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES sessions(id),
    role TEXT NOT NULL,
    text TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL
);
"""


def _new_id() -> str:
    return uuid.uuid4().hex[:12]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def init_db(db_path: str = ":memory:") -> aiosqlite.Connection:
    """Open a connection and create tables. Returns the connection."""
    db = await aiosqlite.connect(db_path)
    db.row_factory = aiosqlite.Row
    await db.executescript(_CREATE_TABLES_SQL)
    await db.commit()
    return db


async def create_session(db: aiosqlite.Connection) -> str:
    """Create a new session. Returns the session ID."""
    sid = _new_id()
    await db.execute(
        "INSERT INTO sessions (id, created_at) VALUES (?, ?)",
        (sid, _now()),
    )
    await db.commit()
    return sid


async def get_session(db: aiosqlite.Connection, session_id: str) -> dict | None:
    cursor = await db.execute("SELECT * FROM sessions WHERE id = ?", (session_id,))
    row = await cursor.fetchone()
    return dict(row) if row else None


async def create_storybook(
    db: aiosqlite.Connection, session_id: str, title: str
) -> str:
    bid = _new_id()
    await db.execute(
        "INSERT INTO storybooks (id, session_id, title, created_at) VALUES (?, ?, ?, ?)",
        (bid, session_id, title, _now()),
    )
    await db.commit()
    return bid


async def get_storybook(db: aiosqlite.Connection, storybook_id: str) -> dict | None:
    cursor = await db.execute(
        "SELECT * FROM storybooks WHERE id = ?", (storybook_id,)
    )
    row = await cursor.fetchone()
    return dict(row) if row else None


async def create_scene(
    db: aiosqlite.Connection,
    *,
    storybook_id: str,
    idx: int,
    title: str,
    narration_text: str,
    visual_description: str,
) -> str:
    sid = _new_id()
    await db.execute(
        "INSERT INTO scenes (id, storybook_id, idx, title, narration_text, visual_description, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (sid, storybook_id, idx, title, narration_text, visual_description, _now()),
    )
    await db.commit()
    return sid


async def get_scenes_by_storybook(
    db: aiosqlite.Connection, storybook_id: str
) -> list[dict]:
    cursor = await db.execute(
        "SELECT * FROM scenes WHERE storybook_id = ? ORDER BY idx",
        (storybook_id,),
    )
    return [dict(row) for row in await cursor.fetchall()]


async def shift_scene_indices(
    db: aiosqlite.Connection, storybook_id: str, from_idx: int, offset: int
) -> None:
    """Shift scene indices >= from_idx forward by offset."""
    await db.execute(
        "UPDATE scenes SET idx = idx + ? WHERE storybook_id = ? AND idx >= ?",
        (offset, storybook_id, from_idx),
    )
    await db.commit()


async def update_scene_field(
    db: aiosqlite.Connection, scene_id: str, field: str, value: str
) -> None:
    if field not in _ALLOWED_SCENE_FIELDS:
        raise ValueError(f"Cannot update field: {field}")
    await db.execute(
        f"UPDATE scenes SET {field} = ? WHERE id = ?",  # noqa: S608 — field is validated
        (value, scene_id),
    )
    await db.commit()


async def create_message(
    db: aiosqlite.Connection, session_id: str, role: str, text: str
) -> str:
    mid = _new_id()
    await db.execute(
        "INSERT INTO messages (id, session_id, role, text, created_at) VALUES (?, ?, ?, ?, ?)",
        (mid, session_id, role, text, _now()),
    )
    await db.commit()
    return mid


async def get_messages_by_session(
    db: aiosqlite.Connection, session_id: str
) -> list[dict]:
    cursor = await db.execute(
        "SELECT * FROM messages WHERE session_id = ? ORDER BY created_at",
        (session_id,),
    )
    return [dict(row) for row in await cursor.fetchall()]


async def list_storybooks(db: aiosqlite.Connection) -> list[dict]:
    """List all storybooks with thumbnail and scene count, newest first."""
    cursor = await db.execute(
        """
        SELECT s.id, s.session_id, s.title, s.created_at,
               (SELECT sc.image_path FROM scenes sc
                WHERE sc.storybook_id = s.id ORDER BY sc.idx LIMIT 1) as thumbnail_path,
               (SELECT COUNT(*) FROM scenes sc
                WHERE sc.storybook_id = s.id) as scene_count
        FROM storybooks s
        ORDER BY s.created_at DESC
        """
    )
    return [dict(row) for row in await cursor.fetchall()]


async def get_storybook_with_scenes(
    db: aiosqlite.Connection, storybook_id: str
) -> dict | None:
    """Return a storybook with its scenes, or None if not found."""
    storybook = await get_storybook(db, storybook_id)
    if storybook is None:
        return None
    scenes = await get_scenes_by_storybook(db, storybook_id)
    return {**storybook, "scenes": scenes}
