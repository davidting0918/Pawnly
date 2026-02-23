import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Chess } from 'chess.js';
import { Chessboard } from 'react-chessboard';
import { useParams, useNavigate } from 'react-router-dom';
import { useSelector } from 'react-redux';
import type { RootState } from '../store/store';
import apiClient from '../api/axios';
import { ArrowLeft, Copy, Check, WifiOff, Flag, RotateCcw, Clock, ShieldX } from 'lucide-react';

type GamePhase = 'loading' | 'joining' | 'waiting' | 'playing' | 'finished' | 'blocked';

const Game: React.FC = () => {
  const { id: roomCode } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const user = useSelector((state: RootState) => state.auth.user);

  const [game, setGame] = useState(new Chess());
  const [isConnected, setIsConnected] = useState(false);
  const [copied, setCopied] = useState(false);
  const [phase, setPhase] = useState<GamePhase>('loading');
  const [mySide, setMySide] = useState<'w' | 'b' | null>(null);
  const [gameOverReason, setGameOverReason] = useState('');
  const [winnerId, setWinnerId] = useState<number | null>(null);
  const [errorMsg, setErrorMsg] = useState('');
  const ws = useRef<WebSocket | null>(null);

  // Step 1: Check game state and auto-join if needed
  useEffect(() => {
    if (!user || !roomCode) return;

    const initGame = async () => {
      try {
        // Try to get game info
        const res = await apiClient.get(`/api/games/${roomCode}`);
        const gameData = res.data;

        const isWhite = gameData.white_player_id === user.id;
        const isBlack = gameData.black_player_id === user.id;

        if (isWhite || isBlack) {
          // Already a player
          setMySide(isWhite ? 'w' : 'b');
          setPhase(gameData.status === 'waiting' ? 'waiting' : 'playing');
          connectWs();
        } else if (gameData.status === 'waiting') {
          // Not a player yet, try to join
          setPhase('joining');
          try {
            const joinRes = await apiClient.post(`/api/games/${roomCode}/join`);
            setMySide(joinRes.data.side === 'white' ? 'w' : 'b');
            setPhase('playing');
            connectWs();
          } catch (joinErr: any) {
            setErrorMsg(joinErr.response?.data?.detail || 'Failed to join game');
            setPhase('blocked');
          }
        } else {
          // Game is active/finished and user is not a player
          setPhase('blocked');
          setErrorMsg('You are not a player in this game');
        }
      } catch (err: any) {
        if (err.response?.status === 403) {
          setPhase('blocked');
          setErrorMsg('You are not a player in this game');
        } else if (err.response?.status === 404) {
          setPhase('blocked');
          setErrorMsg('Game not found');
        } else {
          setPhase('blocked');
          setErrorMsg('Failed to load game');
        }
      }
    };

    const connectWs = () => {
      const wsUrl = import.meta.env.VITE_WS_URL || 'ws://localhost:8000';
      const socket = new WebSocket(`${wsUrl}/api/ws/game/${roomCode}`);

      socket.onopen = () => {
        // Send auth message first
        socket.send(JSON.stringify({ type: 'auth', user_id: user.id }));
        setIsConnected(true);
      };

      socket.onmessage = (event) => {
        const data = JSON.parse(event.data);

        if (data.type === 'init') {
          setGame(new Chess(data.fen));
          setMySide(data.your_side);
          if (data.status === 'waiting') {
            setPhase('waiting');
          } else {
            setPhase('playing');
          }
        } else if (data.type === 'update') {
          setGame(new Chess(data.fen));
          if (data.status === 'active' && phase === 'waiting') {
            setPhase('playing');
          }
          if (data.game_over) {
            setPhase('finished');
            setWinnerId(data.winner_id ?? null);
            if (data.checkmate) setGameOverReason('Checkmate');
            else if (data.stalemate) setGameOverReason('Stalemate');
            else setGameOverReason('Draw');
          }
        } else if (data.type === 'game_over') {
          setPhase('finished');
          setWinnerId(data.winner_id ?? null);
          setGameOverReason(data.reason === 'resign' ? 'Resignation' : 'Game Over');
          if (data.fen) setGame(new Chess(data.fen));
        } else if (data.type === 'error') {
          console.error('Server:', data.message);
          if (data.message.includes('not a player')) {
            setPhase('blocked');
            setErrorMsg(data.message);
          }
        }
      };

      socket.onclose = () => setIsConnected(false);
      ws.current = socket;
    };

    initGame();

    return () => {
      if (ws.current) ws.current.close();
    };
  }, [roomCode, user]);

  const onDrop = useCallback((sourceSquare: string, targetSquare: string) => {
    if (phase !== 'playing') return false;
    if (!ws.current || ws.current.readyState !== WebSocket.OPEN) return false;

    // Check if it's my turn
    const currentTurn = game.turn();
    if (mySide !== currentTurn) return false;

    // Optimistic local validation
    try {
      const temp = new Chess(game.fen());
      const move = temp.move({ from: sourceSquare, to: targetSquare, promotion: 'q' });
      if (!move) return false;
    } catch {
      return false;
    }

    ws.current.send(JSON.stringify({ type: 'move', from: sourceSquare, to: targetSquare }));
    return true;
  }, [game, phase, mySide]);

  const handleResign = () => {
    if (!ws.current || !user) return;
    ws.current.send(JSON.stringify({ type: 'resign' }));
  };

  const copyRoomCode = () => {
    navigator.clipboard.writeText(roomCode || '');
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  // ── Blocked Screen ──
  if (phase === 'blocked') {
    return (
      <div className="min-h-screen gradient-bg flex flex-col items-center justify-center gap-6 p-4">
        <div className="card max-w-sm w-full text-center">
          <ShieldX size={48} className="text-red-400 mx-auto mb-4" />
          <h2 className="text-xl font-bold text-white mb-2">Access Denied</h2>
          <p className="text-zinc-500 text-sm mb-6">{errorMsg}</p>
          <button onClick={() => navigate('/')} className="btn-primary w-full">
            Back to Home
          </button>
        </div>
      </div>
    );
  }

  // ── Loading Screen ──
  if (phase === 'loading' || phase === 'joining') {
    return (
      <div className="min-h-screen gradient-bg flex items-center justify-center">
        <div className="text-center">
          <span className="inline-block w-8 h-8 border-2 border-emerald-400 border-t-transparent rounded-full animate-spin mb-4" />
          <p className="text-zinc-400">{phase === 'joining' ? 'Joining game…' : 'Loading…'}</p>
        </div>
      </div>
    );
  }

  const moves = game.history();
  const turn = game.turn() === 'w' ? 'White' : 'Black';
  const isMyTurn = mySide === game.turn();

  const resultText = (() => {
    if (phase !== 'finished') return null;
    if (!winnerId) return '½ – ½  Draw';
    if (user && winnerId === user.id) return '🎉  You won!';
    return 'You lost';
  })();

  return (
    <div className="min-h-screen gradient-bg flex flex-col">
      {/* Top bar */}
      <nav className="w-full px-4 sm:px-6 py-3 flex items-center justify-between border-b border-zinc-800/50">
        <button onClick={() => navigate('/')} className="flex items-center gap-2 text-zinc-400 hover:text-white transition-colors text-sm">
          <ArrowLeft size={16} /> Back
        </button>

        <button
          onClick={copyRoomCode}
          className="flex items-center gap-2 bg-zinc-800/80 hover:bg-zinc-700/80 border border-zinc-700 px-4 py-1.5 rounded-full transition-all"
        >
          <span className="text-zinc-500 text-xs">ROOM</span>
          <span className="font-mono font-bold text-white tracking-wider">{roomCode}</span>
          {copied ? <Check size={14} className="text-emerald-400" /> : <Copy size={14} className="text-zinc-500" />}
        </button>

        <div className="flex items-center gap-2 text-xs">
          {isConnected ? (
            <span className="flex items-center gap-1.5 text-emerald-400">
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-400"></span>
              </span>
              Live
            </span>
          ) : (
            <span className="flex items-center gap-1.5 text-red-400">
              <WifiOff size={12} /> Offline
            </span>
          )}
        </div>
      </nav>

      {/* Waiting overlay */}
      {phase === 'waiting' && (
        <div className="bg-amber-500/10 border-b border-amber-500/30 px-4 py-3 text-center">
          <p className="text-amber-400 text-sm font-medium">
            ⏳ Waiting for opponent… Share the room code: <span className="font-mono font-bold">{roomCode}</span>
          </p>
        </div>
      )}

      {/* Game Area */}
      <main className="flex-1 flex flex-col lg:flex-row items-center lg:items-start justify-center gap-6 p-4 sm:p-6 lg:p-8">
        {/* Chessboard */}
        <div className="w-full max-w-[min(600px,85vw)] aspect-square">
          <div className="rounded-2xl overflow-hidden shadow-2xl shadow-black/50 border border-zinc-800">
            <Chessboard
              position={game.fen()}
              onPieceDrop={onDrop}
              boardOrientation={mySide === 'b' ? 'black' : 'white'}
              customDarkSquareStyle={{ backgroundColor: '#779952' }}
              customLightSquareStyle={{ backgroundColor: '#e9edcc' }}
              animationDuration={200}
            />
          </div>
        </div>

        {/* Side Panel */}
        <div className="w-full lg:w-80 flex flex-col gap-4">
          {/* Turn / Status */}
          <div className="card">
            {phase === 'finished' ? (
              <div className="text-center">
                <p className="text-lg font-bold text-white mb-1">{resultText}</p>
                <p className="text-zinc-500 text-sm">{gameOverReason}</p>
                <button
                  onClick={() => navigate('/')}
                  className="btn-primary mt-4 w-full flex items-center justify-center gap-2"
                >
                  <RotateCcw size={16} /> New Game
                </button>
              </div>
            ) : (
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className={`w-4 h-4 rounded-full border-2 ${game.turn() === 'w' ? 'bg-white border-zinc-400' : 'bg-zinc-900 border-zinc-600'}`} />
                  <div>
                    <p className="text-white font-semibold">
                      {isMyTurn ? 'Your turn' : `${turn}'s turn`}
                    </p>
                    <p className="text-zinc-500 text-xs">
                      {phase === 'waiting'
                        ? 'Waiting for opponent…'
                        : game.isCheck()
                        ? '🔴 Check!'
                        : `You play ${mySide === 'w' ? 'White ♔' : 'Black ♚'}`}
                    </p>
                  </div>
                </div>
                <Clock size={18} className="text-zinc-600" />
              </div>
            )}
          </div>

          {/* Move History */}
          <div className="card flex-1 min-h-0 flex flex-col">
            <h3 className="text-sm font-semibold text-zinc-400 uppercase tracking-wider mb-3">Moves</h3>
            <div className="flex-1 overflow-y-auto max-h-[360px] space-y-0.5">
              {moves.length === 0 ? (
                <p className="text-zinc-600 text-sm italic">No moves yet</p>
              ) : (
                Array.from({ length: Math.ceil(moves.length / 2) }, (_, i) => (
                  <div key={i} className="flex items-center gap-1 text-sm py-1 px-2 rounded-lg hover:bg-zinc-800/50">
                    <span className="text-zinc-600 w-8 text-right font-mono text-xs">{i + 1}.</span>
                    <span className="text-white font-medium w-16 text-center">{moves[i * 2]}</span>
                    <span className="text-zinc-400 w-16 text-center">{moves[i * 2 + 1] || ''}</span>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* Resign */}
          {phase === 'playing' && (
            <button onClick={handleResign} className="btn-danger flex items-center justify-center gap-2">
              <Flag size={16} /> Resign
            </button>
          )}
        </div>
      </main>
    </div>
  );
};

export default Game;
