import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

from core.database import db_client
from routers import auth, game, users


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await db_client.init_pool()
    yield
    # Shutdown
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
