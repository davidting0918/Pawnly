-- Pawnly Database Schema

-- Users Table
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(255) NOT NULL UNIQUE,
    hashed_password VARCHAR(255) NOT NULL,
    elo_rating INTEGER DEFAULT 1200,
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
    status VARCHAR(20) DEFAULT 'waiting', -- waiting, active, finished, aborted
    winner_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Moves Table (Optional log for detailed history)
CREATE TABLE IF NOT EXISTS moves (
    id SERIAL PRIMARY KEY,
    game_id INTEGER REFERENCES games(id) ON DELETE CASCADE,
    move_number INTEGER NOT NULL,
    color VARCHAR(1) NOT NULL, -- 'w' or 'b'
    san VARCHAR(10) NOT NULL,  -- e.g. "Nf3"
    uci VARCHAR(10) NOT NULL,  -- e.g. "g1f3"
    fen_after TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_games_room_code ON games(room_code);
CREATE INDEX IF NOT EXISTS idx_moves_game_id ON moves(game_id);
