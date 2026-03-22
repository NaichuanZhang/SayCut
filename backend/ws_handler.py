"""WebSocket endpoint for the SayCut voice agent."""

import base64
import logging

from fastapi import WebSocket, WebSocketDisconnect

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
from backend.storybook_tools import STORYBOOK_TOOLS, execute_storybook_tool
from backend.voice_agent import VoiceAgent, STORYBOOK_SYSTEM_PROMPT
from backend.ws_protocol import (
    ClientMessageType,
    ServerMessageType,
    decode_client_message,
    encode_server_message,
)

logger = logging.getLogger(__name__)

# Module-level agent instance (created lazily)
_agent: VoiceAgent | None = None


def get_agent() -> VoiceAgent:
    global _agent
    if _agent is None:
        import os

        api_key = os.environ.get("BOSONAI_API_KEY", "EMPTY")
        _agent = VoiceAgent(api_key=api_key, tools=STORYBOOK_TOOLS)
    return _agent


async def websocket_endpoint(websocket: WebSocket):
    """Handle a WebSocket connection for the voice agent."""
    await websocket.accept()
    logger.info("WebSocket connected")

    session_id: str | None = None
    storybook_id: str | None = None
    db = await init_db(DB_PATH)

    async def _save_message(sid: str, role: str, text: str) -> None:
        await create_message(db, sid, role, text)

    async def _tool_executor(name: str, args: dict, send_event) -> dict:
        nonlocal storybook_id
        if name == "generate_script" and storybook_id is None:
            storybook_id = await create_storybook(db, session_id, "")
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
        if name == "generate_script" and "title" in result:
            await db.execute(
                "UPDATE storybooks SET title = ? WHERE id = ?",
                (result["title"], storybook_id),
            )
            await db.commit()
        return result

    try:
        while True:
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
                        # Don't restore full message history into voice agent —
                        # it includes internal messages (nudges, tool responses)
                        # that pollute the model context. Instead, rely on
                        # LOAD_STORYBOOK → inject_context() for resumed sessions.
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
                # Inject context into the voice agent so it knows about the existing storybook
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
                agent = get_agent()
                agent.inject_context(session_id, context)
                logger.info("Loaded storybook %s for session %s", storybook_id, session_id)

            elif msg_type == ClientMessageType.TEXT_MESSAGE:
                text = payload.get("text", "")
                agent = get_agent()

                async def send_event(event_type, **kwargs):
                    await websocket.send_text(
                        encode_server_message(ServerMessageType(event_type), **kwargs)
                    )

                try:
                    await agent.process_text(
                        session_id=session_id,
                        text=text,
                        send_event=send_event,
                        tool_executor=_tool_executor,
                        save_message=_save_message,
                    )
                except Exception:
                    logger.exception("Error processing text message")
                    await websocket.send_text(
                        encode_server_message(
                            ServerMessageType.ERROR, message="Failed to process text"
                        )
                    )
                finally:
                    logger.debug("Sending agent_idle after text processing")
                    await websocket.send_text(
                        encode_server_message(ServerMessageType.AGENT_IDLE)
                    )

            elif msg_type == ClientMessageType.AUDIO_DATA:
                audio_b64 = payload.get("data", "")
                audio_bytes = base64.b64decode(audio_b64)
                logger.debug("Received audio data, size=%d bytes", len(audio_bytes))
                agent = get_agent()

                async def send_event(event_type, **kwargs):
                    await websocket.send_text(
                        encode_server_message(ServerMessageType(event_type), **kwargs)
                    )

                try:
                    await agent.process_audio(
                        session_id=session_id,
                        audio_bytes=audio_bytes,
                        send_event=send_event,
                        tool_executor=_tool_executor,
                        save_message=_save_message,
                    )
                except Exception:
                    logger.exception("Error processing audio data")
                    await websocket.send_text(
                        encode_server_message(
                            ServerMessageType.ERROR, message="Failed to process audio"
                        )
                    )
                finally:
                    logger.debug("Sending agent_idle after audio processing")
                    await websocket.send_text(
                        encode_server_message(ServerMessageType.AGENT_IDLE)
                    )

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected (session=%s)", session_id)
    finally:
        await db.close()
