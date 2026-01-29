from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    elo_rating = Column(Integer, default=1200)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    games_as_white = relationship("Game", foreign_keys="Game.white_player_id", back_populates="white_player")
    games_as_black = relationship("Game", foreign_keys="Game.black_player_id", back_populates="black_player")

class Game(Base):
    __tablename__ = "games"

    id = Column(Integer, primary_key=True, index=True)
    room_code = Column(String(6), unique=True, index=True) # For inviting friends
    
    white_player_id = Column(Integer, ForeignKey("users.id"), nullable=True) # Nullable for "waiting for player"
    black_player_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    # Game State
    fen = Column(Text, default="rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1")
    pgn = Column(Text, default="")
    status = Column(String, default="waiting") # waiting, active, finished, aborted
    winner_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    white_player = relationship("User", foreign_keys=[white_player_id], back_populates="games_as_white")
    black_player = relationship("User", foreign_keys=[black_player_id], back_populates="games_as_black")
    moves = relationship("Move", back_populates="game")

class Move(Base):
    __tablename__ = "moves"
    
    id = Column(Integer, primary_key=True, index=True)
    game_id = Column(Integer, ForeignKey("games.id"))
    move_number = Column(Integer)
    color = Column(String(1)) # 'w' or 'b'
    san = Column(String(10)) # e.g. "Nf3"
    uci = Column(String(10)) # e.g. "g1f3"
    fen_after = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    game = relationship("Game", back_populates="moves")
