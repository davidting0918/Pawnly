import os
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional
import asyncpg
from asyncpg import Pool
from dotenv import load_dotenv

load_dotenv()

class PostgresAsyncClient:
    _instance: Optional['PostgresAsyncClient'] = None

    def __init__(self):
        self.connection_string = os.getenv("DATABASE_URL")
        if not self.connection_string:
            # Fallback or error - better to fail early
            print("Warning: DATABASE_URL not set.")
        self._pool: Optional[Pool] = None

    @classmethod
    def get_instance(cls) -> 'PostgresAsyncClient':
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    async def init_pool(self):
        if not self._pool and self.connection_string:
            # Handle sslmode query param manually if needed, or let asyncpg handle it if formatted correctly
            # asyncpg prefers dsns without unknown query params.
            # Clean DSN if it contains ?sslmode=require which might confuse simple parsers
            # But asyncpg usually handles standard DSNs well.
            self._pool = await asyncpg.create_pool(
                self.connection_string,
                min_size=1,
                max_size=20
            )

    async def close(self):
        if self._pool:
            await self._pool.close()
            self._pool = None

    @asynccontextmanager
    async def get_connection(self):
        if not self._pool:
            await self.init_pool()
        if not self._pool:
             raise RuntimeError("Database pool not initialized")
        async with self._pool.acquire() as connection:
            yield connection

    async def read(self, query: str, *args: Any) -> List[Dict[str, Any]]:
        async with self.get_connection() as conn:
            rows = await conn.fetch(query, *args)
            return [dict(row) for row in rows]

    async def read_one(self, query: str, *args: Any) -> Optional[Dict[str, Any]]:
        async with self.get_connection() as conn:
            row = await conn.fetchrow(query, *args)
            return dict(row) if row else None

    async def execute(self, query: str, *args: Any) -> str:
        async with self.get_connection() as conn:
            return await conn.execute(query, *args)
            
    async def execute_returning(self, query: str, *args: Any) -> Optional[Dict[str, Any]]:
        async with self.get_connection() as conn:
            row = await conn.fetchrow(query, *args)
            return dict(row) if row else None

# Singleton
db_client = PostgresAsyncClient.get_instance()
