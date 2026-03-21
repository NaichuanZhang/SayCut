"""Save and serve generated assets (images, audio, video)."""

import os


def save_asset(
    assets_dir: str, session_id: str, filename: str, data: bytes
) -> str:
    """Save bytes to disk. Returns the relative path (session_id/filename)."""
    session_dir = os.path.join(assets_dir, session_id)
    os.makedirs(session_dir, exist_ok=True)

    file_path = os.path.join(session_dir, filename)
    with open(file_path, "wb") as f:
        f.write(data)

    return f"{session_id}/{filename}"


def get_asset_url(rel_path: str) -> str:
    """Convert a relative asset path to a URL path served by FastAPI."""
    return f"/assets/{rel_path}"
