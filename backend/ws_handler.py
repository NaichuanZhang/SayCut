"""WebSocket endpoint for the SayCut voice agent."""

import base64
import json
import logging
import os

from fastapi import WebSocket
from starlette.websockets import WebSocketDisconnect

from backend.db import (
    create_message,
    create_session,
    create_storybook,
    get_messages_by_session,
    get_scenes_by_storybook,
    get_session,
    get_storybook,
    init_db,
)
from backend.config import ASSETS_DIR, DB_PATH
from backend.storybook_tools import STORY_TOOLS, MOVIE_TOOLS, get_tools_for_mode, execute_storybook_tool
from backend.voice_agent import VoiceAgent, STORY_SYSTEM_PROMPT, get_system_prompt_for_mode
from backend.ws_protocol import (
    ClientMessageType,
    ServerMessageType,
    decode_client_message,
    encode_server_message,
)

logger = logging.getLogger(__name__)


def _create_agent(mode: str = "story") -> VoiceAgent:
    """Create a VoiceAgent configured for the given mode."""
    api_key = os.environ.get("BOSONAI_API_KEY", "EMPTY")
    return VoiceAgent(
        api_key=api_key,
        system_prompt=get_system_prompt_for_mode(mode),
        tools=get_tools_for_mode(mode),
    )


async def websocket_endpoint(websocket: WebSocket):
    """Handle a WebSocket connection for the voice agent."""
    await websocket.accept()
    logger.info("WebSocket connected")

    session_id: str | None = None
    storybook_id: str | None = None
    storybook_mode: str = "story"
    storybook_characters: str | None = None  # JSON string
    agent: VoiceAgent | None = None
    db = await init_db(DB_PATH)

    ws_closed = False

    async def _safe_send(msg: str) -> None:
        """Send a message, silently ignoring if the connection is already closed."""
        nonlocal ws_closed
        if ws_closed:
            return
        try:
            await websocket.send_text(msg)
        except (RuntimeError, WebSocketDisconnect):
            ws_closed = True
            logger.info("WS connection closed — further sends will be skipped")

    def _get_agent() -> VoiceAgent:
        nonlocal agent
        if agent is None:
            agent = _create_agent(storybook_mode)
        return agent

    def _reconfigure_agent(mode: str) -> VoiceAgent:
        nonlocal agent, storybook_mode
        storybook_mode = mode
        agent = _create_agent(mode)
        return agent

    async def _save_message(sid: str, role: str, text: str) -> None:
        await create_message(db, sid, role, text)

    async def _tool_executor(name: str, args: dict, send_event) -> dict:
        nonlocal storybook_id
        # Lazy storybook creation on first script generation
        script_tools = ("generate_script", "generate_movie_script")
        if name in script_tools and storybook_id is None:
            storybook_id = await create_storybook(
                db, session_id, "",
                mode=storybook_mode,
                characters=storybook_characters,
            )
            await send_event(
                "storybook_created", storybook_id=storybook_id
            )
        if storybook_id is None:
            return {
                "name": name,
                "error": "No storybook yet. Please generate a script first.",
            }
        result = await execute_storybook_tool(
            name,
            args,
            send_event=send_event,
            db=db,
            session_id=session_id,
            storybook_id=storybook_id,
            assets_dir=ASSETS_DIR,
        )
        if name in script_tools and "title" in result:
            await db.execute(
                "UPDATE storybooks SET title = ? WHERE id = ?",
                (result["title"], storybook_id),
            )
            await db.commit()
        return result

    try:
        while not ws_closed:
            raw = await websocket.receive_text()
            msg_type, payload = decode_client_message(raw)

            if msg_type is None:
                logger.warning("Invalid message: %s", payload.get("error"))
                await websocket.send_text(
                    encode_server_message(
                        ServerMessageType.ERROR, message=payload.get("error", "Unknown error")
                    )
                )
                continue

            logger.debug("Received message type=%s", msg_type.value)

            # Require session_init before any other message
            if session_id is None and msg_type != ClientMessageType.SESSION_INIT:
                await websocket.send_text(
                    encode_server_message(
                        ServerMessageType.ERROR, message="Must send session_init first"
                    )
                )
                continue

            if msg_type == ClientMessageType.SESSION_INIT:
                requested_id = payload.get("session_id")
                if requested_id:
                    existing = await get_session(db, requested_id)
                    if existing:
                        session_id = requested_id
                        logger.info("Resuming existing session %s", session_id)
                    else:
                        session_id = await create_session(db)
                else:
                    session_id = await create_session(db)

                logger.info("Session initialized: %s", session_id)
                await websocket.send_text(
                    encode_server_message(
                        ServerMessageType.SESSION_CREATED, session_id=session_id
                    )
                )

            elif msg_type == ClientMessageType.SET_PROJECT_MODE:
                mode = payload.get("mode", "story")
                characters = payload.get("characters")
                storybook_characters = json.dumps(characters) if characters else None
                _reconfigure_agent(mode)
                logger.info("Project mode set to %s (characters=%s)", mode, storybook_characters)

            elif msg_type == ClientMessageType.LOAD_STORYBOOK:
                requested_storybook_id = payload.get("storybook_id")
                if not requested_storybook_id:
                    await websocket.send_text(
                        encode_server_message(
                            ServerMessageType.ERROR, message="Missing storybook_id"
                        )
                    )
                    continue
                sb = await get_storybook(db, requested_storybook_id)
                if sb is None:
                    await websocket.send_text(
                        encode_server_message(
                            ServerMessageType.ERROR, message="Storybook not found"
                        )
                    )
                    continue
                storybook_id = requested_storybook_id
                # Reconfigure agent for the storybook's mode
                mode = sb.get("mode", "story")
                storybook_characters = sb.get("characters")
                current_agent = _reconfigure_agent(mode)
                # Inject context into the voice agent
                scenes = await get_scenes_by_storybook(db, storybook_id)
                scene_titles = ", ".join(
                    f'Scene {s["idx"] + 1} (id="{s["id"]}"): "{s["title"]}"'
                    for s in scenes
                )
                context = (
                    f'Previously, you created a storybook titled "{sb["title"]}" '
                    f"with {len(scenes)} scenes: {scene_titles}. "
                    "The user is resuming work on this storybook."
                )
                current_agent.inject_context(session_id, context)
                logger.info("Loaded storybook %s (mode=%s) for session %s", storybook_id, mode, session_id)

            elif msg_type == ClientMessageType.TEXT_MESSAGE:
                text = payload.get("text", "")
                current_agent = _get_agent()

                async def send_event(event_type, **kwargs):
                    await _safe_send(
                        encode_server_message(ServerMessageType(event_type), **kwargs)
                    )

                try:
                    await current_agent.process_text(
                        session_id=session_id,
                        text=text,
                        send_event=send_event,
                        tool_executor=_tool_executor,
                        save_message=_save_message,
                    )
                except Exception:
                    logger.exception("Error processing text message")
                    await _safe_send(
                        encode_server_message(
                            ServerMessageType.ERROR, message="Failed to process text"
                        )
                    )
                finally:
                    logger.debug("Sending agent_idle after text processing")
                    await _safe_send(
                        encode_server_message(ServerMessageType.AGENT_IDLE)
                    )

            elif msg_type == ClientMessageType.AUDIO_DATA:
                audio_b64 = payload.get("data", "")
                audio_bytes = base64.b64decode(audio_b64)
                logger.debug("Received audio data, size=%d bytes", len(audio_bytes))
                current_agent = _get_agent()

                async def send_event(event_type, **kwargs):
                    await _safe_send(
                        encode_server_message(ServerMessageType(event_type), **kwargs)
                    )

                try:
                    await current_agent.process_audio(
                        session_id=session_id,
                        audio_bytes=audio_bytes,
                        send_event=send_event,
                        tool_executor=_tool_executor,
                        save_message=_save_message,
                    )
                except Exception:
                    logger.exception("Error processing audio data")
                    await _safe_send(
                        encode_server_message(
                            ServerMessageType.ERROR, message="Failed to process audio"
                        )
                    )
                finally:
                    logger.debug("Sending agent_idle after audio processing")
                    await _safe_send(
                        encode_server_message(ServerMessageType.AGENT_IDLE)
                    )

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected (session=%s)", session_id)
    finally:
        await db.close()
