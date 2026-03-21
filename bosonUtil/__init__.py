"""Boson AI and EigenAI utilities for SayCut."""

from .audio import (
    TARGET_SAMPLE_RATE,
    chunk_audio_file,
    encode_chunk_to_base64,
    load_audio,
    resample_audio,
)
from .api import (
    DEFAULT_BASE_URL,
    DEFAULT_MAX_TOKENS,
    DEFAULT_MODEL,
    DEFAULT_SYSTEM_PROMPT,
    DEFAULT_TEMPERATURE,
    DEFAULT_TOP_P,
    EXTRA_BODY,
    STOP_SEQUENCES,
    build_messages,
    predict,
)
from .tools import (
    CALCULATOR_TOOLS,
    MAX_TOOL_CALLS_PER_TURN,
    build_system_prompt,
    execute_tool_call,
    parse_tool_calls,
    safe_eval_math,
)
from .eigen_config import (
    EIGENAI_BASE_URL,
    EIGENAI_WS_URL,
    resolve_eigenai_api_key,
)
from .eigen_script import generate_script, stream_script
from .eigen_image_gen import generate_image, generate_image_base64
from .eigen_image_edit import edit_image, ImageEditResult
from .eigen_i2v import generate_video, submit_i2v_job, VideoResult
from .eigen_tts import synthesize_speech, synthesize_to_wav, TTSResult
