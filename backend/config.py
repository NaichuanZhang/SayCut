"""Backend configuration — env vars and paths."""

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ASSETS_DIR = str(PROJECT_ROOT / "generated_assets")
DB_PATH = str(PROJECT_ROOT / "saycut.db")

BOSONAI_API_KEY = os.environ.get("BOSONAI_API_KEY", "")
EIGENAI_API_KEY = os.environ.get("EIGENAI_API_KEY", "")

BACKEND_PORT = 3001
