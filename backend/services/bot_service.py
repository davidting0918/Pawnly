"""Bot move generation + difficulty configuration."""

import asyncio
import chess
import chess.engine
from core.engine import ChessEngine
from typing import Dict, Any

DIFFICULTY_MAP: Dict[str, Dict[str, Any]] = {
    "beginner": {"skill": 0, "time": 0.1, "depth": 1, "elo": 800},
    "easy": {"skill": 5, "time": 0.3, "depth": 4, "elo": 1100},
    "medium": {"skill": 10, "time": 0.5, "depth": 8, "elo": 1500},
    "hard": {"skill": 15, "time": 1.0, "depth": 12, "elo": 2000},
    "expert": {"skill": 20, "time": 2.0, "depth": 20, "elo": 2500},
}

VALID_DIFFICULTIES = list(DIFFICULTY_MAP.keys())

# Minimum "thinking" delay so moves don't feel instant (seconds)
MIN_THINK_DELAY = 0.4


def get_difficulty_config(difficulty: str) -> Dict[str, Any]:
    """Get engine config for a difficulty level."""
    return DIFFICULTY_MAP.get(difficulty, DIFFICULTY_MAP["medium"])


def get_bot_elo(difficulty: str) -> int:
    """Get approximate Elo for a difficulty level."""
    return get_difficulty_config(difficulty)["elo"]


def get_bot_display_name(difficulty: str) -> str:
    """Get display name for the bot at a difficulty level."""
    labels = {
        "beginner": "🟢 Bot (Beginner)",
        "easy": "🟡 Bot (Easy)",
        "medium": "🟠 Bot (Medium)",
        "hard": "🔴 Bot (Hard)",
        "expert": "💀 Bot (Expert)",
    }
    return labels.get(difficulty, "🤖 Bot")


async def get_bot_move(board: chess.Board, difficulty: str) -> chess.Move:
    """Get a move from Stockfish at the given difficulty.

    Includes a minimum delay so moves don't appear instant.
    """
    config = get_difficulty_config(difficulty)
    engine = await ChessEngine.get()

    def _think():
        engine.configure({"Skill Level": config["skill"]})
        return engine.play(
            board,
            chess.engine.Limit(
                time=config["time"],
                depth=config["depth"],
            ),
        )

    result, _ = await asyncio.gather(
        asyncio.to_thread(_think),
        asyncio.sleep(MIN_THINK_DELAY),
    )

    if result.move is None:
        raise RuntimeError("Stockfish returned no move")

    return result.move
