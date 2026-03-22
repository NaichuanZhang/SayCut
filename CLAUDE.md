# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

SayCut is an AI-powered visual audio storybook maker. Users create interactive storybooks through voice conversation. The stack is Next.js frontend + FastAPI backend, with AI models served by BosonAI (voice agent) and EigenAI (image gen, video gen, TTS, script LLM). Core utilities live in `bosonUtil/`. `assistant.py` is a standalone CLI demo of the voice agent, not the production entry point.

SayCut supports two modes:
- **Story mode**: Single narrator with `narration_text` per scene, single TTS voice ("Linda")
- **Movie mode**: 2-person conversational scripts with `dialogue_lines` per scene, 3 voices (Narrator via Morgan Freeman voice_id + 2 characters), multi-voice TTS via WAV concatenation

## Setup

```bash
uv sync
export BOSONAI_API_KEY="your-key"   # Voice agent (hackathon.boson.ai)
export EIGENAI_API_KEY="your-key"   # Image, video, TTS, script LLM (api-web.eigenai.com)
```

## Commands

```bash
# Run the backend (FastAPI + WebSocket on port 3001)
uv run uvicorn backend.main:app --port 3001

# Run the frontend (Next.js on port 3000)
cd frontend && npm run dev

# Run the CLI demo (standalone, all flags optional)
uv run python assistant.py
uv run python assistant.py --system-prompt "You are an ASR system." --no-tools
uv run python assistant.py --model higgs-audio-understanding-v3-Hackathon

# Unit tests (no API key needed)
uv run pytest tests/ -m "not integration" -v

# Integration tests (requires BOSONAI_API_KEY)
uv run pytest tests/ -m integration -v

# Run a single test class or method
uv run pytest tests/test_integration.py::TestParseToolCalls -v
uv run pytest tests/test_integration.py::TestSafeEvalMath::test_basic_addition -v
```

## Architecture

**Stack**: Next.js frontend → FastAPI backend → BosonAI + EigenAI APIs. Generated assets stored on local filesystem.

**Routes**: `/` — projects listing page (shows mode badge on movie projects); `/project/new` — mode selection screen (Story vs Movie) then editor; `/project/[id]` — resume editing existing storybook (hydrates scenes + conversation history + mode/characters from REST, connects fresh WS session with `LOAD_STORYBOOK` to inject context into voice agent — full message history is NOT restored into the voice model to avoid polluting context).

**Production data flow**: Browser mic → `useAudioRecorder` (16kHz PCM → WAV → base64) → `useAgent` → `WSClient` (WebSocket) → `ws_handler.py` → `VoiceAgent` → `audio.py` (VAD → 4s chunks) → BosonAI API → streamed response → WebSocket events → frontend stores

**Tool use flow** (v3.5): `build_system_prompt()` injects `<tools>` JSON into system prompt (accepts custom tool defs via `tools` param) → model responds with `<tool_call>` tags → `parse_tool_calls` extracts & normalizes → tool executor runs the tool → result sent back as `<tool_response>` → model generates follow-up (up to 6 rounds). In production, `ws_handler.py` creates a per-session `VoiceAgent` configured with mode-specific tools (`STORY_TOOLS` or `MOVIE_TOOLS`) + corresponding system prompt + a `tool_executor` closure that lazily creates a storybook and delegates to `execute_storybook_tool()`. An auto-nudge mechanism re-prompts the model if it narrates intent without calling a tool after a tool response. Tool responses sent back to the model are text-only (scene IDs, titles, status) — asset URLs are delivered to the frontend via `send_event` instead.

**Storybook creation flow — Story mode** (voice-driven, multi-turn):
1. User describes a story via voice → model calls `generate_script` → storybook + scenes created in DB → `scene_add` events sent to frontend
2. Model chains `generate_scene_image` for all scenes → images saved, `scene_update` events with `imageUrl`
3. Model chains `generate_scene_audio` for all scenes → TTS audio saved, `scene_update` events with `audioUrl`
4. Model chains `generate_scene_video` for all scenes → video saved, `scene_update` events with `videoUrl`
5. User can request edits ("make the kitten bigger in scene 2") → `edit_scene_image`
6. User can insert scenes between existing ones ("add a scene between 1 and 2") → `generate_script` with `insert_after_scene_id` → backend shifts existing scene indices, inserts new scenes, sends `scene_update` events with `field="index"` for shifted scenes
7. User can remove scenes ("remove scene 3") → `remove_scene` → deletes scene row + asset files, shifts remaining indices backward, sends `scene_remove` event + `scene_update` events for re-indexed scenes

**Storybook creation flow — Movie mode** (same pattern, different tools):
1. User describes a movie idea → model calls `generate_movie_script` → scenes with `dialogue_lines` JSON → `scene_add` events include `dialogueLines`
2. Model chains `generate_scene_image` (shared tool)
3. Model chains `generate_scene_dialogue_audio` → reads dialogue_lines + character voice map from DB, synthesizes each line with correct voice, concatenates WAVs with silence gaps
4. Model chains `generate_scene_video` (shared tool)

**AI Models**:
- Voice Agent (STT + tool calling): `higgs-audio-understanding-v3.5-Hackathon` via BosonAI (`hackathon.boson.ai/v1`)
- Script Generation: `kimi-k2-5` via EigenAI (`api-web.eigenai.com`, OpenAI-compatible)
- Image Generation: `eigen-image` via EigenAI (`api-web.eigenai.com`)
- Image Editing: `qwen-image-edit-2511` via EigenAI (multipart upload, up to 9 source images)
- Image-to-Video: `wan2p2-i2v-14b-turbo` via EigenAI (async: submit → poll → download MP4)
- Text-to-Speech: `higgs2p5` via EigenAI (`data.eigenai.com`, WebSocket streaming)

**Key modules**:
- `backend/main.py` — FastAPI app, mounts `/assets` static files, exposes `/ws` WebSocket, `/health`, and REST endpoints `GET /api/storybooks` (list), `GET /api/storybooks/{id}` (detail with scenes), `GET /api/storybooks/{id}/messages` (conversation history)
- `backend/ws_handler.py` — WebSocket endpoint: session init, `SET_PROJECT_MODE` (sets mode + characters), `load_storybook` (resume existing, reconfigures agent for mode), per-session `VoiceAgent` with mode-specific tools/prompt, `tool_executor` closure with lazy storybook creation, routes `audio_data`/`text_message` to `VoiceAgent`
- `backend/ws_protocol.py` — Message type enums (`ClientMessageType` incl. `LOAD_STORYBOOK`, `SET_PROJECT_MODE`, `ServerMessageType` incl. `STORYBOOK_CREATED`, `SCENE_REMOVE`), encode/decode helpers
- `backend/voice_agent.py` — Async `VoiceAgent` class: streaming responses, multi-turn history with sliding-window truncation (`MAX_HISTORY_MESSAGES=20`), tool call loop with auto-nudge, custom tools injection via `tools` param, `inject_context()` for resumed storybooks; `STORY_SYSTEM_PROMPT` + `MOVIE_SYSTEM_PROMPT` with `get_system_prompt_for_mode()`
- `backend/storybook_tools.py` — `STORY_TOOLS` + `MOVIE_TOOLS` (mode-specific tool sets with shared image/video/edit/remove tools), `get_tools_for_mode()`; async executors for script, movie_script, image, audio, dialogue_audio, video, edit, remove; `generate_movie_script` stores `dialogue_lines` JSON per scene; `generate_scene_dialogue_audio` reads dialogue + voice map from DB, synthesizes per-line, concatenates WAVs
- `backend/db.py` — Async SQLite layer (sessions, storybooks, scenes, messages) via `aiosqlite`; includes `shift_scene_indices()` for scene insertion, `delete_scene()` for removal with index compaction, `list_storybooks()` and `get_storybook_with_scenes()` for REST endpoints
- `backend/asset_storage.py` — Save/serve/delete generated assets on local filesystem
- `backend/config.py` — Env vars, paths (`ASSETS_DIR`, `DB_PATH`), `BACKEND_PORT`
- `bosonUtil/audio_concat.py` — WAV concatenation utility for multi-voice dialogue: normalizes to 24kHz/16-bit/mono, inserts configurable silence gaps between segments
- `bosonUtil/audio.py` — Audio chunking pipeline; VAD model is cached as a module-level singleton
- `bosonUtil/api.py` — API config constants, `build_messages()`, and `predict()` for one-shot calls
- `bosonUtil/tools.py` — Tool definitions, `<tool_call>` tag parsing (handles array/object/nested formats + truncated calls), `build_system_prompt()` with custom tools param, safe math eval
- `frontend/app/lib/wsClient.ts` — `WSClient` class: WebSocket connection with auto-reconnect, `sendLoadStorybook()` for resume flow
- `frontend/app/lib/api.ts` — REST client: `fetchStorybooks()`, `fetchStorybook(id)`, and `fetchMessages(id)` for projects page, editor hydration, and conversation history
- `frontend/app/lib/editorContext.ts` — React context to pass `storybookId` down to `useAgent` via `VoiceOrb`
- `frontend/app/hooks/useAgent.ts` — React hook: connects WSClient, dispatches server messages to stores; accepts optional `storybookId` to send `LOAD_STORYBOOK` on resume, `projectMode`/`projectCharacters` to send `SET_PROJECT_MODE` on init
- `frontend/app/hooks/useAudioRecorder.ts` — React hook: browser mic → 16kHz PCM WAV → base64
- `frontend/app/components/ProjectCard.tsx` — Card component for projects listing: thumbnail, title, scene count, relative date
- `frontend/app/components/ModeSelector.tsx` — Mode selection screen for new projects: Story vs Movie cards, character name/voice config for movie mode, voice sample preview
- `frontend/app/components/SceneEditor.tsx` — Scene thumbnail grid; renders dialogue lines (movie) or narration textarea (story); prefers `<video>` over `<img>` when `videoUrl` exists
- `frontend/app/components/PlayerOverlay.tsx` — Full-screen cinematic player with crossfade; shows stacked dialogue subtitles (movie) or single narration text (story); plays narration audio alongside looping video, advances scenes on audio `ended` event (falls back to 6s timer when no `audioUrl`); prefers `<video>` over `<img>` when `videoUrl` exists
- `assistant.py` — Standalone CLI demo of the voice agent (not the production entry point)

## HiggsAudioM3 API Specs

### Endpoint & Auth
- Base URL: `https://hackathon.boson.ai/v1`
- Model: `higgs-audio-understanding-v3.5-Hackathon`
- Auth: Bearer token via `BOSONAI_API_KEY` env var
- OpenAI-compatible chat completions API

### Audio Requirements
- **Sample rate**: Must be 16kHz — resample before sending
- **Chunking**: Max 4 seconds per chunk (64,000 samples). Use Silero VAD to segment, then split long segments
- **Min chunk length**: ~0.1s (1,600 samples) — zero-pad shorter chunks
- **Encoding**: Each chunk is base64-encoded 16-bit PCM WAV
- **MIME type**: Must use indexed format `audio/wav_{i}` (not plain `audio/wav`) to preserve chunk ordering

### Message Format
Audio chunks go as `audio_url` content parts in a user message:
```json
{
  "type": "audio_url",
  "audio_url": {"url": "data:audio/wav_0;base64,<base64-data>"}
}
```
Optional text can precede audio chunks in the same user message (used for ASR instructions).

### Required API Parameters
- **stop sequences** (do not modify): `["<|eot_id|>", "<|endoftext|>", "<|audio_eos|>", "<|im_end|>"]`
- **extra_body** (do not modify): `{"skip_special_tokens": false}`
- Default generation: `temperature=0.2`, `top_p=0.9`, `max_tokens=4096`

### Prompt Patterns
- **General chat**: System prompt only; audio is the user input
- **ASR**: Both `system_prompt` and `user_text` (text goes before audio chunks)
- **Thinking mode** (v3.5): Append `"Use Thinking."` to system prompt (both words capitalized)
- **Tool use** (v3.5): Embed tool definitions in `<tools>...</tools>` within system prompt

### Tool Use Flow (v3.5)
1. Define tools as JSON in `<tools>{"tools": [...]}</tools>` block in system prompt
2. Model responds with `<tool_call>...</tool_call>` tags containing JSON
3. Tool call JSON may be an array or object, with nested `function` field or flat format
4. Execute tool locally, send result back as user message: `<tool_response>{"name": "...", "result": ...}</tool_response>`
5. Model generates final answer (or another tool call — loop up to 6 times)

### Multi-turn Conversations
- Append messages to the list as normal (system → user → assistant → user → ...)
- Chunk indices (`wav_0`, `wav_1`, ...) reset per user message

## Critical Constraints — Do Not Modify
- Stop sequences and extra_body in `bosonUtil/api.py`
- VAD + 4-second chunking logic in `bosonUtil/audio.py`
- Indexed MIME type format `audio/wav_{i}`

