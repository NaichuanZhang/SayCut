"""Unit tests for EigenAI modules (no API key needed)."""

import os

import pytest

from bosonUtil.eigen_config import resolve_eigenai_api_key
from bosonUtil.eigen_image_edit import DEFAULT_GUIDANCE_SCALE, DEFAULT_NUM_INFERENCE_STEPS, MAX_SOURCE_IMAGES
from bosonUtil.eigen_i2v import (
    DEFAULT_INFER_STEPS,
    DEFAULT_MAX_POLL_ATTEMPTS,
    DEFAULT_POLL_INTERVAL_S,
    STATUS_COMPLETED,
    STATUS_FAILED,
)
from bosonUtil.eigen_tts import DEFAULT_VOICE, TTS_CHANNELS, TTS_SAMPLE_RATE, TTS_SAMPLE_WIDTH


class TestEigenConfig:
    def test_resolve_key_from_param(self):
        assert resolve_eigenai_api_key("test-key-123") == "test-key-123"

    def test_resolve_key_from_env(self, monkeypatch):
        monkeypatch.setenv("EIGENAI_API_KEY", "env-key-456")
        assert resolve_eigenai_api_key() == "env-key-456"

    def test_param_takes_precedence_over_env(self, monkeypatch):
        monkeypatch.setenv("EIGENAI_API_KEY", "env-key")
        assert resolve_eigenai_api_key("param-key") == "param-key"

    def test_raises_when_no_key(self, monkeypatch):
        monkeypatch.delenv("EIGENAI_API_KEY", raising=False)
        with pytest.raises(ValueError, match="EigenAI API key required"):
            resolve_eigenai_api_key()


class TestImageEditValidation:
    def test_rejects_empty_image_list(self):
        with pytest.raises(ValueError, match="At least one source image"):
            # Import the validation logic directly
            from bosonUtil.eigen_image_edit import edit_image
            import asyncio
            asyncio.get_event_loop().run_until_complete(
                edit_image("test prompt", [])
            )

    def test_rejects_too_many_images(self):
        from bosonUtil.eigen_image_edit import edit_image
        import asyncio
        paths = [f"fake_{i}.jpg" for i in range(MAX_SOURCE_IMAGES + 1)]
        with pytest.raises(ValueError, match=f"Maximum {MAX_SOURCE_IMAGES}"):
            asyncio.get_event_loop().run_until_complete(
                edit_image("test prompt", paths)
            )

    def test_max_source_images_is_nine(self):
        assert MAX_SOURCE_IMAGES == 9


class TestI2VConstants:
    def test_default_infer_steps(self):
        assert DEFAULT_INFER_STEPS == 5

    def test_default_poll_interval(self):
        assert DEFAULT_POLL_INTERVAL_S == 2.0

    def test_default_max_poll_attempts(self):
        assert DEFAULT_MAX_POLL_ATTEMPTS == 150

    def test_status_values(self):
        assert STATUS_COMPLETED == "completed"
        assert STATUS_FAILED == "failed"


class TestTTSDefaults:
    def test_default_voice(self):
        assert DEFAULT_VOICE == "Linda"

    def test_sample_rate(self):
        assert TTS_SAMPLE_RATE == 24_000

    def test_sample_format(self):
        assert TTS_SAMPLE_WIDTH == 2  # 16-bit
        assert TTS_CHANNELS == 1  # mono
