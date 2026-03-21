"""Interactive CLI voice assistant using HiggsAudioM3.

Multi-turn conversation loop that accepts three input modes:
  - Microphone recording (press Enter to start, Enter again to stop)
  - WAV file path (type an existing file path)
  - Text input (converted to speech via macOS `say` command)

Usage:
    python assistant.py
    python assistant.py --system-prompt "You are an ASR system."
    python assistant.py --model higgs-audio-understanding-v3-Hackathon
    python assistant.py --no-tools
"""

from dotenv import load_dotenv
load_dotenv()

import argparse
import json
import os
import subprocess
import tempfile
import threading

import numpy as np
import soundfile as sf

from openai import OpenAI

from bosonUtil.audio import chunk_audio_file, TARGET_SAMPLE_RATE
from bosonUtil.api import (
    DEFAULT_BASE_URL,
    DEFAULT_MAX_TOKENS,
    DEFAULT_MODEL,
    DEFAULT_SYSTEM_PROMPT,
    DEFAULT_TEMPERATURE,
    DEFAULT_TOP_P,
    EXTRA_BODY,
    STOP_SEQUENCES,
)
from bosonUtil.tools import (
    MAX_TOOL_CALLS_PER_TURN,
    build_system_prompt,
    execute_tool_call,
    parse_tool_calls,
)

MAX_RECORDING_SECONDS = 30


# ──────────────────────────────────────────────────────────────────────────────
# Audio input helpers
# ──────────────────────────────────────────────────────────────────────────────

def record_audio_from_mic() -> str:
    """Record from microphone, save to temp WAV, return file path."""
    import sounddevice as sd

    sample_rate = TARGET_SAMPLE_RATE
    frames: list[np.ndarray] = []
    stop_event = threading.Event()

    def callback(indata, frame_count, time_info, status):
        if not stop_event.is_set():
            frames.append(indata.copy())

    print("  Recording... Press ENTER to stop (max 30s)")
    stream = sd.InputStream(
        samplerate=sample_rate,
        channels=1,
        dtype="float32",
        callback=callback,
    )
    stream.start()

    input_event = threading.Event()

    def wait_for_enter():
        input()
        input_event.set()

    t = threading.Thread(target=wait_for_enter, daemon=True)
    t.start()
    t.join(timeout=MAX_RECORDING_SECONDS)

    stop_event.set()
    stream.stop()
    stream.close()

    if not frames:
        raise ValueError("No audio recorded")

    waveform = np.concatenate(frames, axis=0).flatten()
    duration = len(waveform) / sample_rate

    if duration < 0.1:
        raise ValueError("Recording too short (< 0.1s)")

    print(f"  Recorded {duration:.1f}s of audio")

    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    sf.write(tmp.name, waveform, sample_rate)
    return tmp.name


def text_to_wav(text: str) -> str:
    """Convert text to WAV using macOS `say` command. Returns temp file path."""
    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    tmp.close()

    result = subprocess.run(
        ["say", "-o", tmp.name, "--data-format=LEI16@16000", text],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        os.unlink(tmp.name)
        raise RuntimeError(f"TTS failed: {result.stderr}")

    return tmp.name


def get_audio_from_input(user_input: str) -> tuple[str, bool]:
    """Dispatch input to mic/file/TTS. Returns (wav_path, is_temp_file)."""
    stripped = user_input.strip()

    if stripped.lower() in ("r", ""):
        return record_audio_from_mic(), True

    if os.path.isfile(stripped):
        return stripped, False

    return text_to_wav(stripped), True


# ──────────────────────────────────────────────────────────────────────────────
# Message building & API
# ──────────────────────────────────────────────────────────────────────────────

def build_user_content(audio_chunks: list[str]) -> list[dict]:
    """Build audio_url content parts for a user message."""
    return [
        {
            "type": "audio_url",
            "audio_url": {"url": f"data:audio/wav_{i};base64,{chunk_b64}"},
        }
        for i, chunk_b64 in enumerate(audio_chunks)
    ]


def stream_response(
    client: OpenAI,
    messages: list[dict],
    model: str,
    temperature: float,
    top_p: float,
    max_tokens: int,
) -> str:
    """Stream API response, printing tokens live. Returns full response text."""
    response_stream = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        top_p=top_p,
        max_tokens=max_tokens,
        stop=STOP_SEQUENCES,
        extra_body=EXTRA_BODY,
        stream=True,
    )

    full_response = ""
    for chunk in response_stream:
        delta = chunk.choices[0].delta
        if delta.content:
            print(delta.content, end="", flush=True)
            full_response += delta.content
    print()
    return full_response.strip()


# ──────────────────────────────────────────────────────────────────────────────
# Interactive loop
# ──────────────────────────────────────────────────────────────────────────────

def print_banner(tools_enabled: bool):
    print("=" * 60)
    print("  HiggsAudio Interactive Voice Assistant")
    print("=" * 60)
    print("  Input modes:")
    print("    ENTER or 'r'  - Record from microphone")
    print("    /path/to.wav  - Send an existing WAV file")
    print("    any text      - Convert text to speech, then send")
    print("  Commands:")
    print("    'q' / 'quit'  - Exit")
    print("    'clear'       - Reset conversation history")
    if tools_enabled:
        print("  Tools:")
        print("    calculator    - Math expressions (e.g. 'what is 15 * 7 + 3')")
    print("=" * 60)


def interactive_loop(
    system_prompt: str,
    base_url: str,
    model: str,
    api_key: str,
    temperature: float,
    top_p: float,
    max_tokens: int,
    tools_enabled: bool = True,
) -> None:
    client = OpenAI(
        base_url=base_url,
        api_key=api_key,
        timeout=180.0,
        max_retries=3,
    )

    full_system_prompt = build_system_prompt(system_prompt, tools_enabled)
    messages = [{"role": "system", "content": full_system_prompt}]
    print_banner(tools_enabled)

    while True:
        print("\n[You] (r)ecord | file path | text | (q)uit")
        try:
            user_input = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if user_input.lower() in ("q", "quit", "exit"):
            print("Goodbye!")
            break

        if user_input.lower() == "clear":
            messages = [{"role": "system", "content": full_system_prompt}]
            print("  Conversation cleared.")
            continue

        # Get audio
        try:
            wav_path, is_temp = get_audio_from_input(user_input)
        except Exception as e:
            print(f"  Error: {e}")
            continue

        # Chunk through VAD pipeline
        try:
            audio_chunks, meta = chunk_audio_file(wav_path)
            print(f"  Audio: {meta['duration_s']}s -> {meta['num_chunks']} chunks")
        except Exception as e:
            print(f"  Error processing audio: {e}")
            if is_temp:
                os.unlink(wav_path)
            continue
        finally:
            if is_temp and os.path.exists(wav_path):
                os.unlink(wav_path)

        # Append user turn
        user_content = build_user_content(audio_chunks)
        messages = [*messages, {"role": "user", "content": user_content}]

        # Stream response (with tool call loop)
        print("\n[Assistant]")
        try:
            response_text = stream_response(
                client,
                messages,
                model=model,
                temperature=temperature,
                top_p=top_p,
                max_tokens=max_tokens,
            )
        except Exception as e:
            print(f"\n  API Error: {e}")
            messages = messages[:-1]
            continue

        messages = [*messages, {"role": "assistant", "content": response_text}]

        # Handle tool calls if tools are enabled
        if tools_enabled:
            for _ in range(MAX_TOOL_CALLS_PER_TURN):
                tool_calls = parse_tool_calls(response_text)
                if not tool_calls:
                    break

                for tc in tool_calls:
                    tc_name = tc["name"]
                    tc_args = tc["arguments"]
                    print(f"\n  [Tool Call] {tc_name}({json.dumps(tc_args)})")

                    try:
                        result = execute_tool_call(tc_name, tc_args)
                        print(f"  [Tool Result] {result.get('result', result.get('error'))}")
                    except Exception as e:
                        result = {"name": tc_name, "error": str(e)}
                        print(f"  [Tool Error] {e}")

                    tool_response = f"<tool_response>{json.dumps(result)}</tool_response>"
                    messages = [*messages, {"role": "user", "content": tool_response}]

                # Get follow-up response
                print("\n[Assistant]")
                try:
                    response_text = stream_response(
                        client,
                        messages,
                        model=model,
                        temperature=temperature,
                        top_p=top_p,
                        max_tokens=max_tokens,
                    )
                except Exception as e:
                    print(f"\n  API Error: {e}")
                    break

                messages = [*messages, {"role": "assistant", "content": response_text}]


# ──────────────────────────────────────────────────────────────────────────────
# CLI entry point
# ──────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Interactive voice assistant using HiggsAudioM3",
    )
    parser.add_argument("--system-prompt", default=DEFAULT_SYSTEM_PROMPT)
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--temperature", type=float, default=DEFAULT_TEMPERATURE)
    parser.add_argument("--top-p", type=float, default=DEFAULT_TOP_P)
    parser.add_argument("--max-tokens", type=int, default=DEFAULT_MAX_TOKENS)
    parser.add_argument(
        "--no-tools",
        action="store_true",
        help="Disable tool use (calculator)",
    )
    args = parser.parse_args()

    api_key = os.environ.get("BOSONAI_API_KEY", "EMPTY")

    interactive_loop(
        system_prompt=args.system_prompt,
        base_url=args.base_url,
        model=args.model,
        api_key=api_key,
        temperature=args.temperature,
        top_p=args.top_p,
        max_tokens=args.max_tokens,
        tools_enabled=not args.no_tools,
    )


if __name__ == "__main__":
    main()
