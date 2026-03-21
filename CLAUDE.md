# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

SayCut is an AI-powered visual audio storybook maker. Users create interactive storybooks through voice conversation. The stack is Next.js frontend + FastAPI backend, with AI models served by BosonAI (voice agent) and EigenAI (image gen, video gen, TTS, script LLM). Core utilities live in `bosonUtil/`. `assistant.py` is a standalone CLI demo of the voice agent, not the production entry point.

## Setup

```bash
uv sync
export BOSONAI_API_KEY="your-key"   # Voice agent (hackathon.boson.ai)
export EIGENAI_API_KEY="your-key"   # Image, video, TTS, script LLM (api-web.eigenai.com)
uv run python assistant.py
```

## Commands

```bash
# Run the assistant (all flags optional)
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

**Voice agent data flow**: Audio file → `audio.py` (load → resample 16kHz → Silero VAD → 4s chunk → base64 WAV) → `api.py` (build messages → OpenAI-compatible call) → text response

**Tool use flow** (v3.5): `tools.py` injects `<tools>` JSON into system prompt → model responds with `<tool_call>` tags → `parse_tool_calls` extracts & normalizes → `execute_tool_call` runs locally → result sent back as `<tool_response>` → model generates final answer (up to 3 rounds)

**AI Models**:
- Voice Agent (STT + tool calling): `higgs-audio-understanding-v3.5-Hackathon` via BosonAI (`hackathon.boson.ai/v1`)
- Script Generation: `gpt-oss-120b` via EigenAI (`api-web.eigenai.com`, OpenAI-compatible)
- Image Generation: `eigen-image` via EigenAI (`api-web.eigenai.com`)
- Image Editing: `qwen-image-edit-2511` via EigenAI (multipart upload, up to 9 source images)
- Image-to-Video: `wan2p2-i2v-14b-turbo` via EigenAI (async: submit → poll → download MP4)
- Text-to-Speech: `higgs2p5` via EigenAI (`data.eigenai.com`, WebSocket streaming)

**Key modules**:
- `bosonUtil/audio.py` — Audio chunking pipeline; VAD model is cached as a module-level singleton
- `bosonUtil/api.py` — API config constants, `build_messages()`, and `predict()` for one-shot calls
- `bosonUtil/tools.py` — Tool definitions, `<tool_call>` tag parsing (handles array/object/nested formats), safe math eval
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
- Default generation: `temperature=0.2`, `top_p=0.9`, `max_tokens=2048`

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
5. Model generates final answer (or another tool call — loop up to 3 times)

### Multi-turn Conversations
- Append messages to the list as normal (system → user → assistant → user → ...)
- Chunk indices (`wav_0`, `wav_1`, ...) reset per user message

## Critical Constraints — Do Not Modify
- Stop sequences and extra_body in `bosonUtil/api.py`
- VAD + 4-second chunking logic in `bosonUtil/audio.py`
- Indexed MIME type format `audio/wav_{i}`

