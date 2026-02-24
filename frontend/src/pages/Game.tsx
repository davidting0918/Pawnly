import React, { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import { Chess } from 'chess.js';
import { Chessboard } from 'react-chessboard';
import { useParams, useNavigate } from 'react-router-dom';
import { useSelector } from 'react-redux';
import type { RootState } from '../store/store';
import apiClient from '../api/axios';
import { ArrowLeft, Copy, Check, WifiOff, Flag, RotateCcw, Clock, ShieldX, Timer, Palette } from 'lucide-react';
import { findKingSquare } from '../components/BoardEffects';
import { EffectsLayer } from '../components/ExperimentalEffectsWrapper';
import BoardThemePicker from '../components/BoardThemePicker';
import { getThemeById, getSavedThemeId, saveThemeId, type BoardTheme } from '../themes/boardThemes';

type GamePhase = 'loading' | 'joining' | 'waiting' | 'playing' | 'finished' | 'blocked';

interface MoveEntry {
  move_number: number;
  color: 'w' | 'b';
  san: string;
}

interface PlayerInfo {
  id: number;
  name: string;
}

interface Players {
  white: PlayerInfo | null;
  black: PlayerInfo | null;
}

// ── Helpers ──

const W_ICONS: Record<string, string> = { K: '♔', Q: '♕', R: '♖', B: '♗', N: '♘' };
const B_ICONS: Record<string, string> = { K: '♚', Q: '♛', R: '♜', B: '♝', N: '♞' };
const CAPTURE_ICONS_W: Record<string, string> = { p: '♟', r: '♜', n: '♞', b: '♝', q: '♛' };
const CAPTURE_ICONS_B: Record<string, string> = { P: '♙', R: '♖', N: '♘', B: '♗', Q: '♕' };
const PIECE_ORDER_W = ['q', 'r', 'b', 'n', 'p'];
const PIECE_ORDER_B = ['Q', 'R', 'B', 'N', 'P'];

function formatMove(san: string, color: 'w' | 'b') {
  const icons = color === 'w' ? W_ICONS : B_ICONS;
  if (san.startsWith('O-O')) return { icon: icons.K, text: san };
  const first = san[0];
  if (icons[first]) return { icon: icons[first], text: san.slice(1) };
  return { icon: color === 'w' ? '♙' : '♟', text: san };
}

function getCapturedPieces(fen: string) {
  const starting: Record<string, number> = {
    P: 8, R: 2, N: 2, B: 2, Q: 1, K: 1,
    p: 8, r: 2, n: 2, b: 2, q: 1, k: 1,
  };
  const board = fen.split(' ')[0];
  const current: Record<string, number> = {};
  for (const ch of board) {
    if (starting[ch] !== undefined) current[ch] = (current[ch] || 0) + 1;
  }
  const byCapturer: { white: string[]; black: string[] } = { white: [], black: [] };
  for (const [piece, count] of Object.entries(starting)) {
    const diff = count - (current[piece] || 0);
    for (let i = 0; i < diff; i++) {
      if (piece === piece.toLowerCase()) byCapturer.white.push(piece);
      else byCapturer.black.push(piece);
    }
  }
  byCapturer.white.sort((a, b) => PIECE_ORDER_W.indexOf(a) - PIECE_ORDER_W.indexOf(b));
  byCapturer.black.sort((a, b) => PIECE_ORDER_B.indexOf(a) - PIECE_ORDER_B.indexOf(b));
  return byCapturer;
}

function formatClock(seconds: number) {
  if (seconds <= 0) return '0:00';
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${s.toString().padStart(2, '0')}`;
}

// ── Components ──

function PlayerBar({
  name,
  isActive,
  capturedPieces,
  captureIcons,
  timeLeft,
  hasTimer,
}: {
  name: string;
  isActive: boolean;
  capturedPieces: string[];
  captureIcons: Record<string, string>;
  timeLeft: number | null;
  hasTimer: boolean;
}) {
  const urgency = hasTimer && timeLeft !== null
    ? timeLeft <= 10 ? 'text-red-400' : timeLeft <= 30 ? 'text-amber-400' : 'text-emerald-400'
    : 'text-zinc-500';

  return (
    <div className={`flex items-center justify-between px-4 py-2.5 rounded-xl transition-all ${
      isActive ? 'bg-zinc-800/80 border border-emerald-500/30' : 'bg-zinc-900/60 border border-zinc-800/50'
    }`}>
      <div className="flex items-center gap-3 min-w-0">
        <div className={`w-2.5 h-2.5 rounded-full flex-shrink-0 ${
          isActive ? 'bg-emerald-400 animate-pulse' : 'bg-zinc-600'
        }`} />
        <span className={`font-semibold truncate ${isActive ? 'text-white' : 'text-zinc-400'}`}>
          {name}
        </span>
        {capturedPieces.length > 0 && (
          <span className="text-base tracking-tight opacity-80 flex-shrink-0">
            {capturedPieces.map((p, i) => (
              <span key={i} className="inline-block -mr-0.5">{captureIcons[p] || p}</span>
            ))}
          </span>
        )}
      </div>
      {hasTimer && timeLeft !== null && (
        <span className={`font-mono font-bold text-lg tabular-nums flex-shrink-0 ml-3 ${urgency} ${
          isActive && timeLeft <= 10 ? 'animate-pulse' : ''
        }`}>
          {formatClock(timeLeft)}
        </span>
      )}
    </div>
  );
}

// ── Main Component ──

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
  const [moveHistory, setMoveHistory] = useState<MoveEntry[]>([]);
  const [players, setPlayers] = useState<Players>({ white: null, black: null });
  const [timePerMove, setTimePerMove] = useState<number | null>(null);
  const [turnStartedAt, setTurnStartedAt] = useState<string | null>(null);
  const [clockTick, setClockTick] = useState(0);
  const [eloChange, setEloChange] = useState<number | null>(null);
  const [isBotGame, setIsBotGame] = useState(false);
  const [_botDifficulty, setBotDifficulty] = useState<string | null>(null);

  const [lastMoveSquares, setLastMoveSquares] = useState<{ from: string; to: string; san: string } | null>(null);
  const [captureSquare, setCaptureSquare] = useState<string | null>(null);
  const [showCheckmate, setShowCheckmate] = useState(false);
  const [boardSize, setBoardSize] = useState(0);
  const boardContainerRef = useRef<HTMLDivElement>(null);

  // Board theme
  const [boardTheme, setBoardTheme] = useState<BoardTheme>(() => getThemeById(getSavedThemeId()));
  const [showThemePicker, setShowThemePicker] = useState(false);
  const handleThemeSelect = (theme: BoardTheme) => {
    setBoardTheme(theme);
    saveThemeId(theme.id);
    setShowThemePicker(false);
  };

  const ws = useRef<WebSocket | null>(null);
  const phaseRef = useRef<GamePhase>('loading');
  const mySideRef = useRef<'w' | 'b' | null>(null);
  const movesEndRef = useRef<HTMLDivElement | null>(null);

  const updatePhase = (p: GamePhase) => { phaseRef.current = p; setPhase(p); };
  const updateMySide = (s: 'w' | 'b') => { mySideRef.current = s; setMySide(s); };

  // Clock tick — drives countdown re-render
  useEffect(() => {
    if (!timePerMove || phase !== 'playing' || !turnStartedAt) return;
    const id = setInterval(() => setClockTick((t) => t + 1), 250);
    return () => clearInterval(id);
  }, [timePerMove, phase, turnStartedAt]);

  // Auto-scroll move list
  useEffect(() => {
    movesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [moveHistory.length]);

  // Compute time left for current turn
  const getTimeLeft = useCallback(() => {
    if (!timePerMove || !turnStartedAt) return null;
    const elapsed = (Date.now() - new Date(turnStartedAt).getTime()) / 1000;
    return Math.max(0, timePerMove - elapsed);
  }, [timePerMove, turnStartedAt, clockTick]); // eslint-disable-line react-hooks/exhaustive-deps

  // Auto-send timeout
  useEffect(() => {
    if (phase !== 'playing' || !timePerMove || !turnStartedAt) return;
    const left = getTimeLeft();
    if (left !== null && left <= 0 && ws.current?.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify({ type: 'timeout' }));
    }
  }, [clockTick]); // eslint-disable-line react-hooks/exhaustive-deps

  // Track board container size for effects overlay
  useEffect(() => {
    const el = boardContainerRef.current;
    if (!el) return;
    const obs = new ResizeObserver((entries) => {
      for (const e of entries) setBoardSize(e.contentRect.width);
    });
    obs.observe(el);
    setBoardSize(el.clientWidth);
    return () => obs.disconnect();
  }, [phase]);

  // Square highlight styles (last move + check) — only for non-effects themes
  const checkSquare = useMemo(() => {
    if (!game.isCheck()) return null;
    return findKingSquare(game.fen(), game.turn());
  }, [game]);

  // Simple highlights for normal (non-FX) boards
  const squareHighlights = useMemo<Record<string, React.CSSProperties>>(() => {
    if (boardTheme.effects) return {}; // FX themes use overlay effects instead
    const s: Record<string, React.CSSProperties> = {};
    if (lastMoveSquares) {
      s[lastMoveSquares.from] = { backgroundColor: 'rgba(250, 204, 21, 0.25)' };
      s[lastMoveSquares.to] = { boxShadow: 'inset 0 0 10px rgba(52, 211, 153, 0.5)' };
    }
    if (game.isCheck() && checkSquare) {
      s[checkSquare] = {
        ...(s[checkSquare] || {}),
        backgroundColor: 'rgba(239, 68, 68, 0.35)',
        boxShadow: 'inset 0 0 16px rgba(239, 68, 68, 0.5)',
      };
    }
    return s;
  }, [lastMoveSquares, game, checkSquare, boardTheme.effects]);

  // ── WebSocket setup ──
  useEffect(() => {
    if (!user || !roomCode) return;
    let cancelled = false;

    const connectWs = () => {
      if (cancelled) return;
      const wsUrl = import.meta.env.VITE_WS_URL || 'ws://localhost:8000';
      const socket = new WebSocket(`${wsUrl}/api/ws/game/${roomCode}`);

      socket.onopen = () => {
        if (cancelled) { socket.close(); return; }
        socket.send(JSON.stringify({ type: 'auth', user_id: user.id }));
        setIsConnected(true);
      };

      socket.onmessage = (event) => {
        if (cancelled) return;
        const data = JSON.parse(event.data);

        if (data.type === 'init') {
          setGame(new Chess(data.fen));
          updateMySide(data.your_side);
          if (data.players) setPlayers(data.players);
          if (data.moves) setMoveHistory(data.moves);
          if (data.time_per_move != null) setTimePerMove(data.time_per_move);
          if (data.turn_started_at) setTurnStartedAt(data.turn_started_at);
          if (data.is_bot_game) { setIsBotGame(true); setBotDifficulty(data.bot_difficulty); }
          updatePhase(data.status === 'active' ? 'playing' : 'waiting');
        } else if (data.type === 'game_start') {
          setGame(new Chess(data.fen));
          if (data.players) setPlayers(data.players);
          if (data.time_per_move != null) setTimePerMove(data.time_per_move);
          if (data.turn_started_at) setTurnStartedAt(data.turn_started_at);
          updatePhase('playing');
        } else if (data.type === 'update') {
          setGame(new Chess(data.fen));
          if (data.last_move) {
            // Track last move for highlighting
            setLastMoveSquares({ from: data.last_move.from, to: data.last_move.to, san: data.last_move.san });
            // Detect capture → trigger explosion
            if (data.last_move.san && data.last_move.san.includes('x')) {
              setCaptureSquare(data.last_move.to);
            }
            setMoveHistory((prev) => {
              const dup = prev.some(
                (m) => m.move_number === data.last_move.move_number && m.color === data.last_move.color
              );
              if (dup) return prev;
              return [...prev, {
                move_number: data.last_move.move_number,
                color: data.last_move.color,
                san: data.last_move.san,
              }];
            });
          }
          if (data.turn_started_at) setTurnStartedAt(data.turn_started_at);
          if (phaseRef.current === 'waiting') updatePhase('playing');
          if (data.game_over) {
            updatePhase('finished');
            setWinnerId(data.winner_id ?? null);
            setTurnStartedAt(null);
            if (data.checkmate) {
              setGameOverReason('Checkmate');
              setShowCheckmate(true);
            } else if (data.stalemate) setGameOverReason('Stalemate');
            else setGameOverReason('Draw');
            if (data.bot_elo_change != null) {
              setEloChange(data.bot_elo_change);
            } else if (data.elo_change_white != null && data.elo_change_black != null) {
              setEloChange(mySideRef.current === 'w' ? data.elo_change_white : data.elo_change_black);
            }
          }
        } else if (data.type === 'game_over') {
          updatePhase('finished');
          setWinnerId(data.winner_id ?? null);
          setTurnStartedAt(null);
          const reasons: Record<string, string> = { resign: 'Resignation', timeout: 'Time ran out' };
          setGameOverReason(reasons[data.reason] || 'Game Over');
          if (data.fen) setGame(new Chess(data.fen));
          if (data.bot_elo_change != null) {
            setEloChange(data.bot_elo_change);
          } else if (data.elo_change_white != null && data.elo_change_black != null) {
            setEloChange(mySideRef.current === 'w' ? data.elo_change_white : data.elo_change_black);
          }
        } else if (data.type === 'error') {
          console.error('Server:', data.message);
          if (data.message.includes('not a player')) {
            updatePhase('blocked');
            setErrorMsg(data.message);
          }
        }
      };

      socket.onclose = () => { if (!cancelled) setIsConnected(false); };
      ws.current = socket;
    };

    const initGame = async () => {
      try {
        const res = await apiClient.get(`/api/games/${roomCode}`);
        if (cancelled) return;
        const gameData = res.data;
        const isWhite = gameData.white_player_id === user.id;
        const isBlack = gameData.black_player_id === user.id;

        if (isWhite || isBlack) {
          updateMySide(isWhite ? 'w' : 'b');
          updatePhase(gameData.status === 'waiting' ? 'waiting' : 'playing');
          connectWs();
        } else if (gameData.status === 'waiting') {
          updatePhase('joining');
          try {
            const joinRes = await apiClient.post(`/api/games/${roomCode}/join`);
            if (cancelled) return;
            updateMySide(joinRes.data.side === 'white' ? 'w' : 'b');
            updatePhase('playing');
            connectWs();
          } catch (joinErr: any) {
            if (cancelled) return;
            setErrorMsg(joinErr.response?.data?.detail || 'Failed to join game');
            updatePhase('blocked');
          }
        } else {
          updatePhase('blocked');
          setErrorMsg('You are not a player in this game');
        }
      } catch (err: any) {
        if (cancelled) return;
        if (err.response?.status === 403) {
          updatePhase('blocked'); setErrorMsg('You are not a player in this game');
        } else if (err.response?.status === 404) {
          updatePhase('blocked'); setErrorMsg('Game not found');
        } else {
          updatePhase('blocked'); setErrorMsg('Failed to load game');
        }
      }
    };

    initGame();
    return () => {
      cancelled = true;
      if (ws.current) { ws.current.close(); ws.current = null; }
    };
  }, [roomCode, user]);

  const onDrop = useCallback(({ sourceSquare, targetSquare }: { sourceSquare: string; targetSquare: string | null }) => {
    if (!targetSquare) return false;
    if (phaseRef.current !== 'playing') return false;
    if (!ws.current || ws.current.readyState !== WebSocket.OPEN) return false;
    if (mySideRef.current !== game.turn()) return false;

    try {
      const temp = new Chess(game.fen());
      const move = temp.move({ from: sourceSquare, to: targetSquare, promotion: 'q' });
      if (!move) return false;
    } catch { return false; }

    ws.current.send(JSON.stringify({ type: 'move', from: sourceSquare, to: targetSquare }));
    return true;
  }, [game]);

  const handleResign = () => {
    if (!ws.current || !user) return;
    ws.current.send(JSON.stringify({ type: 'resign' }));
  };

  const copyRoomCode = () => {
    navigator.clipboard.writeText(roomCode || '');
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  // ── Derived state ──

  const isMyTurn = mySide === game.turn();
  const boardOrientation = mySide === 'b' ? 'black' : 'white';
  const captured = useMemo(() => getCapturedPieces(game.fen()), [game]);
  const timeLeft = getTimeLeft();

  const whiteTimeLeft = game.turn() === 'w' ? timeLeft : null;
  const blackTimeLeft = game.turn() === 'b' ? timeLeft : null;

  const topPlayer = boardOrientation === 'white' ? 'black' : 'white';
  const bottomPlayer = boardOrientation === 'white' ? 'white' : 'black';

  const topName = (topPlayer === 'white' ? players.white?.name : players.black?.name) || (topPlayer === 'white' ? 'White' : 'Black');
  const bottomName = (bottomPlayer === 'white' ? players.white?.name : players.black?.name) || (bottomPlayer === 'white' ? 'White' : 'Black');

  const topCaptured = topPlayer === 'white' ? captured.white : captured.black;
  const bottomCaptured = bottomPlayer === 'white' ? captured.white : captured.black;
  const topCaptureIcons = topPlayer === 'white' ? CAPTURE_ICONS_W : CAPTURE_ICONS_B;
  const bottomCaptureIcons = bottomPlayer === 'white' ? CAPTURE_ICONS_W : CAPTURE_ICONS_B;

  const topTimeLeft = topPlayer === 'white' ? whiteTimeLeft : blackTimeLeft;
  const bottomTimeLeft = bottomPlayer === 'white' ? whiteTimeLeft : blackTimeLeft;
  const topActive = (topPlayer === 'white' && game.turn() === 'w') || (topPlayer === 'black' && game.turn() === 'b');
  const bottomActive = !topActive;

  const movePairs = useMemo(() => {
    const pairs: { num: number; white?: MoveEntry; black?: MoveEntry }[] = [];
    for (const m of moveHistory) {
      if (m.color === 'w') {
        pairs.push({ num: m.move_number, white: m });
      } else {
        const last = pairs[pairs.length - 1];
        if (last && last.num === m.move_number && !last.black) {
          last.black = m;
        } else {
          pairs.push({ num: m.move_number, black: m });
        }
      }
    }
    return pairs;
  }, [moveHistory]);

  const resultText = (() => {
    if (phase !== 'finished') return null;
    if (user && winnerId === user.id) return 'You won!';
    if (isBotGame) {
      // In bot games: winner_id = user.id means human won, null = bot won or draw
      if (!winnerId && game.isCheckmate()) return 'You lost';
      if (!winnerId && game.isStalemate()) return '½ – ½  Draw';
      if (!winnerId) return 'You lost';
    }
    if (!winnerId) return '½ – ½  Draw';
    return 'You lost';
  })();

  // ── Screens ──

  if (phase === 'blocked') {
    return (
      <div className="min-h-screen gradient-bg flex flex-col items-center justify-center gap-6 p-4">
        <div className="card max-w-sm w-full text-center">
          <ShieldX size={48} className="text-red-400 mx-auto mb-4" />
          <h2 className="text-xl font-bold text-white mb-2">Access Denied</h2>
          <p className="text-zinc-500 text-sm mb-6">{errorMsg}</p>
          <button onClick={() => navigate('/')} className="btn-primary w-full">Back to Home</button>
        </div>
      </div>
    );
  }

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

  return (
    <div className="min-h-screen gradient-bg flex flex-col">
      {/* Top bar */}
      <nav className="w-full px-4 sm:px-6 py-3 flex items-center justify-between border-b border-zinc-800/50">
        <button onClick={() => navigate('/')} className="flex items-center gap-2 text-zinc-400 hover:text-white transition-colors text-sm">
          <ArrowLeft size={16} /> Back
        </button>
        <button onClick={copyRoomCode} className="flex items-center gap-2 bg-zinc-800/80 hover:bg-zinc-700/80 border border-zinc-700 px-4 py-1.5 rounded-full transition-all">
          <span className="text-zinc-500 text-xs">ROOM</span>
          <span className="font-mono font-bold text-white tracking-wider">{roomCode}</span>
          {copied ? <Check size={14} className="text-emerald-400" /> : <Copy size={14} className="text-zinc-500" />}
        </button>
        <div className="flex items-center gap-3 text-xs">
          <button
            onClick={() => setShowThemePicker(!showThemePicker)}
            className="flex items-center gap-1 text-zinc-500 hover:text-emerald-400 transition-colors"
            title="Board Theme"
          >
            <Palette size={14} />
          </button>
          <span className="text-zinc-500 font-medium">{mySide === 'w' ? '♔ White' : '♚ Black'}</span>
          {isConnected ? (
            <span className="flex items-center gap-1.5 text-emerald-400">
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
                <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-400" />
              </span>
              Live
            </span>
          ) : (
            <span className="flex items-center gap-1.5 text-red-400"><WifiOff size={12} /> Offline</span>
          )}
        </div>
      </nav>

      {phase === 'waiting' && (
        <div className="bg-amber-500/10 border-b border-amber-500/30 px-4 py-3 text-center">
          <p className="text-amber-400 text-sm font-medium">
            Waiting for opponent… Share the room code: <span className="font-mono font-bold">{roomCode}</span>
          </p>
        </div>
      )}

      {/* Game Area */}
      <main className="flex-1 flex flex-col lg:flex-row items-center lg:items-start justify-center gap-6 p-4 sm:p-6 lg:p-8">
        {/* Board Column */}
        <div className="w-full max-w-[min(600px,85vw)] flex flex-col gap-2">
          <PlayerBar
            name={topName}
            isActive={topActive && phase === 'playing'}
            capturedPieces={topCaptured}
            captureIcons={topCaptureIcons}
            timeLeft={topTimeLeft}
            hasTimer={!!timePerMove}
          />
          <div
            ref={boardContainerRef}
            className={`relative rounded-2xl overflow-hidden shadow-2xl shadow-black/50 border ${boardTheme.boardBorder || 'border-zinc-800'} ${
              boardTheme.effects ? 'ring-1 ring-inset ring-white/5' : ''
            }`}
          >
            <Chessboard
              options={{
                position: game.fen(),
                onPieceDrop: onDrop,
                boardOrientation,
                darkSquareStyle: boardTheme.darkSquare,
                lightSquareStyle: boardTheme.lightSquare,
                animationDurationInMs: 200,
                allowDragging: phase === 'playing' && isMyTurn,
                squareStyles: squareHighlights,
              }}
            />
            {/* Experimental effects — lazy-loaded only when using FX themes */}
            {boardTheme.effects && boardSize > 0 && (
              <EffectsLayer
                theme={boardTheme}
                boardSize={boardSize}
                orientation={boardOrientation}
                captureSquare={captureSquare}
                onCaptureDone={() => setCaptureSquare(null)}
                lastMove={lastMoveSquares ? { from: lastMoveSquares.from, to: lastMoveSquares.to } : null}
                isCheck={game.isCheck()}
                checkSquare={checkSquare}
                showCheckmate={showCheckmate}
                isWinner={!!winnerId && !!user && winnerId === user.id}
              />
            )}
          </div>
          <PlayerBar
            name={bottomName}
            isActive={bottomActive && phase === 'playing'}
            capturedPieces={bottomCaptured}
            captureIcons={bottomCaptureIcons}
            timeLeft={bottomTimeLeft}
            hasTimer={!!timePerMove}
          />
        </div>

        {/* Side Panel */}
        <div className="w-full lg:w-80 flex flex-col gap-4">
          {/* Status / Result */}
          <div className="card">
            {phase === 'finished' ? (
              <div className="text-center">
                <p className="text-lg font-bold text-white mb-1">
                  {resultText}
                  {eloChange !== null && (
                    <span
                      className={`ml-2 inline-block animate-[fadeScale_0.4s_ease-out] ${
                        eloChange > 0 ? 'text-emerald-400' : eloChange < 0 ? 'text-red-400' : 'text-zinc-400'
                      }`}
                    >
                      {eloChange > 0 ? '+' : ''}{eloChange} {isBotGame ? 'Bot Elo' : 'Elo'}
                    </span>
                  )}
                </p>
                <p className="text-zinc-500 text-sm">{gameOverReason}</p>
                <button onClick={() => navigate('/')} className="btn-primary mt-4 w-full flex items-center justify-center gap-2">
                  <RotateCcw size={16} /> New Game
                </button>
              </div>
            ) : (
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className={`w-4 h-4 rounded-full border-2 ${
                    isMyTurn ? 'bg-emerald-400 border-emerald-500 animate-pulse'
                      : game.turn() === 'w' ? 'bg-white border-zinc-400' : 'bg-zinc-900 border-zinc-600'
                  }`} />
                  <div>
                    <p className="text-white font-semibold">
                      {phase === 'waiting' ? 'Waiting for opponent' : isMyTurn ? 'Your turn!' : `${game.turn() === 'w' ? 'White' : 'Black'}'s turn`}
                    </p>
                    <p className="text-zinc-500 text-xs">
                      {phase === 'waiting' ? 'Share the room code'
                        : game.isCheck() ? 'Check!'
                        : `You play ${mySide === 'w' ? 'White ♔' : 'Black ♚'}`}
                    </p>
                  </div>
                </div>
                {timePerMove && phase === 'playing' ? (
                  <div className="flex items-center gap-1.5">
                    <Timer size={14} className="text-zinc-500" />
                    <span className="text-zinc-500 text-xs font-mono">{timePerMove}s/move</span>
                  </div>
                ) : (
                  <Clock size={18} className="text-zinc-600" />
                )}
              </div>
            )}
          </div>

          {/* Countdown Clock Card */}
          {timePerMove && phase === 'playing' && timeLeft !== null && (
            <div className={`card text-center ${timeLeft <= 10 ? 'border-red-500/50' : timeLeft <= 30 ? 'border-amber-500/30' : ''}`}>
              <p className="text-zinc-500 text-xs uppercase tracking-wider mb-1">
                {isMyTurn ? 'Your time' : "Opponent's time"}
              </p>
              <p className={`text-4xl font-mono font-bold tabular-nums ${
                timeLeft <= 10 ? 'text-red-400 animate-pulse' : timeLeft <= 30 ? 'text-amber-400' : 'text-white'
              }`}>
                {formatClock(timeLeft)}
              </p>
            </div>
          )}

          {/* Move History */}
          <div className="card flex-1 min-h-0 flex flex-col">
            <h3 className="text-sm font-semibold text-zinc-400 uppercase tracking-wider mb-3">Moves</h3>
            <div className="flex-1 overflow-y-auto max-h-[360px] space-y-0.5">
              {movePairs.length === 0 ? (
                <p className="text-zinc-600 text-sm italic">No moves yet</p>
              ) : (
                movePairs.map((pair, i) => {
                  const wm = pair.white ? formatMove(pair.white.san, 'w') : null;
                  const bm = pair.black ? formatMove(pair.black.san, 'b') : null;
                  return (
                    <div key={i} className="flex items-center gap-1 text-sm py-1.5 px-2 rounded-lg hover:bg-zinc-800/50">
                      <span className="text-zinc-600 w-7 text-right font-mono text-xs">{pair.num}.</span>
                      <span className="text-white font-medium w-20 text-center">
                        {wm && <><span className="opacity-60 mr-0.5">{wm.icon}</span>{wm.text}</>}
                      </span>
                      <span className="text-zinc-400 w-20 text-center">
                        {bm && <><span className="opacity-60 mr-0.5">{bm.icon}</span>{bm.text}</>}
                      </span>
                    </div>
                  );
                })
              )}
              <div ref={movesEndRef} />
            </div>
          </div>

          {/* Board Theme Picker */}
          {showThemePicker && (
            <BoardThemePicker
              currentThemeId={boardTheme.id}
              onSelect={handleThemeSelect}
              onClose={() => setShowThemePicker(false)}
            />
          )}

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
