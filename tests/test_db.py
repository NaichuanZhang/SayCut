"""Tests for backend.db — SQLite database layer."""

import pytest
import pytest_asyncio

from backend.db import init_db, create_session, get_session, create_storybook, get_storybook, create_scene, get_scenes_by_storybook, update_scene_field, create_message, get_messages_by_session


@pytest_asyncio.fixture
async def db():
    """Create an in-memory SQLite database for testing."""
    connection = await init_db(":memory:")
    yield connection
    await connection.close()


@pytest.mark.asyncio
async def test_create_tables(db):
    """Tables exist after init_db."""
    cursor = await db.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    )
    tables = [row[0] for row in await cursor.fetchall()]
    assert "sessions" in tables
    assert "storybooks" in tables
    assert "scenes" in tables
    assert "messages" in tables


@pytest.mark.asyncio
async def test_create_session(db):
    """Insert and retrieve a session by ID."""
    session_id = await create_session(db)
    assert session_id is not None
    session = await get_session(db, session_id)
    assert session is not None
    assert session["id"] == session_id
    assert "created_at" in session


@pytest.mark.asyncio
async def test_create_storybook(db):
    """Insert a storybook linked to a session."""
    session_id = await create_session(db)
    storybook_id = await create_storybook(db, session_id, "My Story")
    storybook = await get_storybook(db, storybook_id)
    assert storybook is not None
    assert storybook["session_id"] == session_id
    assert storybook["title"] == "My Story"


@pytest.mark.asyncio
async def test_create_scene(db):
    """Insert a scene and retrieve by storybook_id."""
    session_id = await create_session(db)
    storybook_id = await create_storybook(db, session_id, "Test Book")
    scene_id = await create_scene(
        db,
        storybook_id=storybook_id,
        idx=0,
        title="Scene One",
        narration_text="Once upon a time...",
        visual_description="A dark forest",
    )
    scenes = await get_scenes_by_storybook(db, storybook_id)
    assert len(scenes) == 1
    assert scenes[0]["id"] == scene_id
    assert scenes[0]["title"] == "Scene One"
    assert scenes[0]["status"] == "empty"


@pytest.mark.asyncio
async def test_update_scene_field(db):
    """Update image_path and status on a scene."""
    session_id = await create_session(db)
    storybook_id = await create_storybook(db, session_id, "Test Book")
    scene_id = await create_scene(
        db, storybook_id=storybook_id, idx=0, title="S1",
        narration_text="", visual_description="",
    )
    await update_scene_field(db, scene_id, "image_path", "/assets/img.png")
    await update_scene_field(db, scene_id, "status", "ready")

    scenes = await get_scenes_by_storybook(db, storybook_id)
    assert scenes[0]["image_path"] == "/assets/img.png"
    assert scenes[0]["status"] == "ready"


@pytest.mark.asyncio
async def test_create_message(db):
    """Insert and retrieve messages by session."""
    session_id = await create_session(db)
    await create_message(db, session_id, "user", "Hello")
    await create_message(db, session_id, "agent", "Hi there!")
    messages = await get_messages_by_session(db, session_id)
    assert len(messages) == 2
    assert messages[0]["role"] == "user"
    assert messages[1]["role"] == "agent"
