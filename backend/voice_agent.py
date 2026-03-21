"""Async voice agent — adapts assistant.py's interactive loop for WebSocket use."""

import json
import logging
import os
import tempfile
import uuid
from typing import Callable, Awaitable

logger = logging.getLogger(__name__)

from openai import AsyncOpenAI

from bosonUtil.api import (
    DEFAULT_BASE_URL,
    DEFAULT_MODEL,
    DEFAULT_TEMPERATURE,
    DEFAULT_TOP_P,
    DEFAULT_MAX_TOKENS,
    EXTRA_BODY,
    STOP_SEQUENCES,
)
from bosonUtil.tools import (
    MAX_TOOL_CALLS_PER_TURN,
    build_system_prompt,
    execute_tool_call,
    parse_tool_calls,
)

# Type for the event callback: async def send_event(event_type, **kwargs)
SendEvent = Callable[..., Awaitable[None]]

# Default system prompt for the storybook agent
STORYBOOK_SYSTEM_PROMPT = (
    "You are SayCut, an AI-powered visual storybook maker. "
    "Help users create interactive storybooks through voice conversation.\n\n"
    "WORKFLOW — follow this order automatically, do NOT wait for user confirmation between steps:\n"
    "1. When the user describes a story idea, call generate_script.\n"
    "2. After the script result comes back, IMMEDIATELY call generate_scene_image for ALL scenes.\n"
    "3. After all images are done, IMMEDIATELY call generate_scene_audio for ALL scenes.\n"
    "4. After all audio is done, IMMEDIATELY call generate_scene_video for ALL scenes.\n"
    "5. If the user asks to modify a scene's image, use edit_scene_image.\n\n"
    "CRITICAL RULES:\n"
    "- When you decide to use a tool, you MUST include <tool_call> tags. Never just describe what you will do.\n"
    "- After receiving a <tool_response>, immediately call the next tool(s) — do not stop to chat.\n"
    "- You can call multiple tools at once by putting multiple JSON objects in one <tool_call> tag.\n"
    "- Keep your text responses SHORT. Prioritize calling tools over narrating.\n\n"
    "IMPORTANT: Always begin your response by quoting what you heard from the user "
    'in the format: [Heard: "<transcript>"]\n'
    "Then proceed with your answer.\n\n"
    "Use Thinking."
)


class VoiceAgent:
    """Async voice agent with multi-turn conversation and tool calling."""

    def __init__(
        self,
        api_key: str,
        base_url: str = DEFAULT_BASE_URL,
        model: str = DEFAULT_MODEL,
        system_prompt: str = STORYBOOK_SYSTEM_PROMPT,
        tools_enabled: bool = True,
        tools: list[dict] | None = None,
    ):
        self._client = AsyncOpenAI(
            base_url=base_url,
            api_key=api_key,
            timeout=180.0,
            max_retries=3,
        )
        self._model = model
        self._system_prompt = build_system_prompt(
            system_prompt, tools_enabled, tools=tools
        )
        self._tools_enabled = tools_enabled
        # In-memory conversation history per session
        self._histories: dict[str, list[dict]] = {}

    def _ensure_history(self, session_id: str) -> list[dict]:
        if session_id not in self._histories:
            self._histories[session_id] = [
                {"role": "system", "content": self._system_prompt}
            ]
        return self._histories[session_id]

    def get_history(self, session_id: str) -> list[dict]:
        return list(self._histories.get(session_id, []))

    async def _create_stream(self, messages: list[dict]):
        """Create an async streaming chat completion. Separated for testability."""
        return await self._client.chat.completions.create(
            model=self._model,
            messages=messages,
            temperature=DEFAULT_TEMPERATURE,
            top_p=DEFAULT_TOP_P,
            max_tokens=DEFAULT_MAX_TOKENS,
            stop=STOP_SEQUENCES,
            extra_body=EXTRA_BODY,
            stream=True,
        )

    async def _stream_and_collect(
        self, messages: list[dict], send_event: SendEvent
    ) -> str:
        """Stream a response, sending events for each chunk. Returns full text."""
        message_id = uuid.uuid4().hex[:12]
        logger.debug("Streaming start, message_id=%s", message_id)
        await send_event("agent_stream_start", message_id=message_id)

        stream = await self._create_stream(messages)
        full_text = ""
        async for chunk in stream:
            delta = chunk.choices[0].delta
            if delta.content:
                full_text += delta.content
                await send_event(
                    "agent_stream_chunk", message_id=message_id, text=delta.content
                )

        logger.debug("Streaming end, message_id=%s, length=%d", message_id, len(full_text))
        await send_event("agent_stream_end", message_id=message_id)
        return full_text.strip()

    async def _handle_tool_calls(
        self,
        response_text: str,
        history: list[dict],
        send_event: SendEvent,
        tool_executor: Callable | None = None,
    ) -> str:
        """Process tool calls in the response, up to MAX_TOOL_CALLS_PER_TURN rounds."""
        did_execute_tool = False

        for round_num in range(MAX_TOOL_CALLS_PER_TURN):
            tool_calls = parse_tool_calls(response_text)

            if not tool_calls:
                if not did_execute_tool:
                    # No tool calls at all in the initial response — done
                    break
                # Model got a tool response but didn't chain the next tool call.
                # Nudge it once to continue the workflow.
                did_execute_tool = False
                logger.info("Nudging model to continue tool workflow")
                history.append({
                    "role": "user",
                    "content": "Continue — call the next tool(s) now.",
                })
                response_text = await self._stream_and_collect(history, send_event)
                history.append({"role": "assistant", "content": response_text})
                continue

            logger.info("Tool call round %d: %d calls detected", round_num + 1, len(tool_calls))

            for tc in tool_calls:
                tc_name = tc["name"]
                tc_args = tc["arguments"]
                logger.debug("Executing tool: %s", tc_name)

                if tool_executor:
                    result = await tool_executor(tc_name, tc_args, send_event)
                else:
                    await send_event("tool_status", tool_name=tc_name, status="running")
                    try:
                        result = execute_tool_call(tc_name, tc_args)
                    except Exception as e:
                        logger.error("Tool %s failed: %s", tc_name, e)
                        result = {"name": tc_name, "error": str(e)}
                    await send_event("tool_status", tool_name=tc_name, status="done")

                logger.debug("Tool %s result: %s", tc_name, result)

                tool_response = f"<tool_response>{json.dumps(result)}</tool_response>"
                history.append({"role": "user", "content": tool_response})

            did_execute_tool = True

            # Get follow-up response
            response_text = await self._stream_and_collect(history, send_event)
            history.append({"role": "assistant", "content": response_text})

        return response_text

    async def process_text(
        self,
        session_id: str,
        text: str,
        send_event: SendEvent,
        tool_executor: Callable | None = None,
    ) -> str:
        """Process a text input and stream the response."""
        history = self._ensure_history(session_id)
        logger.info("process_text session=%s, history_len=%d", session_id, len(history))

        await send_event("agent_thinking")

        history.append({"role": "user", "content": text})

        response_text = await self._stream_and_collect(history, send_event)
        history.append({"role": "assistant", "content": response_text})

        if self._tools_enabled:
            response_text = await self._handle_tool_calls(
                response_text, history, send_event, tool_executor
            )

        return response_text

    async def process_audio(
        self,
        session_id: str,
        audio_bytes: bytes,
        send_event: SendEvent,
        tool_executor: Callable | None = None,
    ) -> str:
        """Process audio bytes through the VAD pipeline and stream the response."""
        from bosonUtil.audio import chunk_audio_file

        history = self._ensure_history(session_id)
        logger.info(
            "process_audio session=%s, audio_size=%d, history_len=%d",
            session_id, len(audio_bytes), len(history),
        )

        await send_event("agent_thinking")

        # Write bytes to temp file for chunk_audio_file
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name

        try:
            audio_chunks, meta = chunk_audio_file(tmp_path)
        finally:
            os.unlink(tmp_path)

        # Build audio content parts with indexed MIME types
        user_content = [
            {
                "type": "audio_url",
                "audio_url": {"url": f"data:audio/wav_{i};base64,{chunk_b64}"},
            }
            for i, chunk_b64 in enumerate(audio_chunks)
        ]
        history.append({"role": "user", "content": user_content})

        response_text = await self._stream_and_collect(history, send_event)
        history.append({"role": "assistant", "content": response_text})

        if self._tools_enabled:
            response_text = await self._handle_tool_calls(
                response_text, history, send_event, tool_executor
            )

        return response_text
