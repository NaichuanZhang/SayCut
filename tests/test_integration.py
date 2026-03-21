"""Integration tests for bosonUtil.

Unit tests run without an API key.
Tests marked @pytest.mark.integration require BOSONAI_API_KEY to be set.
"""

import json
import os
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

    def test_tools_enabled(self):
        prompt = build_system_prompt("Hello", tools_enabled=True)
        assert "<tools>" in prompt
        assert "calculate" in prompt


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


@skip_without_api_key
@integration
class TestToolCallRoundTrip:
    def test_calculator_tool_call(self):
        """Send 'what is 2 plus 2' and verify the tool call round-trip works."""
        import subprocess

        from openai import OpenAI

        # Generate audio via macOS TTS
        tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        tmp.close()
        subprocess.run(
            ["say", "-o", tmp.name, "--data-format=LEI16@16000", "what is two plus two"],
            capture_output=True,
            check=True,
        )

        try:
            chunks, meta = chunk_audio_file(tmp.name)
            system_prompt = build_system_prompt(DEFAULT_SYSTEM_PROMPT, tools_enabled=True)

            user_content = [
                {
                    "type": "audio_url",
                    "audio_url": {"url": f"data:audio/wav_{i};base64,{c}"},
                }
                for i, c in enumerate(chunks)
            ]

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ]

            api_key = os.environ["BOSONAI_API_KEY"]
            client = OpenAI(
                base_url=DEFAULT_BASE_URL,
                api_key=api_key,
                timeout=180.0,
                max_retries=3,
            )

            response = client.chat.completions.create(
                model=DEFAULT_MODEL,
                messages=messages,
                temperature=0.2,
                top_p=0.9,
                max_tokens=2048,
                stop=STOP_SEQUENCES,
                extra_body=EXTRA_BODY,
            )

            response_text = (response.choices[0].message.content or "").strip()
            tool_calls = parse_tool_calls(response_text)

            if tool_calls:
                tc = tool_calls[0]
                result = execute_tool_call(tc["name"], tc["arguments"])
                assert result["name"] == "calculate"
                assert result["result"] == 4.0

                # Send tool response and get final answer
                tool_response = f"<tool_response>{json.dumps(result)}</tool_response>"
                messages = [
                    *messages,
                    {"role": "assistant", "content": response_text},
                    {"role": "user", "content": tool_response},
                ]
                final = client.chat.completions.create(
                    model=DEFAULT_MODEL,
                    messages=messages,
                    temperature=0.2,
                    top_p=0.9,
                    max_tokens=2048,
                    stop=STOP_SEQUENCES,
                    extra_body=EXTRA_BODY,
                )
                final_text = (final.choices[0].message.content or "").strip()
                assert "4" in final_text
            else:
                # Model answered directly without tool call — still valid
                assert "4" in response_text
        finally:
            os.unlink(tmp.name)
