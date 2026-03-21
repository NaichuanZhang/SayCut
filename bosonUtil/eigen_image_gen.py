"""EigenAI image generation client using eigen-image model."""

import base64

import httpx

from .eigen_config import EIGENAI_GENERATE_URL, build_auth_headers, resolve_eigenai_api_key

DEFAULT_MODEL = "eigen-image"
TIMEOUT_S = 120.0


async def generate_image(
    prompt: str,
    *,
    model: str = DEFAULT_MODEL,
    api_key: str | None = None,
) -> bytes:
    b64 = await generate_image_base64(prompt, model=model, api_key=api_key)
    return base64.b64decode(b64)


async def generate_image_base64(
    prompt: str,
    *,
    model: str = DEFAULT_MODEL,
    api_key: str | None = None,
) -> str:
    key = resolve_eigenai_api_key(api_key)
    headers = {**build_auth_headers(key), "Content-Type": "application/json"}
    payload = {"model": model, "prompt": prompt}

    async with httpx.AsyncClient(timeout=TIMEOUT_S) as client:
        response = await client.post(EIGENAI_GENERATE_URL, headers=headers, json=payload)
        response.raise_for_status()

    result = response.json()
    b64 = result.get("turbo_image_base64")
    if not b64:
        raise ValueError(f"No turbo_image_base64 in response. Keys: {list(result.keys())}")
    return b64
