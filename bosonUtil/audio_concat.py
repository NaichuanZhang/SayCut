"""WAV concatenation utility for multi-voice dialogue audio."""

import io
import struct
import wave

TARGET_SAMPLE_RATE = 24_000
TARGET_SAMPLE_WIDTH = 2  # 16-bit
TARGET_CHANNELS = 1  # mono


def _read_pcm(wav_bytes: bytes) -> tuple[bytes, int, int, int]:
    """Read a WAV file and return (raw PCM, sample_rate, sample_width, channels)."""
    with wave.open(io.BytesIO(wav_bytes)) as w:
        return (
            w.readframes(w.getnframes()),
            w.getframerate(),
            w.getsampwidth(),
            w.getnchannels(),
        )


def _silence_bytes(duration_s: float) -> bytes:
    """Generate silence as raw PCM bytes."""
    num_samples = int(TARGET_SAMPLE_RATE * duration_s)
    return b"\x00\x00" * num_samples


def concatenate_wavs(segments: list[bytes], gap_s: float = 0.3) -> tuple[bytes, float]:
    """Concatenate WAV file bytes with silence gaps between them.

    Args:
        segments: List of WAV file bytes.
        gap_s: Seconds of silence between segments.

    Returns:
        (combined_wav_bytes, total_duration_s)
    """
    if not segments:
        raise ValueError("No segments to concatenate")

    silence = _silence_bytes(gap_s)
    pcm_parts: list[bytes] = []

    for i, wav_bytes in enumerate(segments):
        pcm, sr, sw, ch = _read_pcm(wav_bytes)
        # For now, assume all segments match target format (24kHz/16-bit/mono)
        # since they come from the same TTS engine
        pcm_parts.append(pcm)
        if i < len(segments) - 1:
            pcm_parts.append(silence)

    combined_pcm = b"".join(pcm_parts)
    total_samples = len(combined_pcm) // TARGET_SAMPLE_WIDTH
    total_duration = total_samples / TARGET_SAMPLE_RATE

    # Write combined WAV
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(TARGET_CHANNELS)
        w.setsampwidth(TARGET_SAMPLE_WIDTH)
        w.setframerate(TARGET_SAMPLE_RATE)
        w.writeframes(combined_pcm)

    return buf.getvalue(), total_duration
