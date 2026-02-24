import logging
import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

logger = logging.getLogger("uvicorn.error")

from core.database import db_client
from core.engine import ChessEngine
from routers import auth, game, users
from services import game_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    await db_client.init_pool()
    # Detect or create time_per_move column
    try:
        row = await db_client.read_one(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_name='games' AND column_name='time_per_move'"
        )
        if row:
            game_service.set_time_column_available(True)
        else:
            async with db_client.get_connection() as conn:
                await conn.execute(
                    "ALTER TABLE games ADD COLUMN IF NOT EXISTS time_per_move INTEGER DEFAULT NULL"
                )
            game_service.set_time_column_available(True)
    except Exception as e:
        logger.warning("Migration note (time_per_move): %s — timer feature will be disabled", e)
        game_service.set_time_column_available(False)
    # Start Stockfish engine if available
    if ChessEngine.is_available():
        try:
            await ChessEngine.get()
            logger.info("Stockfish engine initialized")
        except Exception as e:
            logger.warning("Stockfish init failed: %s — bot games will be unavailable", e)
    else:
        logger.info("Stockfish binary not found — bot games will be unavailable")
    yield
    await ChessEngine.shutdown()
    await db_client.close()


app = FastAPI(title="Pawnly API", version="0.2.0", lifespan=lifespan)

# CORS
origins = [os.getenv("FRONTEND_URL", "http://localhost:5173")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(game.router, prefix="/api", tags=["game"])
app.include_router(users.router, prefix="/api/users", tags=["users"])


@app.get("/")
async def root():
    return {"message": "Welcome to Pawnly API - Easy Chess Platform"}


@app.get("/health")
async def health_check():
    try:
        result = await db_client.read_one("SELECT 1 AS ok")
        if result and result.get("ok") == 1:
            return {"status": "ok", "db": "connected"}
        return {"status": "error", "db": "query failed"}
    except Exception as e:
        return {"status": "error", "db": str(e)}
