import os
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
def normalize_database_url(value: str) -> str:
    """Make standard Neon/Postgres URLs compatible with SQLAlchemy asyncpg."""
    value = (value or "sqlite+aiosqlite:///./chorva_pro.db").strip()
    if value.startswith("postgres://"):
        value = "postgresql://" + value[len("postgres://"):]
    if value.startswith("postgresql://"):
        value = "postgresql+asyncpg://" + value[len("postgresql://"):]
    if value.startswith("postgresql+asyncpg://"):
        parts = urlsplit(value)
        query = []
        for key, val in parse_qsl(parts.query, keep_blank_values=True):
            if key == "channel_binding":
                continue
            if key == "sslmode":
                key = "ssl"
            query.append((key, val))
        value = urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))
    return value

DATABASE_URL = normalize_database_url(os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./chorva_pro.db"))
TIMEZONE = os.getenv("TIMEZONE", "Asia/Tashkent").strip()
DATA_DIR = os.getenv("DATA_DIR", "./data").strip()
ADMIN_IDS = {int(x.strip()) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip().isdigit()}

WEBAPP_URL = os.getenv("WEBAPP_URL", "").strip()
