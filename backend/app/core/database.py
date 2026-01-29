from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL is not set in .env")

# Ensure async driver is used
if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

# Handle SSL mode for asyncpg
connect_args = {}
if "sslmode=require" in DATABASE_URL:
    # Remove query params from URL for asyncpg as we pass them in connect_args
    # Or rely on asyncpg parsing? asyncpg usually prefers 'ssl': 'require' in connect_args
    # Let's clean the URL and use connect_args
    DATABASE_URL = DATABASE_URL.split("?")[0]
    connect_args = {"ssl": "require"}

engine = create_async_engine(DATABASE_URL, echo=True, connect_args=connect_args)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

class Base(DeclarativeBase):
    pass

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
