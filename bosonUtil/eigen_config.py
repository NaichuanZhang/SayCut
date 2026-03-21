"""Shared configuration for EigenAI API clients."""

import os

EIGENAI_API_KEY_ENV = "EIGENAI_API_KEY"
EIGENAI_BASE_URL = "https://api-web.eigenai.com/api/v1"
EIGENAI_GENERATE_URL = f"{EIGENAI_BASE_URL}/generate"
EIGENAI_WS_URL = "wss://data.eigenai.com/api/v1/generate/ws"


def resolve_eigenai_api_key(api_key: str | None = None) -> str:
    key = api_key or os.environ.get(EIGENAI_API_KEY_ENV)
    if not key:
        raise ValueError(
            f"EigenAI API key required. Pass api_key parameter or set {EIGENAI_API_KEY_ENV} env var."
        )
    return key


def build_auth_headers(api_key: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {api_key}"}
