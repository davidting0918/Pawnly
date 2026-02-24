# 🤖 Pawnly Bot Play — Implementation Plan

## Overview

Add AI opponent (Stockfish) so players can practice against a bot.
Bot games have a separate lobby flow and separate Elo rating.

---

## 1. Chess Engine Choice

### python-chess built-in engine protocol ✅

We already have `chess` (python-chess) in `requirements.txt`. It includes `chess.engine` which speaks UCI protocol to any engine binary (Stockfish, etc.)

```python
import chess.engine

engine = chess.engine.SimpleEngine.popen_uci("/usr/bin/stockfish")
result = engine.play(board, chess.engine.Limit(time=1.0))
print(result.move)  # e.g. Move.from_uci('e2e4')
engine.quit()
```

### Stockfish binary

- Need Stockfish installed on the server
- `apt install stockfish` (Debian/Ubuntu) or download from stockfishchess.org
- Free, open source, strongest chess engine in the world
- Difficulty control via `Skill Level` (0-20) and search depth/time limits

### Difficulty Levels (map to user-friendly names)

| Display Name | Stockfish Skill | Time Limit | ~Elo |
|-------------|----------------|------------|------|
| Beginner 🟢 | 0 | 0.1s | ~800 |
| Easy 🟡 | 5 | 0.3s | ~1100 |
| Medium 🟠 | 10 | 0.5s | ~1500 |
| Hard 🔴 | 15 | 1.0s | ~2000 |
| Expert 💀 | 20 | 2.0s | ~2500 |

---

## 2. Database Changes

### 2.1 Add `bot_elo` to users table

```sql
-- Migration: Add bot_elo column (separate Elo for bot games)
ALTER TABLE users ADD COLUMN bot_elo INTEGER DEFAULT 1200;
```

### 2.2 Add bot columns to games table

```sql
-- Migration: Add bot game columns
ALTER TABLE games ADD COLUMN is_bot_game BOOLEAN DEFAULT FALSE;
ALTER TABLE games ADD COLUMN bot_difficulty VARCHAR(20) DEFAULT NULL;

-- Index for filtering bot vs human games
CREATE INDEX idx_games_is_bot ON games(is_bot_game);
```

### 2.3 Updated schema.sql (for reference)

```sql
-- Users Table
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(255) NOT NULL UNIQUE,
    hashed_password VARCHAR(255) NOT NULL,
    elo_rating INTEGER DEFAULT 1200,
    bot_elo INTEGER DEFAULT 1200,              -- NEW
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Games Table
CREATE TABLE IF NOT EXISTS games (
    id SERIAL PRIMARY KEY,
    room_code VARCHAR(10) UNIQUE,
    white_player_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    black_player_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    fen TEXT DEFAULT 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1',
    pgn TEXT DEFAULT '',
    status VARCHAR(20) DEFAULT 'waiting',
    winner_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    time_per_move INTEGER DEFAULT NULL,
    is_bot_game BOOLEAN DEFAULT FALSE,         -- NEW
    bot_difficulty VARCHAR(20) DEFAULT NULL,    -- NEW: 'beginner'|'easy'|'medium'|'hard'|'expert'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Summary of SQL to run:
```sql
ALTER TABLE users ADD COLUMN bot_elo INTEGER DEFAULT 1200;
ALTER TABLE games ADD COLUMN is_bot_game BOOLEAN DEFAULT FALSE;
ALTER TABLE games ADD COLUMN bot_difficulty VARCHAR(20) DEFAULT NULL;
CREATE INDEX idx_games_is_bot ON games(is_bot_game);
```

---

## 3. Backend Architecture

### 3.1 New Files

```
backend/
├── core/
│   └── engine.py            # NEW: Stockfish engine wrapper (singleton)
├── services/
│   ├── game_service.py      # Modified: bot game creation, bot Elo
│   └── bot_service.py       # NEW: bot move logic, difficulty config
├── routers/
│   └── game.py              # Modified: bot game endpoints + WS bot logic
```

### 3.2 Engine Wrapper (`core/engine.py`)

```python
"""Stockfish engine singleton — managed lifecycle."""
import chess.engine
import asyncio
from typing import Optional

class ChessEngine:
    _instance: Optional[chess.engine.UciProtocol] = None
    _transport: Optional[asyncio.SubprocessTransport] = None

    @classmethod
    async def get(cls) -> chess.engine.UciProtocol:
        if cls._instance is None:
            transport, engine = await chess.engine.popen_uci("/usr/bin/stockfish")
            cls._transport = transport
            cls._instance = engine
        return cls._instance

    @classmethod
    async def shutdown(cls):
        if cls._instance:
            await cls._instance.quit()
            cls._instance = None
            cls._transport = None
```

### 3.3 Bot Service (`services/bot_service.py`)

```python
"""Bot move generation + difficulty configuration."""
import chess
import chess.engine
from core.engine import ChessEngine

DIFFICULTY_MAP = {
    "beginner":  {"skill": 0,  "time": 0.1, "elo": 800},
    "easy":      {"skill": 5,  "time": 0.3, "elo": 1100},
    "medium":    {"skill": 10, "time": 0.5, "elo": 1500},
    "hard":      {"skill": 15, "time": 1.0, "elo": 2000},
    "expert":    {"skill": 20, "time": 2.0, "elo": 2500},
}

async def get_bot_move(board: chess.Board, difficulty: str) -> chess.Move:
    """Get best move from Stockfish at given difficulty."""
    config = DIFFICULTY_MAP.get(difficulty, DIFFICULTY_MAP["medium"])
    engine = await ChessEngine.get()

    # Set skill level
    await engine.configure({"Skill Level": config["skill"]})

    # Get move with time limit
    result = await engine.play(
        board,
        chess.engine.Limit(time=config["time"])
    )
    return result.move

def get_bot_elo(difficulty: str) -> int:
    """Get approximate Elo for a difficulty level."""
    return DIFFICULTY_MAP.get(difficulty, DIFFICULTY_MAP["medium"])["elo"]
```

### 3.4 Game Service Changes (`services/game_service.py`)

```python
# New function: create bot game
async def create_bot_game(
    user_id: int,
    side: str = "white",
    difficulty: str = "medium",
    time_per_move: Optional[int] = None,
) -> Dict[str, Any]:
    """Create a game against the bot. Immediately active (no waiting)."""
    room_code = generate_room_code()
    
    # User picks a side; bot gets the other
    if side == "white":
        white_id, black_id = user_id, None  # black_player_id NULL = bot
    else:
        white_id, black_id = None, user_id  # white_player_id NULL = bot

    query = """
        INSERT INTO games (
            room_code, white_player_id, black_player_id,
            status, time_per_move, is_bot_game, bot_difficulty
        ) VALUES ($1, $2, $3, 'active', $4, TRUE, $5)
        RETURNING *
    """
    return await db_client.execute_returning(
        query, room_code, white_id, black_id, time_per_move, difficulty
    )


# New function: update bot Elo
async def update_bot_elo_after_game(
    game_id: int, winner_id: Optional[int]
) -> Optional[Dict[str, Any]]:
    """Update user's bot_elo (not regular elo) after a bot game."""
    game = await get_game_by_id(game_id)
    if not game or not game.get("is_bot_game"):
        return None

    # Find the human player
    human_id = game.get("white_player_id") or game.get("black_player_id")
    if not human_id:
        return None

    human = await user_service.get_user_by_id(human_id)
    if not human:
        return None

    old_elo = human.get("bot_elo", 1200)
    bot_elo = bot_service.get_bot_elo(game.get("bot_difficulty", "medium"))

    is_white = game["white_player_id"] == human_id
    if winner_id == human_id:
        result = "white" if is_white else "black"
    elif winner_id is None:
        result = "draw"
    else:
        result = "black" if is_white else "white"

    if is_white:
        new_human_elo, _ = calculate_elo(old_elo, bot_elo, result)
    else:
        _, new_human_elo = calculate_elo(bot_elo, old_elo, result)

    await user_service.update_bot_elo(human_id, new_human_elo)

    return {
        "elo_change": new_human_elo - old_elo,
        "new_elo": new_human_elo,
    }
```

### 3.5 WebSocket Bot Logic (in `routers/game.py`)

The key design: **Bot runs server-side, no second WebSocket connection.**

```
Human connects via WS → sends move → server processes move
→ if bot game & it's bot's turn:
    → asyncio.sleep(0.5-2s)  # "thinking" delay
    → get_bot_move(board, difficulty)
    → push move to board
    → broadcast update back to human
```

```python
# Inside websocket_endpoint, after processing human's move:

if game.get("is_bot_game") and not board.is_game_over():
    current_turn = "w" if board.turn == chess.WHITE else "b"
    bot_side = "w" if game.get("white_player_id") is None else "b"
    
    if current_turn == bot_side:
        # Add realistic "thinking" delay
        difficulty = game.get("bot_difficulty", "medium")
        
        # Bot makes its move
        bot_move = await bot_service.get_bot_move(board, difficulty)
        
        bot_san = board.san(bot_move)
        bot_color = "w" if board.turn == chess.WHITE else "b"
        bot_move_number = board.fullmove_number
        
        board.push(bot_move)
        
        # Check game state
        status = "active"
        winner_id = None
        if board.is_checkmate():
            status = "finished"
            # Bot won (winner_id stays None for bot wins,
            # or we use a sentinel)
            ...
        
        # Save & broadcast
        await game_service.update_game_state(...)
        await game_service.record_move(...)
        
        await manager.broadcast({
            "type": "update",
            "fen": board.fen(),
            "last_move": {
                "from": chess.square_name(bot_move.from_square),
                "to": chess.square_name(bot_move.to_square),
                "san": bot_san,
                "color": bot_color,
                "move_number": bot_move_number,
            },
            "turn": "w" if board.turn == chess.WHITE else "b",
            "check": board.is_check(),
            "checkmate": board.is_checkmate(),
            ...
        }, room_code)
```

### 3.6 Bot Winner Handling

When bot wins, `winner_id` is NULL (no user account for bot).
We distinguish: `winner_id IS NULL AND status = 'finished'` could mean draw OR bot win.

**Solution:** Add result_reason:

```sql
-- Already have gameOverReason in frontend, backend sends reason in WS
-- No extra column needed — we track via:
--   winner_id = NULL + is_bot_game = TRUE → bot won
--   winner_id = NULL + is_bot_game = FALSE → draw
-- OR more explicitly, we can check if the human's king is checkmated
```

Actually, simpler approach: **use a sentinel user ID for the bot.**

```sql
-- Create a bot user row (one-time)
INSERT INTO users (id, username, hashed_password, elo_rating)
VALUES (0, 'Stockfish Bot', 'bot_account', 9999)
ON CONFLICT DO NOTHING;
-- Or use a negative ID convention
```

**Better approach: Use `winner_id = -1` convention for bot wins? No, FK constraint.**

**Best approach: Bot has no winner_id. Frontend determines:**
```
if is_bot_game:
    if winner_id == my_id → I won
    if winner_id IS NULL AND game_over AND not draw → bot won
    if draw → draw
```

This needs no schema changes beyond what we already have.

---

## 4. API Endpoints

### 4.1 New Endpoints

```
POST /api/games/bot              # Create bot game
  Body: { side: "white"|"black", difficulty: "beginner"|...|"expert", time_per_move?: int }
  Response: { id, room_code, status: "active", side, difficulty, is_bot_game: true }
```

### 4.2 Modified Endpoints

```
GET /api/games/{room_code}       # Returns is_bot_game, bot_difficulty fields
GET /api/users/profile           # Returns both elo_rating and bot_elo
GET /api/users/leaderboard       # Add ?type=bot query param for bot leaderboard
GET /api/users/{id}/games        # Add ?type=bot filter
```

---

## 5. Frontend Changes

### 5.1 Home.tsx — Two Lobby Boxes

```
┌─────────────────────────────────┐
│  ♟️ Pawnly                       │
├─────────────────────────────────┤
│                                  │
│  🤖 Play vs Bot                  │  ← NEW card
│  Practice against AI             │
│  [Difficulty picker]             │
│  [Side picker]  [Time picker]    │
│  [Start Game]                    │
│                                  │
│  👥 Play vs Human                │  ← existing (renamed)
│  Create a room & invite friend   │
│  [Side picker]  [Time picker]    │
│  [Create Game]                   │
│                                  │
│  🔗 Join Game                    │  ← existing
│  [Room code input]  [Join]       │
│                                  │
└─────────────────────────────────┘
```

### 5.2 Difficulty Picker Component

```tsx
const DIFFICULTY_OPTIONS = [
  { value: 'beginner', label: 'Beginner', emoji: '🟢', elo: '~800' },
  { value: 'easy',     label: 'Easy',     emoji: '🟡', elo: '~1100' },
  { value: 'medium',   label: 'Medium',   emoji: '🟠', elo: '~1500' },
  { value: 'hard',     label: 'Hard',     emoji: '🔴', elo: '~2000' },
  { value: 'expert',   label: 'Expert',   emoji: '💀', elo: '~2500' },
];
```

### 5.3 Game.tsx Changes

- Bot game: only 1 WS connection (human). No "waiting for opponent" phase
- Show "🤖 Stockfish (Medium)" as opponent name
- Bot's PlayerBar shows difficulty level instead of username
- After bot moves: receive update via WS, animate piece

### 5.4 Profile.tsx Changes

Show two Elo ratings:
```
Human Elo: 1350  📈
Bot Elo:   1180  📉
```

Show game history with "vs Bot (Hard)" or "vs alice"

### 5.5 Leaderboard Changes

Two tabs: "Human" and "Bot"
```
[Human 👥] [Bot 🤖]

# Human Leaderboard        # Bot Leaderboard
1. alice    1450            1. bob      1680
2. bob      1380            2. alice    1520
```

---

## 6. Flow Diagram

```
Human clicks "Play vs Bot" → picks difficulty + side + time
  → POST /api/games/bot → game created (status: active, is_bot_game: true)
  → navigate to /game/{room_code}
  → WS connect → auth → init (no waiting phase!)
  
  If bot plays white (human picked black):
    → Server immediately makes bot's first move (1.e4)
    → Sends update to human
  
  Human moves → WS send move → server validates
    → server processes move
    → if not game_over: server calls get_bot_move()
    → bot "thinks" for 0.5-2s
    → bot move pushed
    → WS update sent to human
    → repeat until game over
  
  Game over → update bot_elo (not regular elo)
  → show result + elo change
```

---

## 7. Implementation Order

| Step | What | Files |
|------|------|-------|
| 1 | Run SQL migration | Neon console |
| 2 | Install Stockfish on server | `apt install stockfish` |
| 3 | `core/engine.py` — Stockfish wrapper | New file |
| 4 | `services/bot_service.py` — difficulty + move gen | New file |
| 5 | `services/game_service.py` — bot game create + bot elo update | Modified |
| 6 | `services/user_service.py` — bot_elo read/write | Modified |
| 7 | `routers/game.py` — POST /games/bot + WS bot logic | Modified |
| 8 | Backend tests for bot games | New tests |
| 9 | Frontend Home.tsx — bot lobby card | Modified |
| 10 | Frontend Game.tsx — bot game UX | Modified |
| 11 | Frontend Profile.tsx — dual Elo | Modified |
| 12 | Frontend Leaderboard.tsx — bot tab | Modified |

---

## 8. Dependencies

### Backend
```
# requirements.txt additions:
# None! chess.engine is included in the chess package we already have.
# Just need Stockfish binary on the server.
```

### Server
```bash
sudo apt install stockfish   # ~15MB
which stockfish              # /usr/bin/stockfish
```

### Frontend
```
# No new npm packages needed
```
