"""FastAPI application — entry point for the SayCut backend."""

import logging
import os

from fastapi import FastAPI, WebSocket
from fastapi.responses import JSONResponse

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.config import ASSETS_DIR, DB_PATH
from backend.db import init_db, get_messages_by_session, list_storybooks, get_storybook_with_scenes
from backend.ws_handler import websocket_endpoint

app = FastAPI(title="SayCut Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure assets directory exists before mounting
os.makedirs(ASSETS_DIR, exist_ok=True)
app.mount("/assets", StaticFiles(directory=ASSETS_DIR), name="assets")


def _asset_url(path: str | None) -> str | None:
    """Convert a relative asset path to a URL."""
    if not path:
        return None
    return f"/assets/{path}"


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/api/storybooks")
async def get_storybooks():
    """List all storybooks with thumbnail and scene count."""
    db = await init_db(DB_PATH)
    try:
        rows = await list_storybooks(db)
        return [
            {
                "id": row["id"],
                "title": row["title"] or "Untitled Story",
                "createdAt": row["created_at"],
                "thumbnailUrl": _asset_url(row["thumbnail_path"]),
                "sceneCount": row["scene_count"],
            }
            for row in rows
        ]
    finally:
        await db.close()


@app.get("/api/storybooks/{storybook_id}")
async def get_storybook_detail(storybook_id: str):
    """Get a storybook with all its scenes."""
    db = await init_db(DB_PATH)
    try:
        data = await get_storybook_with_scenes(db, storybook_id)
        if data is None:
            return JSONResponse(status_code=404, content={"error": "Storybook not found"})
        return {
            "id": data["id"],
            "title": data["title"] or "Untitled Story",
            "sessionId": data["session_id"],
            "createdAt": data["created_at"],
            "scenes": [
                {
                    "id": s["id"],
                    "index": s["idx"],
                    "title": s["title"],
                    "narrationText": s["narration_text"],
                    "visualDescription": s["visual_description"],
                    "imageUrl": _asset_url(s["image_path"]),
                    "videoUrl": _asset_url(s["video_path"]),
                    "audioUrl": _asset_url(s["audio_path"]),
                    "status": s["status"],
                }
                for s in data["scenes"]
            ],
        }
    finally:
        await db.close()


@app.get("/api/storybooks/{storybook_id}/messages")
async def get_storybook_messages(storybook_id: str):
    """Get conversation messages for a storybook's session."""
    db = await init_db(DB_PATH)
    try:
        data = await get_storybook_with_scenes(db, storybook_id)
        if data is None:
            return JSONResponse(status_code=404, content={"error": "Storybook not found"})
        messages = await get_messages_by_session(db, data["session_id"])
        return [
            {
                "id": m["id"],
                "role": m["role"],
                "text": m["text"],
                "createdAt": m["created_at"],
            }
            for m in messages
        ]
    finally:
        await db.close()


@app.websocket("/ws")
async def ws(websocket: WebSocket):
    await websocket_endpoint(websocket)
