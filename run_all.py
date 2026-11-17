"""Run Telegram polling bot and FastAPI Web App backend in one service."""
import asyncio
import logging
import os
import uvicorn
from app.db import init_db
from main import run_bot
from api.app import app

logging.basicConfig(level=logging.INFO)

async def serve_api():
    config = uvicorn.Config(app, host="0.0.0.0", port=int(os.getenv("PORT", "8000")), log_level="info", proxy_headers=True)
    server = uvicorn.Server(config)
    await server.serve()

async def main():
    await init_db()
    await asyncio.gather(run_bot(initialize=False), serve_api())

if __name__ == "__main__":
    asyncio.run(main())
