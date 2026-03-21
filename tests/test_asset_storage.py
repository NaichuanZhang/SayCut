"""Tests for backend.asset_storage — file saving and URL generation."""

import os
import tempfile

import pytest
import pytest_asyncio

from backend.asset_storage import save_asset, get_asset_url


@pytest.fixture
def assets_dir(tmp_path):
    """Use a temporary directory as the assets root."""
    return str(tmp_path)


def test_save_and_get_url(assets_dir):
    """Save bytes and get back a valid URL path."""
    data = b"fake image data"
    rel_path = save_asset(assets_dir, "session123", "scene_1.png", data)

    assert rel_path.startswith("session123/")
    assert rel_path.endswith("scene_1.png")

    # File actually exists on disk
    full_path = os.path.join(assets_dir, rel_path)
    assert os.path.isfile(full_path)
    with open(full_path, "rb") as f:
        assert f.read() == data

    # URL helper returns the expected format
    url = get_asset_url(rel_path)
    assert url == f"/assets/{rel_path}"


def test_creates_session_dir(assets_dir):
    """Session directory is created on first save."""
    session_dir = os.path.join(assets_dir, "new_session")
    assert not os.path.exists(session_dir)

    save_asset(assets_dir, "new_session", "file.wav", b"audio")

    assert os.path.isdir(session_dir)
