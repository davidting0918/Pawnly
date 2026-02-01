from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import os

from app.core.database import db_client
from app.api import auth, game, users

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await db_client.init_pool()
    yield
    # Shutdown
    await db_client.close()

app = FastAPI(title="Pawnly API", version="0.1.0", lifespan=lifespan)

# CORS Setup
origins = [os.getenv("FRONTEND_URL", "http://localhost:5173")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(game.router, prefix="/api", tags=["game"])
app.include_router(users.router, prefix="/api/users", tags=["users"])

@app.get("/")
async def root():
    return {"message": "Welcome to Pawnly API - Easy Chess Platform"}

@app.get("/health")
async def health_check():
    try:
        # Simple query to check DB connection
        result = await db_client.read_one("SELECT 1")
        # asyncpg returns keys like '?column?' for unnamed columns
        if result and result.get('?column?') == 1:
            return {"status": "ok", "db": "connected"}
        else:
            return {"status": "error", "db": "query failed"}
    except Exception as e:
        return {"status": "error", "db": str(e)}
