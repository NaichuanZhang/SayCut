"""Tests for backend.voice_agent — async voice agent with mocked OpenAI."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.voice_agent import VoiceAgent
from bosonUtil.tools import MAX_TOOL_CALLS_PER_TURN


def _make_mock_chunk(content: str | None, finish_reason: str | None = None):
    """Create a mock streaming chunk."""
    delta = MagicMock()
    delta.content = content
    choice = MagicMock()
    choice.delta = delta
    choice.finish_reason = finish_reason
    chunk = MagicMock()
    chunk.choices = [choice]
    return chunk


class _MockStream:
    """Async iterable that yields mock streaming chunks."""

    def __init__(self, texts: list[str]):
        self._texts = texts

    def __aiter__(self):
        return self._iter()

    async def _iter(self):
        for t in self._texts:
            yield _make_mock_chunk(t)
        yield _make_mock_chunk(None, finish_reason="stop")


def _make_mock_stream(texts: list[str]):
    """Create an async iterator of mock streaming chunks."""
    return _MockStream(texts)


@pytest.mark.asyncio
async def test_process_text_input():
    """Text input produces streamed response via send_event callback."""
    events = []

    async def send_event(event_type, **kwargs):
        events.append({"type": event_type, **kwargs})

    agent = VoiceAgent(api_key="test-key")

    mock_stream = _make_mock_stream(["Hello", " there", "!"])

    with patch.object(agent, "_create_stream", return_value=mock_stream):
        await agent.process_text(
            session_id="s1", text="Hi", send_event=send_event
        )

    event_types = [e["type"] for e in events]
    assert "agent_thinking" in event_types
    assert "agent_stream_start" in event_types
    assert "agent_stream_chunk" in event_types
    assert "agent_stream_end" in event_types


@pytest.mark.asyncio
async def test_conversation_history_maintained():
    """Second call includes prior messages in context."""
    agent = VoiceAgent(api_key="test-key")
    send_event = AsyncMock()

    mock_stream1 = _make_mock_stream(["First response"])
    mock_stream2 = _make_mock_stream(["Second response"])

    with patch.object(agent, "_create_stream", side_effect=[mock_stream1, mock_stream2]):
        await agent.process_text(session_id="s1", text="Hi", send_event=send_event)
        await agent.process_text(session_id="s1", text="Follow up", send_event=send_event)

    history = agent.get_history("s1")
    # system + user1 + assistant1 + user2 + assistant2
    assert len(history) >= 5
    roles = [m["role"] for m in history]
    assert roles.count("user") == 2
    assert roles.count("assistant") == 2


@pytest.mark.asyncio
async def test_tool_call_detected_and_executed():
    """Response with <tool_call> triggers tool execution + follow-up."""
    events = []

    async def send_event(event_type, **kwargs):
        events.append({"type": event_type, **kwargs})

    agent = VoiceAgent(api_key="test-key")

    tool_response_text = '<tool_call>{"name": "calculate", "arguments": {"expression": "2+2"}}</tool_call>'
    mock_stream1 = _make_mock_stream([tool_response_text])
    mock_stream2 = _make_mock_stream(["The answer is 4"])
    # After tool result, model responds without tool call → nudge fires → final response
    mock_stream3 = _make_mock_stream(["All done!"])

    with patch.object(agent, "_create_stream", side_effect=[mock_stream1, mock_stream2, mock_stream3]):
        await agent.process_text(
            session_id="s1", text="What is 2+2?", send_event=send_event
        )

    event_types = [e["type"] for e in events]
    assert "tool_status" in event_types


@pytest.mark.asyncio
async def test_max_tool_call_rounds():
    """Stops after MAX_TOOL_CALLS_PER_TURN rounds."""
    agent = VoiceAgent(api_key="test-key")
    send_event = AsyncMock()

    tool_text = '<tool_call>{"name": "calculate", "arguments": {"expression": "1+1"}}</tool_call>'
    # Create MAX+1 streams that all return tool calls — should only process MAX
    streams = [_make_mock_stream([tool_text]) for _ in range(MAX_TOOL_CALLS_PER_TURN + 1)]
    final_stream = _make_mock_stream(["done"])
    streams.append(final_stream)

    with patch.object(agent, "_create_stream", side_effect=streams):
        await agent.process_text(
            session_id="s1", text="loop", send_event=send_event
        )

    # Count how many times tool_status was sent (start + end per round)
    tool_events = [
        c for c in send_event.call_args_list
        if c.args[0] == "tool_status" or (c.kwargs and c.kwargs.get("event_type") == "tool_status")
    ]
    assert len(tool_events) <= MAX_TOOL_CALLS_PER_TURN * 2
