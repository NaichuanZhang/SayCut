"""EigenAI script generation client using gpt-oss-120b (OpenAI-compatible)."""

from collections.abc import AsyncIterator

from openai import AsyncOpenAI

from .eigen_config import EIGENAI_BASE_URL, resolve_eigenai_api_key

DEFAULT_MODEL = "gpt-oss-120b"
DEFAULT_TEMPERATURE = 0.7
DEFAULT_REASONING_EFFORT = "medium"
DEFAULT_MAX_TOKENS = 2000


async def generate_script(
    messages: list[dict],
    *,
    model: str = DEFAULT_MODEL,
    temperature: float = DEFAULT_TEMPERATURE,
    reasoning_effort: str = DEFAULT_REASONING_EFFORT,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    api_key: str | None = None,
) -> str:
    key = resolve_eigenai_api_key(api_key)
    client = AsyncOpenAI(base_url=EIGENAI_BASE_URL, api_key=key, timeout=180.0)

    response = await client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
        extra_body={"reasoning_effort": reasoning_effort},
        stream=False,
    )

    return response.choices[0].message.content or ""


async def stream_script(
    messages: list[dict],
    *,
    model: str = DEFAULT_MODEL,
    temperature: float = DEFAULT_TEMPERATURE,
    reasoning_effort: str = DEFAULT_REASONING_EFFORT,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    api_key: str | None = None,
) -> AsyncIterator[str]:
    key = resolve_eigenai_api_key(api_key)
    client = AsyncOpenAI(base_url=EIGENAI_BASE_URL, api_key=key, timeout=180.0)

    stream = await client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
        extra_body={"reasoning_effort": reasoning_effort},
        stream=True,
    )

    async for chunk in stream:
        delta = chunk.choices[0].delta.content
        if delta:
            yield delta
