import aiosqlite
from typing import Optional
from persistence.base import BaseStateStore

class SqliteStore(BaseStateStore):
    def __init__(self, db_path: str = "sentinelflow.db") -> None:
        self.db_path = db_path
        self._initialized = False

    async def _ensure_table(self) -> None:
        if self._initialized:
            return
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "CREATE TABLE IF NOT EXISTS state_store (key TEXT PRIMARY KEY, value TEXT)"
            )
            await db.commit()
        self._initialized = True

    async def get(self, key: str) -> Optional[str]:
        await self._ensure_table()
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT value FROM state_store WHERE key = ?", (key,)) as cursor:
                row = await cursor.fetchone()
                if row:
                    return str(row[0])
                return None

    async def set(self, key: str, value: str) -> None:
        await self._ensure_table()
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT OR REPLACE INTO state_store (key, value) VALUES (?, ?)", 
                (key, value)
            )
            await db.commit()
