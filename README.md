# SayCut

**An AI-powered visual audio storybook maker — create interactive storybooks just by talking.**

SayCut lets you build rich, narrated visual storybooks through natural voice conversation. Powered by BosonAI's HiggsAudioM3 voice agent, you describe your characters, plot, and style — and SayCut handles the rest: generating scripts, illustrations, narration, and video.

## How It Works

SayCut guides you through five phases, all driven by voice interaction:

### 1. Story Setup

Start by talking to the voice agent. Describe your characters, setting, and the tone you're going for. Pick an art style — watercolor, pixel art, anime, or something else entirely. The agent extracts structured details from your conversation and generates character portraits for you to confirm before moving on.

### 2. Script Generation

The agent writes a scene-by-scene script with narration and dialogue, assigning roles to each character. You can ask it to read the script back, then revise on the fly — "make the ending funnier" or "add a plot twist in scene three."

### 3. Storyboard

Key frame images are generated for each scene, keeping character appearances consistent throughout. Review the frames and request changes — "make the dragon bigger" or "change the background to a forest."

### 4. Production

Once you approve the storyboard, SayCut assembles everything:
- Generates video sequences from the key frames (image-to-video)
- Produces narration audio via text-to-speech
- Combines visuals and audio into the final storybook

### 5. Playback & Edit

Watch your completed storybook. If something isn't right, tell the agent which scene to revise and it regenerates just that part.

## Tech Stack

```
┌─────────────────────────────────┐
│        Next.js Frontend         │
│  Voice Input / Storyboard UI   │
│       Video Playback            │
└──────────────┬──────────────────┘
               │ REST + WebSocket
┌──────────────▼──────────────────┐
│        FastAPI Backend          │
│   Workflow Orchestration        │
│   bosonUtil/ (audio, api, tools)│
│   Local File Storage            │
└──────────────┬──────────────────┘
               │
    ┌──────────┴──────────┐
    ▼                     ▼
┌────────────┐   ┌───────────────┐
│  BosonAI   │   │   EigenAI     │
│  Voice     │   │  Image Gen    │
│  Agent     │   │  Image Edit   │
│            │   │  Image→Video  │
│            │   │  TTS          │
│            │   │  Script LLM   │
└────────────┘   └───────────────┘
```

### Frontend

- **Next.js** (React) — Web-based storybook creation UI
- **Web Audio API / MediaRecorder** — Browser-native voice capture
- Visual storyboard editor for reviewing and reordering scene frames
- Integrated video player for final storybook playback

### Backend

- **FastAPI** (Python) — Async API server with WebSocket support for streaming
- Orchestrates the 5-phase workflow (setup, script, storyboard, production, playback)
- Reuses existing `bosonUtil/` modules for voice agent integration
- **Local filesystem** for generated assets (images, videos, audio)

### AI Models

All models are served by **BosonAI** and **EigenAI** APIs:

| Role | Model | Provider | Protocol |
|------|-------|----------|----------|
| Voice Agent (STT + tool calling) | `higgs-audio-understanding-v3.5-Hackathon` | BosonAI | OpenAI-compatible REST |
| Script Generation | `gpt-oss-120b` | EigenAI | OpenAI-compatible REST |
| Image Generation | `eigen-image` | EigenAI | REST |
| Image Editing | `qwen-image-edit-2511` | EigenAI | REST, multipart upload |
| Image-to-Video | `wan2p2-i2v-14b-turbo` | EigenAI | Async REST with polling |
| Text-to-Speech | `higgs2p5` | EigenAI | WebSocket streaming |

**Key integration patterns:**
- **Image-to-video** is asynchronous — submit a job, poll for status, then download the result MP4
- **TTS** streams PCM audio chunks over WebSocket for real-time playback
- **Image editing** accepts up to 9 source images per request, enabling character consistency across scenes

## Setup

```bash
uv sync
export BOSONAI_API_KEY="your-key"   # Voice agent (hackathon.boson.ai)
export EIGENAI_API_KEY="your-key"   # Image, video, TTS, script LLM (api-web.eigenai.com)
uv run python assistant.py
```

### CLI Demo

`assistant.py` is a standalone CLI demo of the voice agent (not the production entry point):

```bash
uv run python assistant.py
uv run python assistant.py --system-prompt "You are an ASR system." --no-tools
uv run python assistant.py --model higgs-audio-understanding-v3-Hackathon
```

## Architecture

- **`bosonUtil/audio.py`** — Audio chunking pipeline: load, resample to 16kHz, Silero VAD segmentation, 4-second chunking, base64 WAV encoding.
- **`bosonUtil/api.py`** — API configuration, message building, and prediction calls against the OpenAI-compatible endpoint.
- **`bosonUtil/tools.py`** — Tool definitions, `<tool_call>` tag parsing, and safe math evaluation.
- **`assistant.py`** — CLI demo: multi-turn voice conversation with streaming responses and tool call loop.

## Tests

```bash
# Unit tests (no API key needed)
uv run pytest tests/ -m "not integration" -v

# Integration tests (requires BOSONAI_API_KEY)
uv run pytest tests/ -m integration -v
```
