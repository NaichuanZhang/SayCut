"""Tests for backend.storybook_tools — tool definitions and async executors."""

import json
import os
from unittest.mock import AsyncMock, patch, MagicMock
from dataclasses import dataclass

import pytest
import pytest_asyncio

from backend.storybook_tools import (
    STORYBOOK_TOOLS,
    execute_storybook_tool,
)
from backend.db import init_db, create_session, create_storybook, create_scene, get_scenes_by_storybook, shift_scene_indices


@pytest_asyncio.fixture
async def db():
    connection = await init_db(":memory:")
    yield connection
    await connection.close()


@pytest.fixture
def assets_dir(tmp_path):
    return str(tmp_path)


class TestToolDefinitions:
    def test_tool_definitions_valid_json(self):
        """All tool defs match the expected function-call schema."""
        for tool in STORYBOOK_TOOLS:
            assert tool["type"] == "function"
            func = tool["function"]
            assert "name" in func
            assert "description" in func
            assert "parameters" in func
            params = func["parameters"]
            assert params["type"] == "object"
            assert "properties" in params

    def test_tool_names_unique(self):
        """No duplicate tool names."""
        names = [t["function"]["name"] for t in STORYBOOK_TOOLS]
        assert len(names) == len(set(names))

    def test_expected_tools_present(self):
        """All expected storybook tools are defined."""
        names = {t["function"]["name"] for t in STORYBOOK_TOOLS}
        expected = {
            "generate_script",
            "generate_scene_image",
            "generate_scene_audio",
            "generate_scene_video",
            "edit_scene_image",
        }
        assert expected.issubset(names)


class TestExecuteGenerateScript:
    @pytest.mark.asyncio
    async def test_creates_scenes_and_sends_events(self, db, assets_dir):
        """generate_script creates scene records and sends scene_add events."""
        session_id = await create_session(db)
        storybook_id = await create_storybook(db, session_id, "Test Story")

        events = []

        async def send_event(event_type, **kwargs):
            events.append({"type": event_type, **kwargs})

        mock_script_response = json.dumps({
            "title": "Dragon Chef",
            "scenes": [
                {
                    "title": "The Beginning",
                    "narration_text": "Once upon a time...",
                    "visual_description": "A dragon in a kitchen",
                },
                {
                    "title": "The Adventure",
                    "narration_text": "The dragon found...",
                    "visual_description": "A forest with mushrooms",
                },
            ],
        })

        with patch("backend.storybook_tools.generate_script", new_callable=AsyncMock) as mock_gen:
            mock_gen.return_value = mock_script_response
            result = await execute_storybook_tool(
                "generate_script",
                {"story_prompt": "A dragon who learns to cook"},
                send_event=send_event,
                db=db,
                session_id=session_id,
                storybook_id=storybook_id,
                assets_dir=assets_dir,
            )

        assert "title" in result
        scene_add_events = [e for e in events if e["type"] == "scene_add"]
        assert len(scene_add_events) == 2

        # Model response should only contain text fields, no URLs
        for scene in result["scenes"]:
            assert set(scene.keys()) == {"id", "index", "title", "narrationText"}

        scenes = await get_scenes_by_storybook(db, storybook_id)
        assert len(scenes) == 2


class TestExecuteGenerateImage:
    @pytest.mark.asyncio
    async def test_saves_file_and_sends_update(self, db, assets_dir):
        """generate_scene_image saves PNG and sends scene_update."""
        session_id = await create_session(db)
        storybook_id = await create_storybook(db, session_id, "Test")
        scene_id = await create_scene(
            db, storybook_id=storybook_id, idx=0, title="S1",
            narration_text="", visual_description="A forest",
        )

        events = []

        async def send_event(event_type, **kwargs):
            events.append({"type": event_type, **kwargs})

        fake_image_bytes = b"\x89PNG\r\n\x1a\nfake"

        with patch("backend.storybook_tools.generate_image", new_callable=AsyncMock) as mock_gen:
            mock_gen.return_value = fake_image_bytes
            result = await execute_storybook_tool(
                "generate_scene_image",
                {"scene_id": scene_id, "visual_description": "A forest"},
                send_event=send_event,
                db=db,
                session_id=session_id,
                storybook_id=storybook_id,
                assets_dir=assets_dir,
            )

        assert "imageUrl" not in result
        assert result["status"] == "done"
        update_events = [e for e in events if e["type"] == "scene_update"]
        assert len(update_events) >= 1
        assert update_events[-1]["field"] == "imageUrl"


class TestExecuteGenerateAudio:
    @pytest.mark.asyncio
    async def test_saves_wav_and_sends_update(self, db, assets_dir):
        """generate_scene_audio saves WAV and sends scene_update."""
        session_id = await create_session(db)
        storybook_id = await create_storybook(db, session_id, "Test")
        scene_id = await create_scene(
            db, storybook_id=storybook_id, idx=0, title="S1",
            narration_text="Hello", visual_description="",
        )

        events = []

        async def send_event(event_type, **kwargs):
            events.append({"type": event_type, **kwargs})

        @dataclass(frozen=True)
        class FakeTTSResult:
            wav_bytes: bytes = b"RIFF....fake wav data"
            sample_rate: int = 24000
            duration_s: float = 1.5

        with patch("backend.storybook_tools.synthesize_speech", new_callable=AsyncMock) as mock_tts:
            mock_tts.return_value = FakeTTSResult()
            result = await execute_storybook_tool(
                "generate_scene_audio",
                {"scene_id": scene_id, "narration_text": "Hello world"},
                send_event=send_event,
                db=db,
                session_id=session_id,
                storybook_id=storybook_id,
                assets_dir=assets_dir,
            )

        assert "audioUrl" not in result
        assert result["status"] == "done"
        update_events = [e for e in events if e["type"] == "scene_update"]
        assert any(e["field"] == "audioUrl" for e in update_events)


class TestExecuteGenerateVideo:
    @pytest.mark.asyncio
    async def test_saves_mp4_and_sends_update(self, db, assets_dir):
        """generate_scene_video saves MP4 and sends scene_update."""
        session_id = await create_session(db)
        storybook_id = await create_storybook(db, session_id, "Test")
        scene_id = await create_scene(
            db, storybook_id=storybook_id, idx=0, title="S1",
            narration_text="", visual_description="",
        )

        # Create a fake image file for the scene
        from backend.asset_storage import save_asset
        save_asset(assets_dir, session_id, f"scene_{scene_id}.png", b"fake image")
        from backend.db import update_scene_field
        await update_scene_field(db, scene_id, "image_path", f"{session_id}/scene_{scene_id}.png")

        events = []

        async def send_event(event_type, **kwargs):
            events.append({"type": event_type, **kwargs})

        @dataclass(frozen=True)
        class FakeVideoResult:
            video_bytes: bytes = b"fake mp4 data"
            task_id: str = "task123"

        with patch("backend.storybook_tools.generate_video", new_callable=AsyncMock) as mock_vid:
            mock_vid.return_value = FakeVideoResult()
            result = await execute_storybook_tool(
                "generate_scene_video",
                {"scene_id": scene_id},
                send_event=send_event,
                db=db,
                session_id=session_id,
                storybook_id=storybook_id,
                assets_dir=assets_dir,
            )

        assert "videoUrl" not in result
        assert result["status"] == "done"
        update_events = [e for e in events if e["type"] == "scene_update"]
        assert any(e["field"] == "videoUrl" for e in update_events)


class TestExecuteEditImage:
    @pytest.mark.asyncio
    async def test_overwrites_file_and_sends_update(self, db, assets_dir):
        """edit_scene_image overwrites the image and sends scene_update."""
        session_id = await create_session(db)
        storybook_id = await create_storybook(db, session_id, "Test")
        scene_id = await create_scene(
            db, storybook_id=storybook_id, idx=0, title="S1",
            narration_text="", visual_description="",
        )

        # Create an existing image
        from backend.asset_storage import save_asset
        rel = save_asset(assets_dir, session_id, f"scene_{scene_id}.png", b"original")
        from backend.db import update_scene_field
        await update_scene_field(db, scene_id, "image_path", rel)

        events = []

        async def send_event(event_type, **kwargs):
            events.append({"type": event_type, **kwargs})

        @dataclass(frozen=True)
        class FakeEditResult:
            image_bytes: bytes = b"edited image"
            image_base64: str = ""
            use_lightning: bool = False
            processing_time_seconds: float = 1.0

        with patch("backend.storybook_tools.edit_image", new_callable=AsyncMock) as mock_edit:
            mock_edit.return_value = FakeEditResult()
            result = await execute_storybook_tool(
                "edit_scene_image",
                {"scene_id": scene_id, "edit_prompt": "Make it blue"},
                send_event=send_event,
                db=db,
                session_id=session_id,
                storybook_id=storybook_id,
                assets_dir=assets_dir,
            )

        assert "imageUrl" not in result
        assert result["status"] == "done"


class TestExecuteUnknownTool:
    @pytest.mark.asyncio
    async def test_returns_error(self, db, assets_dir):
        """Unknown tool returns an error dict."""
        session_id = await create_session(db)
        storybook_id = await create_storybook(db, session_id, "Test")

        result = await execute_storybook_tool(
            "nonexistent_tool",
            {},
            send_event=AsyncMock(),
            db=db,
            session_id=session_id,
            storybook_id=storybook_id,
            assets_dir=assets_dir,
        )
        assert "error" in result


class TestInsertSceneBetweenExisting:
    @pytest.mark.asyncio
    async def test_inserts_scenes_and_shifts_indices(self, db, assets_dir):
        """generate_script with insert_after_scene_id inserts at correct position and shifts."""
        session_id = await create_session(db)
        storybook_id = await create_storybook(db, session_id, "Test Story")

        # Create 3 existing scenes at idx 0, 1, 2
        scene_ids = []
        for i in range(3):
            sid = await create_scene(
                db, storybook_id=storybook_id, idx=i, title=f"Scene {i + 1}",
                narration_text=f"Narration {i + 1}", visual_description=f"Visual {i + 1}",
            )
            scene_ids.append(sid)

        events = []

        async def send_event(event_type, **kwargs):
            events.append({"type": event_type, **kwargs})

        mock_script_response = json.dumps({
            "title": "Extended Story",
            "scenes": [
                {
                    "title": "Inserted Scene A",
                    "narration_text": "The kitten crosses a river.",
                    "visual_description": "A kitten crossing a river.",
                },
                {
                    "title": "Inserted Scene B",
                    "narration_text": "The kitten finds a bridge.",
                    "visual_description": "A kitten on a bridge.",
                },
            ],
        })

        with patch("backend.storybook_tools.generate_script", new_callable=AsyncMock) as mock_gen:
            mock_gen.return_value = mock_script_response
            result = await execute_storybook_tool(
                "generate_script",
                {"story_prompt": "river crossing", "insert_after_scene_id": scene_ids[0]},
                send_event=send_event,
                db=db,
                session_id=session_id,
                storybook_id=storybook_id,
                assets_dir=assets_dir,
            )

        # New scenes should have idx 1 and 2
        assert result["scenes"][0]["index"] == 1
        assert result["scenes"][1]["index"] == 2

        # Verify DB state: 5 scenes total, correct order
        all_scenes = await get_scenes_by_storybook(db, storybook_id)
        assert len(all_scenes) == 5
        assert all_scenes[0]["id"] == scene_ids[0]  # original scene 0
        assert all_scenes[0]["idx"] == 0
        assert all_scenes[1]["title"] == "Inserted Scene A"
        assert all_scenes[1]["idx"] == 1
        assert all_scenes[2]["title"] == "Inserted Scene B"
        assert all_scenes[2]["idx"] == 2
        assert all_scenes[3]["id"] == scene_ids[1]  # original scene 1 shifted
        assert all_scenes[3]["idx"] == 3
        assert all_scenes[4]["id"] == scene_ids[2]  # original scene 2 shifted
        assert all_scenes[4]["idx"] == 4

        # Verify scene_update events sent for shifted scenes with field="index"
        index_events = [e for e in events if e["type"] == "scene_update" and e.get("field") == "index"]
        shifted_ids = {e["scene_id"] for e in index_events}
        assert scene_ids[1] in shifted_ids
        assert scene_ids[2] in shifted_ids

    @pytest.mark.asyncio
    async def test_insert_after_invalid_scene_returns_error(self, db, assets_dir):
        """generate_script with non-existent insert_after_scene_id returns error."""
        session_id = await create_session(db)
        storybook_id = await create_storybook(db, session_id, "Test Story")

        events = []

        async def send_event(event_type, **kwargs):
            events.append({"type": event_type, **kwargs})

        mock_script_response = json.dumps({
            "title": "Story",
            "scenes": [{"title": "S1", "narration_text": "N1", "visual_description": "V1"}],
        })

        with patch("backend.storybook_tools.generate_script", new_callable=AsyncMock) as mock_gen:
            mock_gen.return_value = mock_script_response
            result = await execute_storybook_tool(
                "generate_script",
                {"story_prompt": "test", "insert_after_scene_id": "nonexistent"},
                send_event=send_event,
                db=db,
                session_id=session_id,
                storybook_id=storybook_id,
                assets_dir=assets_dir,
            )

        assert "error" in result


class TestRemoveScene:
    @pytest.mark.asyncio
    async def test_removes_scene_and_shifts_indices(self, db, assets_dir):
        """remove_scene deletes the scene and shifts later indices backward."""
        session_id = await create_session(db)
        storybook_id = await create_storybook(db, session_id, "Test Story")

        scene_ids = []
        for i in range(3):
            sid = await create_scene(
                db, storybook_id=storybook_id, idx=i, title=f"Scene {i + 1}",
                narration_text=f"N{i + 1}", visual_description=f"V{i + 1}",
            )
            scene_ids.append(sid)

        events = []

        async def send_event(event_type, **kwargs):
            events.append({"type": event_type, **kwargs})

        result = await execute_storybook_tool(
            "remove_scene",
            {"scene_id": scene_ids[1]},
            send_event=send_event,
            db=db,
            session_id=session_id,
            storybook_id=storybook_id,
            assets_dir=assets_dir,
        )

        assert result["status"] == "removed"
        assert result["scene_id"] == scene_ids[1]

        remaining = await get_scenes_by_storybook(db, storybook_id)
        assert len(remaining) == 2
        assert remaining[0]["id"] == scene_ids[0]
        assert remaining[0]["idx"] == 0
        assert remaining[1]["id"] == scene_ids[2]
        assert remaining[1]["idx"] == 1

        remove_events = [e for e in events if e["type"] == "scene_remove"]
        assert len(remove_events) == 1
        assert remove_events[0]["scene_id"] == scene_ids[1]

        index_events = [e for e in events if e["type"] == "scene_update" and e.get("field") == "index"]
        assert any(e["scene_id"] == scene_ids[2] for e in index_events)

    @pytest.mark.asyncio
    async def test_remove_nonexistent_scene_returns_error(self, db, assets_dir):
        """remove_scene with non-existent scene_id returns error."""
        session_id = await create_session(db)
        storybook_id = await create_storybook(db, session_id, "Test")

        events = []

        async def send_event(event_type, **kwargs):
            events.append({"type": event_type, **kwargs})

        result = await execute_storybook_tool(
            "remove_scene",
            {"scene_id": "nonexistent"},
            send_event=send_event,
            db=db,
            session_id=session_id,
            storybook_id=storybook_id,
            assets_dir=assets_dir,
        )

        assert "error" in result


class TestToolSendsStatusEvents:
    @pytest.mark.asyncio
    async def test_status_events_emitted(self, db, assets_dir):
        """tool_status events are sent before and after execution."""
        session_id = await create_session(db)
        storybook_id = await create_storybook(db, session_id, "Test")
        scene_id = await create_scene(
            db, storybook_id=storybook_id, idx=0, title="S1",
            narration_text="", visual_description="A forest",
        )

        events = []

        async def send_event(event_type, **kwargs):
            events.append({"type": event_type, **kwargs})

        with patch("backend.storybook_tools.generate_image", new_callable=AsyncMock) as mock_gen:
            mock_gen.return_value = b"fake image"
            await execute_storybook_tool(
                "generate_scene_image",
                {"scene_id": scene_id, "visual_description": "A forest"},
                send_event=send_event,
                db=db,
                session_id=session_id,
                storybook_id=storybook_id,
                assets_dir=assets_dir,
            )

        status_events = [e for e in events if e["type"] == "tool_status"]
        assert len(status_events) >= 2  # at least "running" and "done"
        assert status_events[0]["status"] == "running"
        assert status_events[-1]["status"] == "done"
