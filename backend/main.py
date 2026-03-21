"""FastAPI application — entry point for the SayCut backend."""

import logging
import os

from fastapi import FastAPI, WebSocket

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.config import ASSETS_DIR
from backend.ws_handler import websocket_endpoint

app = FastAPI(title="SayCut Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure assets directory exists before mounting
os.makedirs(ASSETS_DIR, exist_ok=True)
app.mount("/assets", StaticFiles(directory=ASSETS_DIR), name="assets")


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.websocket("/ws")
async def ws(websocket: WebSocket):
    await websocket_endpoint(websocket)
