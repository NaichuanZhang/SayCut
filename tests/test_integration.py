"""Integration tests for bosonUtil.

Unit tests run without an API key.
Tests marked @pytest.mark.integration require BOSONAI_API_KEY to be set.
"""

import json
import os
import re
import subprocess
import tempfile

import numpy as np
import pytest
import soundfile as sf

from bosonUtil.tools import (
    build_system_prompt,
    execute_tool_call,
    parse_tool_calls,
    safe_eval_math,
    CALCULATOR_TOOLS,
)
from bosonUtil.api import (
    DEFAULT_BASE_URL,
    DEFAULT_MODEL,
    DEFAULT_SYSTEM_PROMPT,
    STOP_SEQUENCES,
    EXTRA_BODY,
    build_messages,
)
from bosonUtil.audio import chunk_audio_file, TARGET_SAMPLE_RATE
from backend.storybook_tools import STORYBOOK_TOOLS
from backend.voice_agent import STORYBOOK_SYSTEM_PROMPT

integration = pytest.mark.integration
skip_without_api_key = pytest.mark.skipif(
    not os.environ.get("BOSONAI_API_KEY"),
    reason="BOSONAI_API_KEY not set",
)


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

def _make_sine_wav(duration_s: float = 1.0, freq_hz: float = 440.0) -> str:
    """Generate a sine wave WAV file and return its path."""
    t = np.linspace(0, duration_s, int(TARGET_SAMPLE_RATE * duration_s), dtype=np.float32)
    waveform = 0.5 * np.sin(2 * np.pi * freq_hz * t)
    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    sf.write(tmp.name, waveform, TARGET_SAMPLE_RATE)
    return tmp.name


# ──────────────────────────────────────────────────────────────────────────────
# Unit tests — no API key needed
# ──────────────────────────────────────────────────────────────────────────────

class TestSafeEvalMath:
    def test_basic_addition(self):
        assert safe_eval_math("2 + 3") == 5.0

    def test_multiplication(self):
        assert safe_eval_math("15 * 7 + 3") == 108.0

    def test_exponentiation(self):
        assert safe_eval_math("144 ** 0.5") == 12.0

    def test_parentheses(self):
        assert safe_eval_math("(2 + 3) * 4") == 20.0

    def test_rejects_letters(self):
        with pytest.raises(ValueError, match="Unsafe expression"):
            safe_eval_math("import os")

    def test_rejects_dunder(self):
        with pytest.raises(ValueError, match="Unsafe expression"):
            safe_eval_math("__import__('os')")


class TestExecuteToolCall:
    def test_calculate(self):
        result = execute_tool_call("calculate", {"expression": "2 + 2"})
        assert result == {"name": "calculate", "result": 4.0}

    def test_unknown_tool(self):
        result = execute_tool_call("unknown", {})
        assert "error" in result


class TestParseToolCalls:
    def test_array_format(self):
        text = '<tool_call>[{"type":"function","function":{"name":"calculate","arguments":"{\\"expression\\": \\"2+2\\"}"}}]</tool_call>'
        calls = parse_tool_calls(text)
        assert len(calls) == 1
        assert calls[0]["name"] == "calculate"
        assert calls[0]["arguments"] == {"expression": "2+2"}

    def test_flat_format(self):
        text = '<tool_call>{"name":"calculate","arguments":{"expression":"3*3"}}</tool_call>'
        calls = parse_tool_calls(text)
        assert len(calls) == 1
        assert calls[0]["name"] == "calculate"
        assert calls[0]["arguments"] == {"expression": "3*3"}

    def test_no_tool_call(self):
        assert parse_tool_calls("Hello, how are you?") == []

    def test_multiple_tool_calls(self):
        text = (
            '<tool_call>{"name":"calculate","arguments":{"expression":"1+1"}}</tool_call>'
            ' some text '
            '<tool_call>{"name":"calculate","arguments":{"expression":"2+2"}}</tool_call>'
        )
        calls = parse_tool_calls(text)
        assert len(calls) == 2

    def test_malformed_json_skipped(self):
        text = "<tool_call>not json</tool_call>"
        assert parse_tool_calls(text) == []


class TestBuildSystemPrompt:
    def test_tools_disabled(self):
        prompt = build_system_prompt("Hello", tools_enabled=False)
        assert prompt == "Hello"
        assert "<tools>" not in prompt

    def test_tools_enabled_default(self):
        prompt = build_system_prompt("Hello", tools_enabled=True)
        assert "<tools>" in prompt
        assert "calculate" in prompt

    def test_tools_enabled_custom(self):
        custom_tools = [
            {"type": "function", "function": {"name": "my_tool", "parameters": {}}}
        ]
        prompt = build_system_prompt("Hello", tools_enabled=True, tools=custom_tools)
        assert "<tools>" in prompt
        assert "my_tool" in prompt
        assert "calculate" not in prompt


class TestAudioChunking:
    def test_chunk_sine_wave(self):
        wav_path = _make_sine_wav(duration_s=1.0)
        try:
            chunks, meta = chunk_audio_file(wav_path)
            assert len(chunks) >= 1
            assert meta["duration_s"] == 1.0
            assert meta["sample_rate"] == TARGET_SAMPLE_RATE
        finally:
            os.unlink(wav_path)

    def test_chunk_long_audio(self):
        wav_path = _make_sine_wav(duration_s=6.0)
        try:
            chunks, meta = chunk_audio_file(wav_path)
            assert len(chunks) >= 2  # 6s must be split into at least 2 chunks
            assert meta["duration_s"] == 6.0
        finally:
            os.unlink(wav_path)


class TestBuildMessages:
    def test_basic_messages(self):
        msgs = build_messages(["base64data"], system_prompt="Test")
        assert msgs[0]["role"] == "system"
        assert msgs[0]["content"] == "Test"
        assert msgs[1]["role"] == "user"
        assert len(msgs[1]["content"]) == 1
        assert "audio/wav_0" in msgs[1]["content"][0]["audio_url"]["url"]

    def test_with_user_text(self):
        msgs = build_messages(["data"], user_text="Transcribe this")
        user_parts = msgs[1]["content"]
        assert user_parts[0]["type"] == "text"
        assert user_parts[0]["text"] == "Transcribe this"
        assert user_parts[1]["type"] == "audio_url"


# ──────────────────────────────────────────────────────────────────────────────
# Integration tests — require BOSONAI_API_KEY
# ──────────────────────────────────────────────────────────────────────────────

@skip_without_api_key
@integration
class TestAPIConnectivity:
    def test_basic_prediction(self):
        """Send a sine wave and verify we get a non-empty response."""
        from bosonUtil.api import predict

        wav_path = _make_sine_wav(duration_s=1.0)
        try:
            response = predict(
                audio_path=wav_path,
                system_prompt="Describe what you hear briefly.",
            )
            assert isinstance(response, str)
            assert len(response) > 0
        finally:
            os.unlink(wav_path)


def _say_to_wav(text: str) -> str:
    """Use macOS `say` to generate a 16kHz WAV file from text."""
    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    tmp.close()
    subprocess.run(
        ["say", "-o", tmp.name, "--data-format=LEI16@16000", text],
        capture_output=True,
        check=True,
    )
    return tmp.name


def _make_boson_client():
    """Create an OpenAI client pointing to BosonAI."""
    from openai import OpenAI

    return OpenAI(
        base_url=DEFAULT_BASE_URL,
        api_key=os.environ["BOSONAI_API_KEY"],
        timeout=180.0,
        max_retries=3,
    )


def _audio_to_content_parts(wav_path: str) -> list[dict]:
    """Chunk a WAV file and return audio_url content parts."""
    chunks, _ = chunk_audio_file(wav_path)
    return [
        {
            "type": "audio_url",
            "audio_url": {"url": f"data:audio/wav_{i};base64,{c}"},
        }
        for i, c in enumerate(chunks)
    ]


def _chat(client, messages: list[dict], max_tokens: int = 2048) -> str:
    """Send a chat completion and return the response text."""
    response = client.chat.completions.create(
        model=DEFAULT_MODEL,
        messages=messages,
        temperature=0.2,
        top_p=0.9,
        max_tokens=max_tokens,
        stop=STOP_SEQUENCES,
        extra_body=EXTRA_BODY,
    )
    return (response.choices[0].message.content or "").strip()


_PARTIAL_TOOL_CALL_RE = re.compile(r"<tool_call>(.*?)$", re.DOTALL)


def _parse_tool_calls_lenient(text: str) -> list[dict]:
    """Like parse_tool_calls but also handles truncated tool calls (missing closing tag)."""
    calls = parse_tool_calls(text)
    if calls:
        return calls
    # Try to extract a partial tool call (truncated before </tool_call>)
    match = _PARTIAL_TOOL_CALL_RE.search(text)
    if not match:
        return []
    raw = match.group(1).strip()
    # Try to parse as-is, then try adding closing braces
    for suffix in ["", "}", '"}', '"}}', '"}]']:
        try:
            parsed = json.loads(raw + suffix)
            items = parsed if isinstance(parsed, list) else [parsed]
            from bosonUtil.tools import _normalize_tool_call
            return [_normalize_tool_call(item) for item in items]
        except (json.JSONDecodeError, KeyError):
            continue
    return []


def _chat_until_tool_call(
    client, messages: list[dict], expected_tool: str, max_follow_ups: int = 2
) -> tuple[str, list[dict]]:
    """Chat and retry if model announces intent without calling.

    Returns (response_text_with_tool_call, tool_calls).
    """
    response_text = _chat(client, messages, max_tokens=4096)
    tool_calls = _parse_tool_calls_lenient(response_text)

    for _ in range(max_follow_ups):
        if tool_calls:
            break
        # Model announced intent but didn't call — nudge it
        messages = [
            *messages,
            {"role": "assistant", "content": response_text},
            {
                "role": "user",
                "content": (
                    f"Please call the {expected_tool} tool now. "
                    "Use <tool_call> tags with JSON arguments."
                ),
            },
        ]
        response_text = _chat(client, messages, max_tokens=4096)
        tool_calls = _parse_tool_calls_lenient(response_text)

    return response_text, tool_calls


@skip_without_api_key
@integration
class TestToolCallRoundTrip:
    def test_calculator_tool_call(self):
        """Send 'what is 2 plus 2' and verify the tool call round-trip works."""
        tmp_path = _say_to_wav("what is two plus two")

        try:
            system_prompt = build_system_prompt(DEFAULT_SYSTEM_PROMPT, tools_enabled=True)
            user_content = _audio_to_content_parts(tmp_path)
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ]

            client = _make_boson_client()
            response_text = _chat(client, messages)
            tool_calls = parse_tool_calls(response_text)

            if tool_calls:
                tc = tool_calls[0]
                result = execute_tool_call(tc["name"], tc["arguments"])
                assert result["name"] == "calculate"
                assert result["result"] == 4.0

                tool_response = f"<tool_response>{json.dumps(result)}</tool_response>"
                messages = [
                    *messages,
                    {"role": "assistant", "content": response_text},
                    {"role": "user", "content": tool_response},
                ]
                final_text = _chat(client, messages)
                assert "4" in final_text
            else:
                assert "4" in response_text
        finally:
            os.unlink(tmp_path)


# ──────────────────────────────────────────────────────────────────────────────
# Storybook tool integration tests — voice-driven via macOS `say`
# ──────────────────────────────────────────────────────────────────────────────

# Append "Use Thinking." to enable reliable tool calling in v3.5
_STORYBOOK_SYS = build_system_prompt(
    STORYBOOK_SYSTEM_PROMPT + "\nUse Thinking.",
    tools_enabled=True,
    tools=STORYBOOK_TOOLS,
)

# Mock script result used to seed conversation history for subsequent tool tests
_MOCK_SCRIPT_RESULT = {
    "name": "generate_script",
    "title": "The Brave Kitten",
    "scenes": [
        {
            "id": "scene_001",
            "index": 0,
            "title": "Scene 1: Into the Forest",
            "narrationText": "A brave little kitten ventured into the dark forest.",
            "visualDescription": "A small orange kitten standing at the edge of a dark forest.",
            "imageUrl": "/assets/test/scene_001.png",
            "videoUrl": None,
            "audioUrl": None,
            "status": "ready",
        },
        {
            "id": "scene_002",
            "index": 1,
            "title": "Scene 2: The Discovery",
            "narrationText": "The kitten discovered a hidden waterfall.",
            "visualDescription": "An orange kitten looking up at a sparkling waterfall.",
            "imageUrl": "/assets/test/scene_002.png",
            "videoUrl": None,
            "audioUrl": None,
            "status": "ready",
        },
    ],
}


def _build_seeded_history() -> list[dict]:
    """Build a conversation history seeded with a generate_script round-trip."""
    script_tool_call = json.dumps(
        {"name": "generate_script", "arguments": {"story_prompt": "a brave kitten", "num_scenes": 2}}
    )
    return [
        {"role": "system", "content": _STORYBOOK_SYS},
        {"role": "user", "content": "Create a story about a brave kitten exploring the forest"},
        {
            "role": "assistant",
            "content": (
                '[Heard: "Create a story about a brave kitten exploring the forest"]\n'
                f"I'll create that story for you!\n<tool_call>{script_tool_call}</tool_call>"
            ),
        },
        {
            "role": "user",
            "content": f"<tool_response>{json.dumps(_MOCK_SCRIPT_RESULT)}</tool_response>",
        },
        {
            "role": "assistant",
            "content": (
                "I've created a 2-scene storybook called 'The Brave Kitten'! "
                "Scene 1 is 'Into the Forest' and Scene 2 is 'The Discovery'. "
                "The scene IDs are scene_001 and scene_002. "
                "Would you like me to generate images for these scenes?"
            ),
        },
    ]


@skip_without_api_key
@integration
class TestStorybookScriptToolCall:
    def test_voice_triggers_generate_script(self):
        """User says 'create a story' and model calls generate_script."""
        tmp_path = _say_to_wav(
            "Create a story about a brave kitten exploring the forest"
        )
        try:
            user_content = _audio_to_content_parts(tmp_path)
            messages = [
                {"role": "system", "content": _STORYBOOK_SYS},
                {"role": "user", "content": user_content},
            ]

            client = _make_boson_client()
            response_text, tool_calls = _chat_until_tool_call(
                client, messages, "generate_script"
            )

            assert len(tool_calls) >= 1, f"Expected tool call, got: {response_text[:200]}"
            tc = tool_calls[0]
            assert tc["name"] == "generate_script"
            assert "story_prompt" in tc["arguments"]

            # Round-trip: send mock result, verify final response
            tool_response = f"<tool_response>{json.dumps(_MOCK_SCRIPT_RESULT)}</tool_response>"
            follow_up_messages = [
                *messages,
                {"role": "assistant", "content": response_text},
                {"role": "user", "content": tool_response},
            ]
            final_text = _chat(client, follow_up_messages)
            assert len(final_text) > 0
        finally:
            os.unlink(tmp_path)


@skip_without_api_key
@integration
class TestStorybookImageToolCall:
    def test_voice_triggers_generate_scene_image(self):
        """User says 'generate images' and model calls generate_scene_image."""
        tmp_path = _say_to_wav("Generate images for the scenes")
        try:
            messages = _build_seeded_history()
            messages.append({"role": "user", "content": _audio_to_content_parts(tmp_path)})

            client = _make_boson_client()
            response_text, tool_calls = _chat_until_tool_call(
                client, messages, "generate_scene_image"
            )

            assert len(tool_calls) >= 1, f"Expected tool call, got: {response_text[:200]}"
            image_calls = [tc for tc in tool_calls if tc["name"] == "generate_scene_image"]
            assert len(image_calls) >= 1
            assert "scene_id" in image_calls[0]["arguments"]
            assert "visual_description" in image_calls[0]["arguments"]
        finally:
            os.unlink(tmp_path)


@skip_without_api_key
@integration
class TestStorybookAudioToolCall:
    def test_voice_triggers_generate_scene_audio(self):
        """User says 'generate narration' and model calls generate_scene_audio."""
        tmp_path = _say_to_wav("Now generate the narration audio for the scenes")
        try:
            messages = _build_seeded_history()
            messages.append({"role": "user", "content": _audio_to_content_parts(tmp_path)})

            client = _make_boson_client()
            response_text, tool_calls = _chat_until_tool_call(
                client, messages, "generate_scene_audio"
            )

            assert len(tool_calls) >= 1, f"Expected tool call, got: {response_text[:200]}"
            audio_calls = [tc for tc in tool_calls if tc["name"] == "generate_scene_audio"]
            assert len(audio_calls) >= 1
            assert "scene_id" in audio_calls[0]["arguments"]
            assert "narration_text" in audio_calls[0]["arguments"]
        finally:
            os.unlink(tmp_path)


@skip_without_api_key
@integration
class TestStorybookVideoToolCall:
    def test_voice_triggers_generate_scene_video(self):
        """User says 'create videos' and model calls generate_scene_video."""
        tmp_path = _say_to_wav("Create video clips for the scenes")
        try:
            messages = _build_seeded_history()
            messages.append({"role": "user", "content": _audio_to_content_parts(tmp_path)})

            client = _make_boson_client()
            response_text, tool_calls = _chat_until_tool_call(
                client, messages, "generate_scene_video"
            )

            assert len(tool_calls) >= 1, f"Expected tool call, got: {response_text[:200]}"
            video_calls = [tc for tc in tool_calls if tc["name"] == "generate_scene_video"]
            assert len(video_calls) >= 1
            assert "scene_id" in video_calls[0]["arguments"]
        finally:
            os.unlink(tmp_path)


@skip_without_api_key
@integration
class TestStorybookEditToolCall:
    def test_voice_triggers_edit_scene_image(self):
        """User says 'make the kitten bigger' and model calls edit_scene_image."""
        tmp_path = _say_to_wav("Make the kitten bigger in scene one")
        try:
            messages = _build_seeded_history()
            messages.append({"role": "user", "content": _audio_to_content_parts(tmp_path)})

            client = _make_boson_client()
            response_text, tool_calls = _chat_until_tool_call(
                client, messages, "edit_scene_image"
            )

            assert len(tool_calls) >= 1, f"Expected tool call, got: {response_text[:200]}"
            edit_calls = [tc for tc in tool_calls if tc["name"] == "edit_scene_image"]
            assert len(edit_calls) >= 1
            assert "scene_id" in edit_calls[0]["arguments"]
            assert "edit_prompt" in edit_calls[0]["arguments"]
        finally:
            os.unlink(tmp_path)


@skip_without_api_key
@integration
class TestStorybookInsertScene:
    def test_voice_triggers_insert_between_scenes(self):
        """User says 'add a scene between 1 and 2' and model passes insert_after_scene_id."""
        tmp_path = _say_to_wav(
            "Add a new scene between scene one and scene two about the kitten crossing a river"
        )
        try:
            messages = _build_seeded_history()
            user_content = _audio_to_content_parts(tmp_path)
            messages.append({"role": "user", "content": user_content})

            client = _make_boson_client()
            response_text, tool_calls = _chat_until_tool_call(
                client, messages, "generate_script"
            )

            assert len(tool_calls) >= 1, f"Expected generate_script call, got: {response_text[:200]}"
            tc = tool_calls[0]
            assert tc["name"] == "generate_script"
            assert "insert_after_scene_id" in tc["arguments"], (
                f"Missing insert_after_scene_id in args: {tc['arguments']}"
            )
            assert tc["arguments"]["insert_after_scene_id"] == "scene_001"
        finally:
            os.unlink(tmp_path)


@skip_without_api_key
@integration
class TestStorybookFullFlow:
    def test_multi_turn_script_then_images(self):
        """Multi-turn: script generation, then image generation."""
        # Turn 1: Generate script
        tmp_path = _say_to_wav("Make a two scene story about a space cat")
        try:
            user_content = _audio_to_content_parts(tmp_path)
            messages = [
                {"role": "system", "content": _STORYBOOK_SYS},
                {"role": "user", "content": user_content},
            ]

            client = _make_boson_client()
            response_text, tool_calls = _chat_until_tool_call(
                client, messages, "generate_script"
            )

            assert len(tool_calls) >= 1, f"Turn 1: expected tool call, got: {response_text[:200]}"
            assert tool_calls[0]["name"] == "generate_script"
        finally:
            os.unlink(tmp_path)

        # Feed back mock script result
        tool_response = f"<tool_response>{json.dumps(_MOCK_SCRIPT_RESULT)}</tool_response>"
        messages = [
            *messages,
            {"role": "assistant", "content": response_text},
            {"role": "user", "content": tool_response},
        ]
        mid_text = _chat(client, messages, max_tokens=4096)
        messages.append({"role": "assistant", "content": mid_text})

        # Check if model already called generate_scene_image in the same response
        image_calls_in_mid = [
            tc for tc in parse_tool_calls(mid_text) if tc["name"] == "generate_scene_image"
        ]

        if not image_calls_in_mid:
            # Turn 2: Ask for images explicitly
            tmp_path2 = _say_to_wav("Now generate images for all the scenes")
            try:
                messages.append(
                    {"role": "user", "content": _audio_to_content_parts(tmp_path2)}
                )
                response_text2, tool_calls2 = _chat_until_tool_call(
                    client, messages, "generate_scene_image"
                )

                image_calls = [
                    tc for tc in tool_calls2 if tc["name"] == "generate_scene_image"
                ]
                assert len(image_calls) >= 1, (
                    f"Turn 2: expected image tool calls, got: {response_text2[:200]}"
                )
            finally:
                os.unlink(tmp_path2)
        else:
            assert len(image_calls_in_mid) >= 1
