"""WebSocket message protocol — type enums, encoding, and decoding."""

import json
from enum import Enum


class ServerMessageType(str, Enum):
    SESSION_CREATED = "session_created"
    AGENT_THINKING = "agent_thinking"
    AGENT_STREAM_START = "agent_stream_start"
    AGENT_STREAM_CHUNK = "agent_stream_chunk"
    AGENT_STREAM_END = "agent_stream_end"
    TOOL_STATUS = "tool_status"
    STORYBOOK_CREATED = "storybook_created"
    SCENE_ADD = "scene_add"
    SCENE_UPDATE = "scene_update"
    SCENE_REMOVE = "scene_remove"
    AGENT_IDLE = "agent_idle"
    ERROR = "error"


class ClientMessageType(str, Enum):
    SESSION_INIT = "session_init"
    LOAD_STORYBOOK = "load_storybook"
    SET_PROJECT_MODE = "set_project_mode"
    AUDIO_DATA = "audio_data"
    TEXT_MESSAGE = "text_message"


_CLIENT_TYPES = {t.value for t in ClientMessageType}


def encode_server_message(msg_type: ServerMessageType, **kwargs) -> str:
    """Encode a server message to JSON string."""
    return json.dumps({"type": msg_type.value, **kwargs})


def decode_client_message(raw: str) -> tuple[ClientMessageType | None, dict]:
    """Decode a client JSON message. Returns (type, payload) or (None, error_dict)."""
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return None, {"error": "Invalid JSON"}

    msg_type_str = data.get("type")
    if msg_type_str not in _CLIENT_TYPES:
        return None, {"error": f"Unknown message type: {msg_type_str}"}

    return ClientMessageType(msg_type_str), data
