"""Tests for backend.ws_handler — WebSocket endpoint."""

import json

import pytest
from fastapi.testclient import TestClient

from backend.main import app


class TestWebSocketHandler:
    def test_session_init_creates_session(self):
        """Send session_init, receive session_created."""
        client = TestClient(app)
        with client.websocket_connect("/ws") as ws:
            ws.send_json({"type": "session_init"})
            response = ws.receive_json()
            assert response["type"] == "session_created"
            assert "session_id" in response

    def test_session_init_with_existing_id(self):
        """Resume a session by providing an existing session_id."""
        client = TestClient(app)
        with client.websocket_connect("/ws") as ws:
            ws.send_json({"type": "session_init"})
            first = ws.receive_json()
            session_id = first["session_id"]

        # Reconnect with same session_id
        with client.websocket_connect("/ws") as ws:
            ws.send_json({"type": "session_init", "session_id": session_id})
            response = ws.receive_json()
            assert response["type"] == "session_created"
            assert response["session_id"] == session_id

    def test_missing_session_init_errors(self):
        """Sending data before session_init returns an error."""
        client = TestClient(app)
        with client.websocket_connect("/ws") as ws:
            ws.send_json({"type": "text_message", "text": "hello"})
            response = ws.receive_json()
            assert response["type"] == "error"

    def test_text_message_sends_agent_idle_after_response(self):
        """After processing a text_message, the last event should be agent_idle."""
        from unittest.mock import patch, AsyncMock
        from backend.voice_agent import VoiceAgent

        async def mock_process_text(session_id, text, send_event, tool_executor=None):
            await send_event("agent_thinking")
            await send_event("agent_stream_start", message_id="m1")
            await send_event("agent_stream_chunk", message_id="m1", text="Hi!")
            await send_event("agent_stream_end", message_id="m1")
            return "Hi!"

        client = TestClient(app)
        with client.websocket_connect("/ws") as ws:
            ws.send_json({"type": "session_init"})
            resp = ws.receive_json()
            assert resp["type"] == "session_created"

            with patch.object(VoiceAgent, "process_text", side_effect=mock_process_text):
                ws.send_json({"type": "text_message", "text": "hello"})

                # Collect all messages until agent_idle
                messages = []
                for _ in range(10):
                    msg = ws.receive_json()
                    messages.append(msg)
                    if msg["type"] == "agent_idle":
                        break

                types = [m["type"] for m in messages]
                assert "agent_idle" in types
                assert types[-1] == "agent_idle"
