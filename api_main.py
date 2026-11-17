import os
import uvicorn
from app.db import init_db
from api.app import app

if __name__ == "__main__":
    import asyncio
    async def start():
        await init_db()
        config = uvicorn.Config(app, host="0.0.0.0", port=int(os.getenv("PORT", "8000")), log_level="info")
        await uvicorn.Server(config).serve()
    asyncio.run(start())
