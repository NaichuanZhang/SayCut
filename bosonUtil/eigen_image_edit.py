"""EigenAI image editing client using qwen-image-edit-2511 model."""

import base64
from dataclasses import dataclass
from pathlib import Path

import httpx

from .eigen_config import EIGENAI_GENERATE_URL, build_auth_headers, resolve_eigenai_api_key

DEFAULT_MODEL = "qwen-image-edit-2511"
DEFAULT_NUM_INFERENCE_STEPS = 4
DEFAULT_GUIDANCE_SCALE = 4.0
MAX_SOURCE_IMAGES = 9
TIMEOUT_S = 180.0


@dataclass(frozen=True)
class ImageEditResult:
    image_bytes: bytes
    image_base64: str
    use_lightning: bool
    processing_time_seconds: float


def _detect_content_type(path: str) -> str:
    suffix = Path(path).suffix.lower()
    types = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}
    return types.get(suffix, "image/jpeg")


async def edit_image(
    prompt: str,
    image_paths: list[str],
    *,
    model: str = DEFAULT_MODEL,
    num_inference_steps: int = DEFAULT_NUM_INFERENCE_STEPS,
    guidance_scale: float = DEFAULT_GUIDANCE_SCALE,
    seed: int | None = None,
    api_key: str | None = None,
) -> ImageEditResult:
    if not image_paths:
        raise ValueError("At least one source image is required.")
    if len(image_paths) > MAX_SOURCE_IMAGES:
        raise ValueError(f"Maximum {MAX_SOURCE_IMAGES} source images allowed, got {len(image_paths)}.")

    key = resolve_eigenai_api_key(api_key)
    headers = build_auth_headers(key)

    data = {
        "model": model,
        "prompt": prompt,
        "num_inference_steps": str(num_inference_steps),
        "guidance_scale": str(guidance_scale),
    }
    if seed is not None:
        data["seed"] = str(seed)

    files = []
    file_handles = []
    try:
        for path in image_paths:
            fh = open(path, "rb")  # noqa: SIM115
            file_handles.append(fh)
            content_type = _detect_content_type(path)
            files.append(("images", (Path(path).name, fh, content_type)))

        async with httpx.AsyncClient(timeout=TIMEOUT_S) as client:
            response = await client.post(
                EIGENAI_GENERATE_URL, headers=headers, data=data, files=files
            )
            response.raise_for_status()
    finally:
        for fh in file_handles:
            fh.close()

    result = response.json()
    b64 = result.get("image_base64", "")
    if not b64:
        raise ValueError(f"No image_base64 in response. Keys: {list(result.keys())}")

    return ImageEditResult(
        image_bytes=base64.b64decode(b64),
        image_base64=b64,
        use_lightning=result.get("use_lightning", False),
        processing_time_seconds=result.get("processing_time_seconds", 0.0),
    )
