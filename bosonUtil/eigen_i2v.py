"""EigenAI image-to-video client using wan2p2-i2v-14b-turbo model."""

import asyncio
from dataclasses import dataclass
from pathlib import Path

import httpx

from .eigen_config import EIGENAI_BASE_URL, EIGENAI_GENERATE_URL, build_auth_headers, resolve_eigenai_api_key

DEFAULT_MODEL = "wan2p2-i2v-14b-turbo"
DEFAULT_INFER_STEPS = 5
DEFAULT_POLL_INTERVAL_S = 2.0
DEFAULT_MAX_POLL_ATTEMPTS = 150  # ~5 min at 2s intervals
STATUS_COMPLETED = "completed"
STATUS_FAILED = "failed"
TIMEOUT_S = 300.0

STATUS_URL = f"{EIGENAI_BASE_URL}/generate/status"
RESULT_URL = f"{EIGENAI_BASE_URL}/generate/result"


@dataclass(frozen=True)
class VideoResult:
    video_bytes: bytes
    task_id: str


async def submit_i2v_job(
    prompt: str,
    image_path: str,
    *,
    model: str = DEFAULT_MODEL,
    infer_steps: int = DEFAULT_INFER_STEPS,
    seed: int | None = None,
    api_key: str | None = None,
) -> str:
    key = resolve_eigenai_api_key(api_key)
    headers = build_auth_headers(key)

    data = {
        "model": model,
        "prompt": prompt,
        "infer_steps": str(infer_steps),
    }
    if seed is not None:
        data["seed"] = str(seed)

    with open(image_path, "rb") as f:
        content_type = "image/jpeg" if Path(image_path).suffix.lower() in (".jpg", ".jpeg") else "image/png"
        files = {"image": (Path(image_path).name, f, content_type)}

        async with httpx.AsyncClient(timeout=TIMEOUT_S) as client:
            response = await client.post(
                EIGENAI_GENERATE_URL, headers=headers, data=data, files=files
            )
            response.raise_for_status()

    result = response.json()
    task_id = result.get("task_id")
    if not task_id:
        raise ValueError(f"No task_id in response. Keys: {list(result.keys())}")
    return task_id


async def poll_job_status(
    task_id: str,
    model: str = DEFAULT_MODEL,
    *,
    api_key: str | None = None,
) -> str:
    key = resolve_eigenai_api_key(api_key)
    headers = build_auth_headers(key)
    params = {"jobId": task_id, "model": model}

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.get(STATUS_URL, headers=headers, params=params)
        response.raise_for_status()

    return response.json().get("status", "unknown")


async def fetch_job_result(
    task_id: str,
    model: str = DEFAULT_MODEL,
    *,
    api_key: str | None = None,
) -> bytes:
    key = resolve_eigenai_api_key(api_key)
    headers = build_auth_headers(key)
    params = {"jobId": task_id, "model": model}

    async with httpx.AsyncClient(timeout=TIMEOUT_S) as client:
        response = await client.get(RESULT_URL, headers=headers, params=params)
        response.raise_for_status()

    return response.content


async def generate_video(
    prompt: str,
    image_path: str,
    *,
    model: str = DEFAULT_MODEL,
    infer_steps: int = DEFAULT_INFER_STEPS,
    seed: int | None = None,
    poll_interval: float = DEFAULT_POLL_INTERVAL_S,
    max_poll_attempts: int = DEFAULT_MAX_POLL_ATTEMPTS,
    api_key: str | None = None,
) -> VideoResult:
    key = resolve_eigenai_api_key(api_key)

    task_id = await submit_i2v_job(
        prompt, image_path, model=model, infer_steps=infer_steps, seed=seed, api_key=key
    )

    for _ in range(max_poll_attempts):
        status = await poll_job_status(task_id, model, api_key=key)

        if status == STATUS_COMPLETED:
            video_bytes = await fetch_job_result(task_id, model, api_key=key)
            return VideoResult(video_bytes=video_bytes, task_id=task_id)

        if status == STATUS_FAILED:
            raise RuntimeError(f"Video generation failed for task {task_id}")

        await asyncio.sleep(poll_interval)

    raise TimeoutError(
        f"Video generation timed out after {max_poll_attempts * poll_interval:.0f}s for task {task_id}"
    )
