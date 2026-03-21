"""Audio utilities for HiggsAudioM3 — VAD chunking pipeline.

Audio must be split into chunks of at most 4 seconds before sending to the API.
This is a requirement of the HiggsAudioM3 API.

Pipeline overview:
    1. Load audio file -> waveform + sample rate
    2. Resample to 16kHz (required by the API)
    3. Run Silero VAD to detect speech segments
    4. Fill gaps between VAD segments (so the full audio is covered)
    5. Enforce max 4s per chunk (split longer segments)
    6. Encode each chunk as base64 WAV

Usage:
    from bosonUtil.audio import chunk_audio_file
    chunks = chunk_audio_file("my_audio.wav")
    # chunks is a list of base64-encoded WAV strings, each <= 4 seconds
"""

import base64
import io
import wave
from typing import Any

import numpy as np
import soundfile as sf

# ──────────────────────────────────────────────────────────────────────────────
# Constants — required by the HiggsAudioM3 API
# ──────────────────────────────────────────────────────────────────────────────

TARGET_SAMPLE_RATE = 16_000          # The API expects 16kHz audio
MAX_CHUNK_SECONDS = 4.0              # Maximum audio length per chunk accepted by the API
MAX_CHUNK_SAMPLES = int(MAX_CHUNK_SECONDS * TARGET_SAMPLE_RATE)  # 64,000 samples
MIN_CHUNK_SAMPLES = 1_600            # ~0.1s — server rejects audio shorter than this

# Silero VAD parameters
VAD_THRESHOLD = 0.55                 # Speech probability threshold
VAD_MIN_SPEECH_MS = 125              # Minimum speech duration to keep
VAD_MIN_SILENCE_MS = 200             # Minimum silence duration to split on
VAD_SPEECH_PAD_MS = 300              # Padding added around speech segments


# ──────────────────────────────────────────────────────────────────────────────
# Step 1: Load audio from file
# ──────────────────────────────────────────────────────────────────────────────

def load_audio(file_path: str) -> tuple[np.ndarray, int]:
    """Load an audio file and return (waveform, sample_rate).

    Supports any format that libsndfile handles (WAV, FLAC, OGG, etc.).
    Stereo audio is mixed down to mono by averaging channels.
    """
    data, sr = sf.read(file_path, dtype="float32")

    # Mix stereo -> mono by averaging channels
    if data.ndim > 1:
        data = data.mean(axis=1)

    return data, sr


# ──────────────────────────────────────────────────────────────────────────────
# Step 2: Resample to 16kHz
# ──────────────────────────────────────────────────────────────────────────────

def resample_audio(
    waveform: np.ndarray,
    orig_sr: int,
    target_sr: int = TARGET_SAMPLE_RATE,
) -> np.ndarray:
    """Resample audio to the target sample rate.

    The API expects 16kHz audio. If your audio is already 16kHz,
    this function returns the input unchanged.
    """
    if orig_sr == target_sr:
        return waveform

    import torch
    import torchaudio
    wv_tensor = torch.tensor(waveform, dtype=torch.float32).unsqueeze(0)
    resampled = torchaudio.transforms.Resample(orig_freq=orig_sr, new_freq=target_sr)(wv_tensor)
    return resampled.squeeze(0).numpy()


# ──────────────────────────────────────────────────────────────────────────────
# Step 3: Silero VAD — detect speech segments
# ──────────────────────────────────────────────────────────────────────────────

_vad_model: Any = None  # Cached singleton


def _get_silero_vad() -> Any:
    """Load Silero VAD model (cached after first call)."""
    global _vad_model
    if _vad_model is not None:
        return _vad_model
    from silero_vad import load_silero_vad
    _vad_model = load_silero_vad(onnx=True, opset_version=16)
    return _vad_model


def get_vad_chunks(waveform: np.ndarray, sr: int) -> list[tuple[int, int]]:
    """Run Silero VAD and return speech segment boundaries as (start, end) sample indices.

    If no speech is detected, returns a single segment covering the entire audio.
    """
    import torch
    from silero_vad import get_speech_timestamps

    model = _get_silero_vad()
    wv_tensor = torch.tensor(waveform, dtype=torch.float32)

    timestamps = get_speech_timestamps(
        audio=wv_tensor,
        model=model,
        threshold=VAD_THRESHOLD,
        sampling_rate=sr,
        min_speech_duration_ms=VAD_MIN_SPEECH_MS,
        min_silence_duration_ms=VAD_MIN_SILENCE_MS,
        speech_pad_ms=VAD_SPEECH_PAD_MS,
        visualize_probs=False,
        return_seconds=False,
    )

    # Fallback: if VAD finds no speech, treat the entire audio as one segment
    if not timestamps:
        return [(0, len(waveform))]

    return [(ts["start"], ts["end"]) for ts in timestamps]


# ──────────────────────────────────────────────────────────────────────────────
# Step 4: Fill gaps between VAD segments
# ──────────────────────────────────────────────────────────────────────────────

def fill_vad_gaps(
    vad_chunks: list[tuple[int, int]],
    total_samples: int,
) -> list[tuple[int, int]]:
    """Expand VAD segments to cover the full audio with no gaps."""
    filled: list[tuple[int, int]] = []
    prev_end = 0

    for idx, (start, end) in enumerate(vad_chunks):
        chunk_start = min(prev_end, start)
        chunk_end = total_samples if idx == len(vad_chunks) - 1 else end
        filled.append((chunk_start, chunk_end))
        prev_end = end

    return filled


# ──────────────────────────────────────────────────────────────────────────────
# Step 5: Enforce max 4-second chunk length
# ──────────────────────────────────────────────────────────────────────────────

def enforce_max_chunk_len(
    chunks: list[tuple[int, int]],
    max_samples: int = MAX_CHUNK_SAMPLES,
) -> list[tuple[int, int]]:
    """Split any chunk exceeding the maximum length into sub-chunks."""
    result: list[tuple[int, int]] = []

    for start, end in chunks:
        length = end - start
        if length == 0:
            continue

        if length <= max_samples:
            result.append((start, end))
        else:
            pos = start
            while pos < end:
                next_pos = min(end, pos + max_samples)
                result.append((pos, next_pos))
                pos = next_pos

    return result


# ──────────────────────────────────────────────────────────────────────────────
# Step 6: Encode a waveform chunk to base64 WAV
# ──────────────────────────────────────────────────────────────────────────────

def encode_chunk_to_base64(waveform_chunk: np.ndarray, sr: int) -> str:
    """Encode a waveform chunk as a base64-encoded WAV string (16-bit PCM)."""
    samples_i16 = np.clip(waveform_chunk * 32767, -32768, 32767).astype(np.int16)
    raw_bytes = samples_i16.tobytes()

    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)       # Mono
        wf.setsampwidth(2)       # 16-bit
        wf.setframerate(sr)
        wf.writeframes(raw_bytes)

    return base64.b64encode(buf.getvalue()).decode("utf-8")


# ──────────────────────────────────────────────────────────────────────────────
# High-level entry point: file -> list of base64 chunks
# ──────────────────────────────────────────────────────────────────────────────

def chunk_audio_file(file_path: str) -> tuple[list[str], dict]:
    """Load an audio file and split it into VAD-segmented, 4s-max base64 chunks.

    This is the main function you'll use. It runs the full pipeline:
        load -> resample -> VAD -> fill gaps -> enforce 4s max -> encode

    Returns:
        chunks: List of base64-encoded WAV strings, each <= 4 seconds.
        metadata: Dict with debug info (duration, sample rate, chunk boundaries).
    """
    # 1. Load audio
    waveform, sr = load_audio(file_path)

    # 2. Resample to 16kHz
    waveform = resample_audio(waveform, sr, TARGET_SAMPLE_RATE)
    sr = TARGET_SAMPLE_RATE

    total_samples = len(waveform)

    # 3. Run VAD to find speech segments
    vad_raw = get_vad_chunks(waveform, sr)

    # 4. Fill gaps so the entire audio is covered
    vad_filled = fill_vad_gaps(vad_raw, total_samples)

    # 5. Split any chunk longer than 4 seconds
    vad_final = enforce_max_chunk_len(vad_filled)

    # 6. Encode each chunk as base64 WAV, padding short chunks to minimum length
    encoded_chunks: list[str] = []
    for start, end in vad_final:
        chunk = waveform[start:end]

        # Pad very short chunks with silence (server rejects < 0.1s audio)
        if len(chunk) < MIN_CHUNK_SAMPLES:
            pad = np.zeros(MIN_CHUNK_SAMPLES - len(chunk), dtype=np.float32)
            chunk = np.concatenate([chunk, pad])

        encoded_chunks.append(encode_chunk_to_base64(chunk, sr))

    metadata = {
        "duration_s": round(total_samples / sr, 3),
        "sample_rate": sr,
        "num_chunks": len(vad_final),
        "vad_raw_segments": len(vad_raw),
        "chunk_boundaries": vad_final,
    }

    return encoded_chunks, metadata
