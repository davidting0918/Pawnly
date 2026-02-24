"""Stockfish engine singleton.

Uses chess.engine.SimpleEngine with a workaround for Windows: uvicorn sets
WindowsSelectorEventLoopPolicy which does not support subprocess creation.
We temporarily switch to WindowsProactorEventLoopPolicy during engine init.
"""

import asyncio
import sys
import chess.engine
import os
import threading
from typing import Optional

STOCKFISH_PATH = os.getenv("STOCKFISH_PATH")


class ChessEngine:
    """Thread-safe Stockfish engine wrapper (singleton)."""

    _engine: Optional[chess.engine.SimpleEngine] = None
    _lock: threading.Lock = threading.Lock()

    @classmethod
    def _open(cls) -> chess.engine.SimpleEngine:
        with cls._lock:
            if cls._engine is not None:
                return cls._engine

            if sys.platform == "win32":
                original_policy = asyncio.get_event_loop_policy()
                asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
                try:
                    cls._engine = chess.engine.SimpleEngine.popen_uci(STOCKFISH_PATH)
                finally:
                    asyncio.set_event_loop_policy(original_policy)
            else:
                cls._engine = chess.engine.SimpleEngine.popen_uci(STOCKFISH_PATH)

            return cls._engine

    @classmethod
    async def get(cls) -> chess.engine.SimpleEngine:
        """Get or lazily create the Stockfish engine."""
        if cls._engine is not None:
            return cls._engine
        return await asyncio.to_thread(cls._open)

    @classmethod
    async def shutdown(cls) -> None:
        """Gracefully shut down the engine."""
        def _quit():
            with cls._lock:
                if cls._engine is not None:
                    try:
                        cls._engine.quit()
                    except Exception:
                        pass
                    cls._engine = None
        await asyncio.to_thread(_quit)

    @classmethod
    def is_available(cls) -> bool:
        """Check if Stockfish binary path is configured and exists."""
        return bool(STOCKFISH_PATH) and os.path.isfile(STOCKFISH_PATH)
