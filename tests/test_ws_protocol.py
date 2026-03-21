"""Tests for backend.ws_protocol — WebSocket message encoding/decoding."""

import json
import pytest

from backend.ws_protocol import (
    encode_server_message,
    decode_client_message,
    ServerMessageType,
    ClientMessageType,
)


class TestEncodeServerMessage:
    def test_session_created(self):
        msg = encode_server_message(ServerMessageType.SESSION_CREATED, session_id="abc123")
        parsed = json.loads(msg)
        assert parsed["type"] == "session_created"
        assert parsed["session_id"] == "abc123"

    def test_agent_thinking(self):
        msg = encode_server_message(ServerMessageType.AGENT_THINKING)
        parsed = json.loads(msg)
        assert parsed["type"] == "agent_thinking"

    def test_agent_stream_chunk(self):
        msg = encode_server_message(
            ServerMessageType.AGENT_STREAM_CHUNK, message_id="m1", text="hello"
        )
        parsed = json.loads(msg)
        assert parsed["type"] == "agent_stream_chunk"
        assert parsed["message_id"] == "m1"
        assert parsed["text"] == "hello"

    def test_tool_status(self):
        msg = encode_server_message(
            ServerMessageType.TOOL_STATUS, tool_name="gen_image", status="running"
        )
        parsed = json.loads(msg)
        assert parsed["type"] == "tool_status"
        assert parsed["tool_name"] == "gen_image"

    def test_scene_add(self):
        scene = {"id": "s1", "index": 0, "title": "Scene 1"}
        msg = encode_server_message(ServerMessageType.SCENE_ADD, scene=scene)
        parsed = json.loads(msg)
        assert parsed["type"] == "scene_add"
        assert parsed["scene"]["id"] == "s1"

    def test_error(self):
        msg = encode_server_message(ServerMessageType.ERROR, message="something broke")
        parsed = json.loads(msg)
        assert parsed["type"] == "error"
        assert parsed["message"] == "something broke"

    def test_encode_agent_idle(self):
        msg = encode_server_message(ServerMessageType.AGENT_IDLE)
        parsed = json.loads(msg)
        assert parsed["type"] == "agent_idle"


class TestDecodeClientMessage:
    def test_session_init(self):
        raw = json.dumps({"type": "session_init"})
        msg_type, payload = decode_client_message(raw)
        assert msg_type == ClientMessageType.SESSION_INIT

    def test_session_init_with_id(self):
        raw = json.dumps({"type": "session_init", "session_id": "abc"})
        msg_type, payload = decode_client_message(raw)
        assert msg_type == ClientMessageType.SESSION_INIT
        assert payload["session_id"] == "abc"

    def test_audio_data(self):
        raw = json.dumps({"type": "audio_data", "data": "base64stuff"})
        msg_type, payload = decode_client_message(raw)
        assert msg_type == ClientMessageType.AUDIO_DATA
        assert payload["data"] == "base64stuff"

    def test_text_message(self):
        raw = json.dumps({"type": "text_message", "text": "Hello"})
        msg_type, payload = decode_client_message(raw)
        assert msg_type == ClientMessageType.TEXT_MESSAGE
        assert payload["text"] == "Hello"

    def test_invalid_json(self):
        msg_type, payload = decode_client_message("not json{{{")
        assert msg_type is None
        assert "error" in payload

    def test_unknown_type(self):
        raw = json.dumps({"type": "bogus_type"})
        msg_type, payload = decode_client_message(raw)
        assert msg_type is None
        assert "error" in payload
