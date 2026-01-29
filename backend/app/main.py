from fastapi import FastAPI, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.core.database import get_db
from app.api import auth
import uvicorn

app = FastAPI(title="Pawnly API", version="0.1.0")

# Include Routers
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])

@app.get("/")
async def root():
    return {"message": "Welcome to Pawnly API - Easy Chess Platform"}

@app.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)):
    try:
        # Simple query to check DB connection
        result = await db.execute(text("SELECT 1"))
        return {"status": "ok", "db": "connected"}
    except Exception as e:
        return {"status": "error", "db": str(e)}

if __name__ == "__main__":
    # Allow running via `python -m app.main`
    uvicorn.run(app, host="0.0.0.0", port=8000)
