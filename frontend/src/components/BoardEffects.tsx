import React, { useEffect, useState, useMemo } from 'react';

// ── Helpers ──

function getSquarePixelPosition(
  square: string,
  boardSize: number,
  orientation: 'white' | 'black',
): { x: number; y: number } {
  const col = square.charCodeAt(0) - 97; // a=0 .. h=7
  const row = parseInt(square[1]) - 1;   // 1=0 .. 8=7
  const sqSize = boardSize / 8;

  if (orientation === 'white') {
    return { x: col * sqSize, y: (7 - row) * sqSize };
  }
  return { x: (7 - col) * sqSize, y: row * sqSize };
}

// ── CaptureEffect ──

interface CaptureEffectProps {
  square: string;
  boardSize: number;
  orientation: 'white' | 'black';
  onDone: () => void;
}

export const CaptureEffect: React.FC<CaptureEffectProps> = ({
  square,
  boardSize,
  orientation,
  onDone,
}) => {
  const sqSize = boardSize / 8;
  const pos = getSquarePixelPosition(square, boardSize, orientation);
  const cx = pos.x + sqSize / 2;
  const cy = pos.y + sqSize / 2;

  // Auto-remove after animation
  useEffect(() => {
    const t = setTimeout(onDone, 700);
    return () => clearTimeout(t);
  }, [onDone]);

  // Generate particles
  const particles = useMemo(() => {
    const count = 10;
    const result: {
      id: number;
      dx: number;
      dy: number;
      size: number;
      color: string;
      delay: number;
    }[] = [];

    for (let i = 0; i < count; i++) {
      const angle = (Math.PI * 2 * i) / count + (Math.random() - 0.5) * 0.4;
      const dist = sqSize * 0.5 + Math.random() * sqSize * 0.4;
      const colors = [
        '#ff6b35', '#ff4500', '#ff8c00', '#ffd700', '#fff',
        '#ff5252', '#ffab40', '#ffc107', '#ffffff', '#ff7043',
      ];
      result.push({
        id: i,
        dx: Math.cos(angle) * dist,
        dy: Math.sin(angle) * dist,
        size: 3 + Math.random() * 5,
        color: colors[i % colors.length],
        delay: Math.random() * 80,
      });
    }
    return result;
  }, [sqSize]);

  return (
    <>
      {/* Central flash */}
      <div
        className="capture-flash-core"
        style={{
          left: cx - sqSize * 0.35,
          top: cy - sqSize * 0.35,
          width: sqSize * 0.7,
          height: sqSize * 0.7,
        }}
      />
      {/* Particles */}
      {particles.map((p) => (
        <div
          key={p.id}
          className="capture-particle"
          style={{
            left: cx - p.size / 2,
            top: cy - p.size / 2,
            width: p.size,
            height: p.size,
            backgroundColor: p.color,
            '--dx': `${p.dx}px`,
            '--dy': `${p.dy}px`,
            animationDelay: `${p.delay}ms`,
          } as React.CSSProperties}
        />
      ))}
    </>
  );
};

// ── CheckmateOverlay ──

interface CheckmateOverlayProps {
  boardSize: number;
  isWinner: boolean;
}

export const CheckmateOverlay: React.FC<CheckmateOverlayProps> = ({
  boardSize,
  isWinner,
}) => {
  const [visible, setVisible] = useState(true);

  useEffect(() => {
    const t = setTimeout(() => setVisible(false), 2600);
    return () => clearTimeout(t);
  }, []);

  // Confetti pieces
  const confetti = useMemo(() => {
    if (!isWinner) return [];
    const pieces: {
      id: number;
      cx: number;
      cxEnd: number;
      cyEnd: number;
      cr: number;
      color: string;
      w: number;
      h: number;
      delay: number;
    }[] = [];
    const colors = ['#ffd700', '#ff6b35', '#34d399', '#60a5fa', '#f472b6', '#a78bfa', '#fb923c'];
    for (let i = 0; i < 30; i++) {
      pieces.push({
        id: i,
        cx: Math.random() * boardSize,
        cxEnd: (Math.random() - 0.5) * boardSize * 0.6,
        cyEnd: boardSize * 0.5 + Math.random() * boardSize * 0.5,
        cr: Math.random() * 720 - 360,
        color: colors[i % colors.length],
        w: 4 + Math.random() * 8,
        h: 4 + Math.random() * 8,
        delay: Math.random() * 400,
      });
    }
    return pieces;
  }, [boardSize, isWinner]);

  if (!visible) return null;

  return (
    <>
      {/* Dark overlay */}
      <div
        className="checkmate-overlay"
        style={{
          position: 'absolute',
          inset: 0,
          backgroundColor: 'rgba(0, 0, 0, 0.6)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 20,
          borderRadius: '1rem',
          pointerEvents: 'none',
        }}
      >
        <span
          className="checkmate-text"
          style={{
            fontSize: Math.max(boardSize * 0.08, 20),
            fontWeight: 800,
            color: isWinner ? '#ffd700' : '#ef4444',
            textShadow: '0 2px 20px rgba(0,0,0,0.8)',
            letterSpacing: '0.05em',
          }}
        >
          {isWinner ? '🏆 Checkmate!' : '💀 Checkmate'}
        </span>
      </div>
      {/* Confetti */}
      {confetti.map((c) => (
        <div
          key={c.id}
          className="confetti-piece"
          style={{
            left: 0,
            top: 0,
            width: c.w,
            height: c.h,
            backgroundColor: c.color,
            borderRadius: Math.random() > 0.5 ? '50%' : '2px',
            '--cx': `${c.cx}px`,
            '--cx-end': `${c.cxEnd}px`,
            '--cy-end': `${c.cyEnd}px`,
            '--cr': `${c.cr}deg`,
            animationDelay: `${c.delay}ms`,
            zIndex: 21,
          } as React.CSSProperties}
        />
      ))}
    </>
  );
};

// ── useSquareHighlights hook ──

interface LastMove {
  from: string;
  to: string;
  san: string;
}

interface UseSquareHighlightsOptions {
  lastMove: LastMove | null;
  isCheck: boolean;
  checkSquare: string | null;
}

export function useSquareHighlights({
  lastMove,
  isCheck,
  checkSquare,
}: UseSquareHighlightsOptions): Record<string, React.CSSProperties> {
  const [styles, setStyles] = useState<Record<string, React.CSSProperties>>({});

  useEffect(() => {
    const s: Record<string, React.CSSProperties> = {};

    // Move highlighting
    if (lastMove) {
      s[lastMove.from] = {
        backgroundColor: 'rgba(250, 204, 21, 0.25)',
        transition: 'background-color 1s ease-out',
      };
      s[lastMove.to] = {
        boxShadow: 'inset 0 0 10px rgba(52, 211, 153, 0.5)',
        transition: 'box-shadow 0.5s ease-out',
      };
    }

    // Check highlighting
    if (isCheck && checkSquare) {
      s[checkSquare] = {
        ...(s[checkSquare] || {}),
        animation: 'check-pulse 500ms ease-in-out 3',
        backgroundColor: 'rgba(239, 68, 68, 0.35)',
        boxShadow: 'inset 0 0 16px rgba(239, 68, 68, 0.5)',
      };
    }

    setStyles(s);
  }, [lastMove, isCheck, checkSquare]);

  return styles;
}

// ── Helper: find king square in check ──

export function findKingSquare(fen: string, turn: 'w' | 'b'): string | null {
  const board = fen.split(' ')[0];
  const kingChar = turn === 'w' ? 'K' : 'k';
  const rows = board.split('/');

  for (let rank = 0; rank < 8; rank++) {
    let file = 0;
    for (const ch of rows[rank]) {
      if (ch >= '1' && ch <= '8') {
        file += parseInt(ch);
      } else {
        if (ch === kingChar) {
          const col = String.fromCharCode(97 + file);
          const rowNum = 8 - rank;
          return `${col}${rowNum}`;
        }
        file++;
      }
    }
  }
  return null;
}
