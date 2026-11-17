from pathlib import Path
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from api.routes import router
from app.db import init_db

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app):
    await init_db()
    yield

app = FastAPI(title="CHORVA PRO API", version="2.4.1", description="CHORVA PRO Web App va Telegram Mini App backend", lifespan=lifespan)
origins = [x.strip() for x in os.getenv("CORS_ORIGINS", "*").split(",") if x.strip()]
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=False, allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"], allow_headers=["Content-Type", "X-Telegram-Init-Data", "X-Dev-Telegram-Id"])
app.include_router(router)

DIST = Path(__file__).resolve().parent.parent / "webapp" / "dist"
if DIST.exists():
    assets = DIST / "assets"
    if assets.exists(): app.mount("/assets", StaticFiles(directory=assets), name="assets")
    @app.get("/", include_in_schema=False)
    async def web_index(): return FileResponse(DIST / "index.html")
    @app.get("/{path:path}", include_in_schema=False)
    async def web_fallback(path: str):
        candidate = DIST / path
        if candidate.is_file(): return FileResponse(candidate)
        return FileResponse(DIST / "index.html")
