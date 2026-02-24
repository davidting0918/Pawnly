"""Stockfish engine singleton — async lifecycle management."""

import asyncio
import chess.engine
import os
from typing import Optional

# Path to Stockfish binary — override with STOCKFISH_PATH env var
STOCKFISH_PATH = os.getenv("STOCKFISH_PATH", "/usr/games/stockfish")


class ChessEngine:
    """Async Stockfish engine wrapper (singleton)."""

    _engine: Optional[chess.engine.UciProtocol] = None
    _lock: asyncio.Lock = asyncio.Lock()

    @classmethod
    async def get(cls) -> chess.engine.UciProtocol:
        """Get or create the Stockfish engine instance."""
        if cls._engine is not None:
            return cls._engine

        async with cls._lock:
            # Double-check after acquiring lock
            if cls._engine is not None:
                return cls._engine

            _transport, engine = await chess.engine.popen_uci(STOCKFISH_PATH)
            cls._engine = engine
            return engine

    @classmethod
    async def shutdown(cls) -> None:
        """Gracefully shut down the engine."""
        async with cls._lock:
            if cls._engine is not None:
                try:
                    await cls._engine.quit()
                except Exception:
                    pass
                cls._engine = None

    @classmethod
    def is_available(cls) -> bool:
        """Check if Stockfish binary exists."""
        return os.path.isfile(STOCKFISH_PATH)
