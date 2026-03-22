"""Storybook tool definitions and async executors for the voice agent."""

import json
import logging
import os
import time
from typing import Any, Callable, Awaitable

logger = logging.getLogger(__name__)

import aiosqlite

from bosonUtil.eigen_script import generate_script
from bosonUtil.eigen_image_gen import generate_image
from bosonUtil.eigen_image_edit import edit_image
from bosonUtil.eigen_i2v import generate_video
from bosonUtil.eigen_tts import synthesize_speech

from backend.asset_storage import save_asset, get_asset_url
from backend.db import create_scene, get_scenes_by_storybook, update_scene_field

SendEvent = Callable[..., Awaitable[None]]


async def _validate_scene(db: aiosqlite.Connection, scene_id: str) -> dict | None:
    """Return scene row if it exists, or None."""
    cursor = await db.execute("SELECT * FROM scenes WHERE id = ?", (scene_id,))
    row = await cursor.fetchone()
    return dict(row) if row else None

STORYBOOK_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "generate_script",
            "description": (
                "Generate a scene-by-scene storybook script from a story prompt. "
                "Returns JSON with title and array of scenes."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "story_prompt": {
                        "type": "string",
                        "description": "The story idea or prompt from the user",
                    },
                    "num_scenes": {
                        "type": "integer",
                        "description": "Number of scenes to generate (default 4)",
                    },
                },
                "required": ["story_prompt"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "generate_scene_image",
            "description": "Generate an illustration for a scene based on its visual description.",
            "parameters": {
                "type": "object",
                "properties": {
                    "scene_id": {"type": "string", "description": "The scene ID"},
                    "visual_description": {
                        "type": "string",
                        "description": "Detailed visual description for image generation",
                    },
                },
                "required": ["scene_id", "visual_description"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "generate_scene_audio",
            "description": "Generate narration audio (text-to-speech) for a scene.",
            "parameters": {
                "type": "object",
                "properties": {
                    "scene_id": {"type": "string", "description": "The scene ID"},
                    "narration_text": {"type": "string", "description": "Text to speak"},
                },
                "required": ["scene_id", "narration_text"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "generate_scene_video",
            "description": "Generate a short video clip from a scene's image.",
            "parameters": {
                "type": "object",
                "properties": {
                    "scene_id": {"type": "string", "description": "The scene ID"},
                    "motion_prompt": {
                        "type": "string",
                        "description": "Description of desired motion/animation",
                    },
                },
                "required": ["scene_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "edit_scene_image",
            "description": "Edit an existing scene image with a text instruction.",
            "parameters": {
                "type": "object",
                "properties": {
                    "scene_id": {"type": "string", "description": "The scene ID"},
                    "edit_prompt": {
                        "type": "string",
                        "description": "How to modify the image",
                    },
                },
                "required": ["scene_id", "edit_prompt"],
            },
        },
    },
]

_SCRIPT_SYSTEM_PROMPT = (
    "You are a storybook script writer. Given a story prompt, generate a JSON object with "
    "a 'title' field and a 'scenes' array. Each scene has 'title', 'narration_text', and "
    "'visual_description' fields. Output ONLY valid JSON, no other text."
)


async def _execute_generate_script(
    args: dict,
    send_event: SendEvent,
    db: aiosqlite.Connection,
    session_id: str,
    storybook_id: str,
    assets_dir: str,
) -> dict:
    story_prompt = args.get("story_prompt", "")
    num_scenes = args.get("num_scenes", 4)

    messages = [
        {"role": "system", "content": _SCRIPT_SYSTEM_PROMPT},
        {"role": "user", "content": f"Create a {num_scenes}-scene storybook about: {story_prompt}"},
    ]

    raw = await generate_script(messages)

    # Parse JSON from response (strip markdown code fences if present)
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[-1].rsplit("```", 1)[0].strip()

    script = json.loads(cleaned)
    title = script.get("title", "Untitled Story")
    scenes_data = script.get("scenes", [])

    existing_scenes = await get_scenes_by_storybook(db, storybook_id)
    idx_offset = len(existing_scenes)

    result_scenes = []
    for i, s in enumerate(scenes_data):
        idx = idx_offset + i
        scene_id = await create_scene(
            db,
            storybook_id=storybook_id,
            idx=idx,
            title=s.get("title", f"Scene {idx + 1}"),
            narration_text=s.get("narration_text", ""),
            visual_description=s.get("visual_description", ""),
        )
        scene_payload = {
            "id": scene_id,
            "index": idx,
            "title": s.get("title", f"Scene {idx + 1}"),
            "narrationText": s.get("narration_text", ""),
            "visualDescription": s.get("visual_description", ""),
            "imageUrl": None,
            "videoUrl": None,
            "audioUrl": None,
            "status": "empty",
        }
        await send_event("scene_add", scene=scene_payload)
        result_scenes.append(scene_payload)

    model_scenes = [
        {"id": s["id"], "index": s["index"], "title": s["title"], "narrationText": s["narrationText"]}
        for s in result_scenes
    ]
    return {"name": "generate_script", "title": title, "scenes": model_scenes}


async def _execute_generate_image(
    args: dict,
    send_event: SendEvent,
    db: aiosqlite.Connection,
    session_id: str,
    assets_dir: str,
) -> dict:
    scene_id = args["scene_id"]
    description = args["visual_description"]

    scene = await _validate_scene(db, scene_id)
    if not scene:
        return {"name": "generate_scene_image", "error": f"Scene {scene_id} not found"}

    image_bytes = await generate_image(description)

    filename = f"scene_{scene_id}.png"
    rel_path = save_asset(assets_dir, session_id, filename, image_bytes)
    url = get_asset_url(rel_path)
    logger.debug("Image saved: %s", rel_path)

    await update_scene_field(db, scene_id, "image_path", rel_path)
    await update_scene_field(db, scene_id, "status", "ready")
    await send_event("scene_update", scene_id=scene_id, field="imageUrl", value=url)

    return {"name": "generate_scene_image", "scene_id": scene_id, "status": "done"}


async def _execute_generate_audio(
    args: dict,
    send_event: SendEvent,
    db: aiosqlite.Connection,
    session_id: str,
    assets_dir: str,
) -> dict:
    scene_id = args["scene_id"]
    text = args["narration_text"]

    scene = await _validate_scene(db, scene_id)
    if not scene:
        return {"name": "generate_scene_audio", "error": f"Scene {scene_id} not found"}

    result = await synthesize_speech(text)

    filename = f"scene_{scene_id}.wav"
    rel_path = save_asset(assets_dir, session_id, filename, result.wav_bytes)
    url = get_asset_url(rel_path)

    await update_scene_field(db, scene_id, "audio_path", rel_path)
    await send_event("scene_update", scene_id=scene_id, field="audioUrl", value=url)

    return {
        "name": "generate_scene_audio",
        "scene_id": scene_id,
        "status": "done",
        "duration_s": result.duration_s,
    }


async def _execute_generate_video(
    args: dict,
    send_event: SendEvent,
    db: aiosqlite.Connection,
    session_id: str,
    assets_dir: str,
) -> dict:
    scene_id = args["scene_id"]
    motion_prompt = args.get("motion_prompt", "gentle slow motion, cinematic")

    scene = await _validate_scene(db, scene_id)
    if not scene:
        return {"name": "generate_scene_video", "error": f"Scene {scene_id} not found"}

    # Get the scene's image path from DB
    cursor = await db.execute("SELECT image_path FROM scenes WHERE id = ?", (scene_id,))
    row = await cursor.fetchone()
    if not row or not row[0]:
        return {"name": "generate_scene_video", "error": "Scene has no image yet"}

    image_full_path = os.path.join(assets_dir, row[0])

    result = await generate_video(motion_prompt, image_full_path)

    filename = f"scene_{scene_id}.mp4"
    rel_path = save_asset(assets_dir, session_id, filename, result.video_bytes)
    url = get_asset_url(rel_path)

    await update_scene_field(db, scene_id, "video_path", rel_path)
    await send_event("scene_update", scene_id=scene_id, field="videoUrl", value=url)

    return {"name": "generate_scene_video", "scene_id": scene_id, "status": "done"}


async def _execute_edit_image(
    args: dict,
    send_event: SendEvent,
    db: aiosqlite.Connection,
    session_id: str,
    assets_dir: str,
) -> dict:
    scene_id = args["scene_id"]
    edit_prompt = args["edit_prompt"]

    scene = await _validate_scene(db, scene_id)
    if not scene:
        return {"name": "edit_scene_image", "error": f"Scene {scene_id} not found"}

    # Get the scene's current image path
    cursor = await db.execute("SELECT image_path FROM scenes WHERE id = ?", (scene_id,))
    row = await cursor.fetchone()
    if not row or not row[0]:
        return {"name": "edit_scene_image", "error": "Scene has no image to edit"}

    image_full_path = os.path.join(assets_dir, row[0])

    result = await edit_image(edit_prompt, [image_full_path])

    filename = f"scene_{scene_id}.png"
    rel_path = save_asset(assets_dir, session_id, filename, result.image_bytes)
    url = get_asset_url(rel_path)

    await update_scene_field(db, scene_id, "image_path", rel_path)
    await send_event("scene_update", scene_id=scene_id, field="imageUrl", value=url)

    return {"name": "edit_scene_image", "scene_id": scene_id, "status": "done"}


async def execute_storybook_tool(
    tool_name: str,
    args: dict,
    *,
    send_event: SendEvent,
    db: aiosqlite.Connection,
    session_id: str,
    storybook_id: str,
    assets_dir: str,
) -> dict:
    """Execute a storybook tool by name. Returns result dict for the voice model."""
    logger.info("Executing tool: %s", tool_name)
    start_time = time.monotonic()
    await send_event("tool_status", tool_name=tool_name, status="running")

    try:
        if tool_name == "generate_script":
            result = await _execute_generate_script(
                args, send_event, db, session_id, storybook_id, assets_dir
            )
        elif tool_name == "generate_scene_image":
            result = await _execute_generate_image(
                args, send_event, db, session_id, assets_dir
            )
        elif tool_name == "generate_scene_audio":
            result = await _execute_generate_audio(
                args, send_event, db, session_id, assets_dir
            )
        elif tool_name == "generate_scene_video":
            result = await _execute_generate_video(
                args, send_event, db, session_id, assets_dir
            )
        elif tool_name == "edit_scene_image":
            result = await _execute_edit_image(
                args, send_event, db, session_id, assets_dir
            )
        else:
            result = {"name": tool_name, "error": f"Unknown tool: {tool_name}"}
    except Exception as e:
        logger.error("Tool %s failed: %s", tool_name, e)
        result = {"name": tool_name, "error": str(e)}

    elapsed = time.monotonic() - start_time
    logger.info("Tool %s completed in %.2fs", tool_name, elapsed)
    await send_event("tool_status", tool_name=tool_name, status="done")
    return result
