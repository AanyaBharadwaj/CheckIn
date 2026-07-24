"""
TeenMind Cloud Server — Render-compatible entry point.

Runs an aiohttp server on PORT that:
  1. Responds to HTTP health checks (GET/HEAD) with 200 OK
  2. Proxies WebSocket connections to the internal pipecat server

The pipecat WebSocket server runs on an internal port (8765) and handles
the actual voice pipeline. This wrapper makes it compatible with Render's
health check requirements.
"""

import asyncio
import os
from pathlib import Path
import aiohttp
from aiohttp import web
import websockets
from loguru import logger

RENDER_PORT = int(os.getenv("PORT", "10000"))
INTERNAL_WS_PORT = 8765


# --- HTTP health check ---

from pathlib import Path

DOCS = Path(__file__).parent / "docs"

async def index(request):
    return web.FileResponse(DOCS / "index.html")


# --- WebSocket proxy to internal pipecat server ---

async def ws_proxy(request):
    client_ws = web.WebSocketResponse()
    await client_ws.prepare(request)

    # Retry connecting to internal pipecat server (may still be starting up)
    pipecat_ws = None
    for attempt in range(10):
        try:
            pipecat_ws = await websockets.connect(
                f"ws://localhost:{INTERNAL_WS_PORT}",
                max_size=None,
            )
            break
        except (ConnectionRefusedError, OSError):
            logger.debug(f"Pipecat server not ready, retry {attempt + 1}/10")
            await asyncio.sleep(1)

    if pipecat_ws is None:
        logger.error("Could not connect to internal pipecat server")
        await client_ws.close(code=1011, message=b"Backend unavailable")
        return client_ws

    logger.info("WebSocket proxy established")

    async def forward_to_pipecat():
        try:
            async for msg in client_ws:
                if msg.type == aiohttp.WSMsgType.BINARY:
                    await pipecat_ws.send(msg.data)
                elif msg.type == aiohttp.WSMsgType.TEXT:
                    await pipecat_ws.send(msg.data)
                elif msg.type in (aiohttp.WSMsgType.CLOSE, aiohttp.WSMsgType.ERROR):
                    break
        except Exception as e:
            logger.debug(f"Client→Pipecat ended: {e}")
        finally:
            await pipecat_ws.close()

    async def forward_to_client():
        try:
            async for msg in pipecat_ws:
                if client_ws.closed:
                    break
                if isinstance(msg, bytes):
                    await client_ws.send_bytes(msg)
                else:
                    await client_ws.send_str(msg)
        except Exception as e:
            logger.debug(f"Pipecat→Client ended: {e}")

    await asyncio.gather(forward_to_pipecat(), forward_to_client())
    return client_ws


# --- Background pipecat voice server ---

async def run_pipecat_loop():
    """Run pipecat sessions in a loop (same as server.py main, but imported)."""
    # Override the port so pipecat uses the internal port, not Render's PORT
    import server
    server.HOST = "0.0.0.0"
    server.PORT = INTERNAL_WS_PORT

    if not server.DEEPGRAM_API_KEY or not server.GEMINI_API_KEY:
        logger.error("Missing API keys — set DEEPGRAM_API_KEY and GEMINI_API_KEY env vars")
        return

    logger.info(f"Pipecat voice server on internal port {INTERNAL_WS_PORT}")
    while True:
        try:
            await server.run_session()
            await asyncio.sleep(1)
        except Exception as e:
            logger.error(f"Pipecat session error: {e}")
            await asyncio.sleep(2)


async def on_startup(app):
    app["pipecat_task"] = asyncio.create_task(run_pipecat_loop())


async def on_cleanup(app):
    app["pipecat_task"].cancel()
    try:
        await app["pipecat_task"]
    except asyncio.CancelledError:
        pass

from pathlib import Path

# --- App setup ---

BASE_DIR = Path(__file__).resolve().parent
DOCS_DIR = BASE_DIR / "docs"

app = web.Application()


async def index(request):
    return web.FileResponse(DOCS_DIR / "index.html")


app.router.add_get("/", index)
app.router.add_get("/health", health)
app.router.add_get("/ws", ws_proxy)

# Serve CSS, JavaScript, images, manifest.json, and other frontend files
app.router.add_static(
    "/",
    path=str(DOCS_DIR),
    show_index=False,
)

app.on_startup.append(on_startup)
app.on_cleanup.append(on_cleanup)

if __name__ == "__main__":
    logger.info(f"TeenMind cloud server starting on port {RENDER_PORT}")
    web.run_app(app, host="0.0.0.0", port=RENDER_PORT)