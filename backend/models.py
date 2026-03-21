"""Pydantic models for DB records and WebSocket messages."""

from pydantic import BaseModel


class SessionRecord(BaseModel):
    id: str
    created_at: str


class StorybookRecord(BaseModel):
    id: str
    session_id: str
    title: str
    created_at: str


class SceneRecord(BaseModel):
    id: str
    storybook_id: str
    idx: int
    title: str
    narration_text: str
    visual_description: str
    image_path: str | None = None
    video_path: str | None = None
    audio_path: str | None = None
    status: str = "empty"
    created_at: str


class MessageRecord(BaseModel):
    id: str
    session_id: str
    role: str
    text: str
    created_at: str
