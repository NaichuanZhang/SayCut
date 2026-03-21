"""HiggsAudioM3 API client — configuration, message building, and prediction."""

import os

from openai import OpenAI

from .audio import chunk_audio_file

# ──────────────────────────────────────────────────────────────────────────────
# API Configuration
# ──────────────────────────────────────────────────────────────────────────────

DEFAULT_BASE_URL = "https://hackathon.boson.ai/v1"
DEFAULT_MODEL = "higgs-audio-understanding-v3.5-Hackathon"
DEFAULT_SYSTEM_PROMPT = (
    "You are a helpful voice assistant. Chat with the user in a friendly "
    "and engaging manner. Keep the response concise and natural."
)

# Stop sequences — required for correct behavior with the HiggsAudioM3 API.
STOP_SEQUENCES = [
    "<|eot_id|>",
    "<|endoftext|>",
    "<|audio_eos|>",
    "<|im_end|>",
]

# Extra parameters for the API backend
EXTRA_BODY = {"skip_special_tokens": False}

# Generation parameters
DEFAULT_TEMPERATURE = 0.2
DEFAULT_TOP_P = 0.9
DEFAULT_MAX_TOKENS = 4096


# ──────────────────────────────────────────────────────────────────────────────
# Build the message payload
# ──────────────────────────────────────────────────────────────────────────────

def build_messages(
    audio_chunks: list[str],
    system_prompt: str = DEFAULT_SYSTEM_PROMPT,
    user_text: str | None = None,
) -> list[dict]:
    """Build OpenAI-format messages with audio chunks embedded.

    The API expects audio as multiple `audio_url` content parts within
    a single user message. Each chunk is base64-encoded WAV data with an
    indexed MIME type: `data:audio/wav_{i};base64,...`
    """
    user_content: list[dict] = []

    if user_text:
        user_content.append({"type": "text", "text": user_text})

    for i, chunk_b64 in enumerate(audio_chunks):
        user_content.append({
            "type": "audio_url",
            "audio_url": {"url": f"data:audio/wav_{i};base64,{chunk_b64}"},
        })

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_content},
    ]


# ──────────────────────────────────────────────────────────────────────────────
# Call the API
# ──────────────────────────────────────────────────────────────────────────────

def predict(
    audio_path: str,
    system_prompt: str = DEFAULT_SYSTEM_PROMPT,
    user_text: str | None = None,
    base_url: str = DEFAULT_BASE_URL,
    model: str = DEFAULT_MODEL,
    api_key: str | None = None,
    stream: bool = False,
    temperature: float = DEFAULT_TEMPERATURE,
    top_p: float = DEFAULT_TOP_P,
    max_tokens: int = DEFAULT_MAX_TOKENS,
) -> str:
    """Send an audio file to HiggsAudioM3 and return the text response."""
    # 1. Chunk the audio
    print(f"Loading and chunking audio: {audio_path}")
    audio_chunks, meta = chunk_audio_file(audio_path)
    print(f"  Duration: {meta['duration_s']}s -> {meta['num_chunks']} chunks")

    # 2. Build messages
    messages = build_messages(
        audio_chunks=audio_chunks,
        system_prompt=system_prompt,
        user_text=user_text,
    )

    # 3. Create the API client
    resolved_api_key = api_key or os.environ.get("BOSONAI_API_KEY", "EMPTY")
    client = OpenAI(
        base_url=base_url,
        api_key=resolved_api_key,
        timeout=180.0,
        max_retries=3,
    )

    # 4. Call the API
    api_kwargs = dict(
        model=model,
        messages=messages,
        temperature=temperature,
        top_p=top_p,
        max_tokens=max_tokens,
        stop=STOP_SEQUENCES,
        extra_body=EXTRA_BODY,
    )

    if stream:
        print("\nResponse (streaming):")
        print("-" * 40)
        response_stream = client.chat.completions.create(stream=True, **api_kwargs)
        full_response = ""
        for chunk in response_stream:
            delta = chunk.choices[0].delta
            if delta.content:
                print(delta.content, end="", flush=True)
                full_response += delta.content
        print()
        print("-" * 40)
        return full_response.strip()
    else:
        response = client.chat.completions.create(**api_kwargs)
        text = ""
        if response.choices and response.choices[0].message:
            text = (response.choices[0].message.content or "").strip()
        print(f"\nResponse:\n{text}")
        return text
