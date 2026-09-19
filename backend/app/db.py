import asyncpg
from pathlib import Path
from .config import settings

async def pool():
    return await asyncpg.create_pool(settings().database_url, min_size=1, max_size=10, command_timeout=30)

async def initialize(p):
    async with p.acquire() as conn:
        await conn.execute(Path(__file__).with_name('schema.sql').read_text())
