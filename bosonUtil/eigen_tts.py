"""EigenAI text-to-speech client using higgs2p5 model."""

import io
import wave
from dataclasses import dataclass

import httpx

from .eigen_config import EIGENAI_GENERATE_URL, build_auth_headers, resolve_eigenai_api_key

DEFAULT_MODEL = "higgs2p5"
DEFAULT_VOICE = "Linda"
MORGAN_FREEMAN_VOICE_ID = "5fdbb23ac32e44b8abfe2cea405d0495"
TTS_SAMPLE_RATE = 24_000
TTS_SAMPLE_WIDTH = 2  # 16-bit
TTS_CHANNELS = 1  # mono
TIMEOUT_S = 120.0


@dataclass(frozen=True)
class TTSResult:
    wav_bytes: bytes  # complete WAV file
    sample_rate: int
    duration_s: float


async def synthesize_speech(
    text: str,
    *,
    voice: str = DEFAULT_VOICE,
    voice_id: str | None = None,
    model: str = DEFAULT_MODEL,
    api_key: str | None = None,
) -> TTSResult:
    key = resolve_eigenai_api_key(api_key)
    headers = build_auth_headers(key)

    headers["Content-Type"] = "application/json"
    payload: dict[str, str] = {"model": model, "text": text}
    if voice_id:
        payload["voice_id"] = voice_id
    else:
        payload["voice"] = voice

    async with httpx.AsyncClient(timeout=TIMEOUT_S) as client:
        response = await client.post(EIGENAI_GENERATE_URL, headers=headers, json=payload)
        response.raise_for_status()

    wav_bytes = response.content
    if wav_bytes[:4] != b"RIFF":
        raise ValueError(f"Expected WAV response, got: {wav_bytes[:20]!r}")

    with wave.open(io.BytesIO(wav_bytes)) as wav:
        sample_rate = wav.getframerate()
        duration_s = wav.getnframes() / sample_rate if sample_rate > 0 else 0.0

    return TTSResult(wav_bytes=wav_bytes, sample_rate=sample_rate, duration_s=duration_s)


async def synthesize_to_wav(
    text: str,
    output_path: str,
    **kwargs,
) -> str:
    result = await synthesize_speech(text, **kwargs)

    with open(output_path, "wb") as f:
        f.write(result.wav_bytes)

    return output_path
