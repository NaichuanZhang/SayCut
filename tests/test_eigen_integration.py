"""Integration tests for EigenAI API clients (require EIGENAI_API_KEY)."""

import asyncio
import os
import tempfile

import numpy as np
import pytest

skip_without_eigenai_key = pytest.mark.skipif(
    not os.environ.get("EIGENAI_API_KEY"),
    reason="EIGENAI_API_KEY not set",
)


def _make_test_png(width: int = 64, height: int = 64) -> str:
    """Create a minimal solid-color PNG and return its temp file path."""
    import struct
    import zlib

    # Minimal PNG: IHDR + IDAT + IEND
    def _chunk(chunk_type: bytes, data: bytes) -> bytes:
        c = chunk_type + data
        return struct.pack(">I", len(data)) + c + struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)

    ihdr_data = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)  # 8-bit RGB
    raw_rows = b"".join(b"\x00" + b"\xff\x00\x00" * width for _ in range(height))  # red
    idat_data = zlib.compress(raw_rows)

    png = b"\x89PNG\r\n\x1a\n"
    png += _chunk(b"IHDR", ihdr_data)
    png += _chunk(b"IDAT", idat_data)
    png += _chunk(b"IEND", b"")

    tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    tmp.write(png)
    tmp.close()
    return tmp.name


@pytest.mark.eigenai_integration
@skip_without_eigenai_key
class TestScriptLLM:
    def test_generate_script(self):
        from bosonUtil.eigen_script import generate_script

        messages = [
            {"role": "system", "content": "You are a story writer."},
            {"role": "user", "content": "Write a one-sentence story about a cat."},
        ]
        result = asyncio.get_event_loop().run_until_complete(generate_script(messages))

        assert isinstance(result, str)
        assert len(result) > 0


@pytest.mark.eigenai_integration
@skip_without_eigenai_key
class TestImageGeneration:
    def test_generate_image(self):
        from bosonUtil.eigen_image_gen import generate_image

        result = asyncio.get_event_loop().run_until_complete(
            generate_image("A simple red circle on a white background")
        )

        assert isinstance(result, bytes)
        assert len(result) > 0
        assert result[:4] == b"\x89PNG", "Expected PNG format"


@pytest.mark.eigenai_integration
@skip_without_eigenai_key
class TestImageEditing:
    def test_edit_image(self):
        from bosonUtil.eigen_image_edit import ImageEditResult, edit_image

        test_image = _make_test_png()
        try:
            result = asyncio.get_event_loop().run_until_complete(
                edit_image("make it cartoon style", [test_image])
            )

            assert isinstance(result, ImageEditResult)
            assert len(result.image_bytes) > 0
            assert len(result.image_base64) > 0
            assert isinstance(result.processing_time_seconds, (int, float))
        finally:
            os.unlink(test_image)


@pytest.mark.eigenai_integration
@skip_without_eigenai_key
class TestImageToVideo:
    def test_submit_job(self):
        """Test that job submission works and returns a task_id."""
        from bosonUtil.eigen_i2v import submit_i2v_job

        test_image = _make_test_png()
        try:
            task_id = asyncio.get_event_loop().run_until_complete(
                submit_i2v_job("A circle moving slowly", test_image)
            )

            assert isinstance(task_id, str)
            assert len(task_id) > 0
        finally:
            os.unlink(test_image)

    @pytest.mark.slow
    def test_generate_video_full(self):
        """Full end-to-end video generation (slow, may take minutes)."""
        from bosonUtil.eigen_i2v import VideoResult, generate_video

        test_image = _make_test_png()
        try:
            result = asyncio.get_event_loop().run_until_complete(
                generate_video("A circle moving slowly", test_image)
            )

            assert isinstance(result, VideoResult)
            assert len(result.video_bytes) > 0
            assert len(result.task_id) > 0
        finally:
            os.unlink(test_image)


@pytest.mark.eigenai_integration
@skip_without_eigenai_key
class TestTTS:
    def test_synthesize_speech(self):
        from bosonUtil.eigen_tts import TTSResult, synthesize_speech

        result = asyncio.get_event_loop().run_until_complete(
            synthesize_speech("Hello, this is a test.")
        )

        assert isinstance(result, TTSResult)
        assert len(result.wav_bytes) > 0
        assert result.wav_bytes[:4] == b"RIFF", "Expected WAV format"
        assert result.sample_rate == 24_000
        assert result.duration_s > 0

    def test_synthesize_to_wav(self):
        from bosonUtil.eigen_tts import synthesize_to_wav

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            result_path = asyncio.get_event_loop().run_until_complete(
                synthesize_to_wav("Hello, this is a test.", tmp_path)
            )

            assert result_path == tmp_path
            assert os.path.getsize(tmp_path) > 44  # WAV header is 44 bytes
        finally:
            os.unlink(tmp_path)
