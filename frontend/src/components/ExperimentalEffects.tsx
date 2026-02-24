import React, { useEffect, useState } from 'react';
import Particles, { initParticlesEngine } from '@tsparticles/react';
import { loadSlim } from '@tsparticles/slim';
import { motion } from 'framer-motion';
import type { BoardTheme } from '../themes/boardThemes';

// ── Initialize tsParticles engine once ──
let engineReady = false;
let enginePromise: Promise<void> | null = null;

function ensureEngine(): Promise<void> {
  if (engineReady) return Promise.resolve();
  if (!enginePromise) {
    enginePromise = initParticlesEngine(async (engine) => {
      await loadSlim(engine);
    }).then(() => {
      engineReady = true;
    });
  }
  return enginePromise;
}

// ── Square position calculation ──
function getSquareCenter(
  square: string,
  boardSize: number,
  orientation: 'white' | 'black',
): { x: number; y: number } {
  const col = square.charCodeAt(0) - 97;
  const row = parseInt(square[1]) - 1;
  const sq = boardSize / 8;
  if (orientation === 'white') {
    return { x: col * sq + sq / 2, y: (7 - row) * sq + sq / 2 };
  }
  return { x: (7 - col) * sq + sq / 2, y: row * sq + sq / 2 };
}

// ── Capture Explosion (tsParticles emitter) ──
interface CaptureExplosionProps {
  square: string;
  boardSize: number;
  orientation: 'white' | 'black';
  theme: BoardTheme;
  onDone: () => void;
}

export const CaptureExplosion: React.FC<CaptureExplosionProps> = ({
  square,
  boardSize,
  orientation,
  theme,
  onDone,
}) => {
  const [ready, setReady] = useState(engineReady);
  const pos = getSquareCenter(square, boardSize, orientation);

  useEffect(() => {
    if (!ready) ensureEngine().then(() => setReady(true));
  }, [ready]);

  useEffect(() => {
    const t = setTimeout(onDone, 900);
    return () => clearTimeout(t);
  }, [onDone]);

  const isNeon = theme.id === 'neon';
  const colors = isNeon
    ? ['#00ffff', '#22d3ee', '#06b6d4', '#67e8f9', '#ffffff']
    : ['#e879f9', '#d946ef', '#a855f7', '#c084fc', '#ffffff'];

  if (!ready || boardSize === 0) return null;

  return (
    <div
      style={{
        position: 'absolute',
        left: pos.x - boardSize * 0.12,
        top: pos.y - boardSize * 0.12,
        width: boardSize * 0.24,
        height: boardSize * 0.24,
        pointerEvents: 'none',
        zIndex: 15,
      }}
    >
      <Particles
        id={`capture-${square}-${Date.now()}`}
        options={{
          fullScreen: false,
          fpsLimit: 60,
          particles: {
            number: { value: 0 },
            color: { value: colors },
            shape: { type: 'circle' },
            opacity: {
              value: { min: 0.4, max: 1 },
              animation: { enable: true, speed: 2, startValue: 'max', destroy: 'min' },
            },
            size: {
              value: { min: 1, max: 4 },
              animation: { enable: true, speed: 3, startValue: 'max', destroy: 'min' },
            },
            move: {
              enable: true,
              speed: { min: 4, max: 12 },
              direction: 'outside',
              outModes: 'destroy',
            },
            life: {
              duration: { value: 0.6 },
              count: 1,
            },
          },
          emitters: {
            position: { x: 50, y: 50 },
            rate: { quantity: 20, delay: 0 },
            life: { count: 1, duration: 0.1 },
            size: { width: 10, height: 10 },
          },
        }}
      />
    </div>
  );
};

// ── Move Trail (Framer Motion) ──
interface MoveTrailProps {
  fromSquare: string;
  toSquare: string;
  boardSize: number;
  orientation: 'white' | 'black';
  theme: BoardTheme;
}

export const MoveTrail: React.FC<MoveTrailProps> = ({
  fromSquare,
  toSquare,
  boardSize,
  orientation,
  theme,
}) => {
  const from = getSquareCenter(fromSquare, boardSize, orientation);
  const to = getSquareCenter(toSquare, boardSize, orientation);
  const sq = boardSize / 8;

  const isNeon = theme.id === 'neon';
  const glowColor = isNeon ? 'rgba(34, 211, 238, 0.5)' : 'rgba(217, 70, 239, 0.5)';
  const trailColor = isNeon ? 'rgba(6, 182, 212, 0.3)' : 'rgba(168, 85, 247, 0.3)';

  return (
    <>
      {/* Source square fade */}
      <motion.div
        initial={{ opacity: 0.6, scale: 1 }}
        animate={{ opacity: 0, scale: 1.3 }}
        transition={{ duration: 0.8, ease: 'easeOut' }}
        style={{
          position: 'absolute',
          left: from.x - sq / 2,
          top: from.y - sq / 2,
          width: sq,
          height: sq,
          backgroundColor: trailColor,
          borderRadius: 4,
          pointerEvents: 'none',
          zIndex: 10,
        }}
      />
      {/* Target square glow */}
      <motion.div
        initial={{ opacity: 0.8, boxShadow: `inset 0 0 20px ${glowColor}, 0 0 15px ${glowColor}` }}
        animate={{ opacity: 0, boxShadow: `inset 0 0 0px transparent, 0 0 0px transparent` }}
        transition={{ duration: 1, ease: 'easeOut' }}
        style={{
          position: 'absolute',
          left: to.x - sq / 2,
          top: to.y - sq / 2,
          width: sq,
          height: sq,
          borderRadius: 4,
          pointerEvents: 'none',
          zIndex: 10,
        }}
      />
    </>
  );
};

// ── Check Pulse (Framer Motion) ──
interface CheckPulseProps {
  square: string;
  boardSize: number;
  orientation: 'white' | 'black';
  theme: BoardTheme;
}

export const CheckPulse: React.FC<CheckPulseProps> = ({
  square,
  boardSize,
  orientation,
  theme: _theme,
}) => {
  const pos = getSquareCenter(square, boardSize, orientation);
  const sq = boardSize / 8;

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{
        opacity: [0, 0.7, 0, 0.7, 0, 0.7, 0],
        scale: [1, 1.05, 1, 1.05, 1, 1.05, 1],
      }}
      transition={{ duration: 1.8, ease: 'easeInOut' }}
      style={{
        position: 'absolute',
        left: pos.x - sq / 2,
        top: pos.y - sq / 2,
        width: sq,
        height: sq,
        backgroundColor: 'rgba(239, 68, 68, 0.5)',
        boxShadow: 'inset 0 0 20px rgba(239, 68, 68, 0.6), 0 0 30px rgba(239, 68, 68, 0.3)',
        borderRadius: 4,
        pointerEvents: 'none',
        zIndex: 12,
      }}
    />
  );
};

// ── Checkmate Overlay (Framer Motion) ──
interface CheckmateOverlayFXProps {
  boardSize: number;
  isWinner: boolean;
  theme: BoardTheme;
}

export const CheckmateOverlayFX: React.FC<CheckmateOverlayFXProps> = ({
  boardSize,
  isWinner,
  theme,
}) => {
  const [ready, setReady] = useState(engineReady);
  const [visible, setVisible] = useState(true);

  useEffect(() => {
    if (!ready) ensureEngine().then(() => setReady(true));
  }, [ready]);

  useEffect(() => {
    const t = setTimeout(() => setVisible(false), 3000);
    return () => clearTimeout(t);
  }, []);

  if (!visible) return null;

  const isNeon = theme.id === 'neon';
  const titleColor = isWinner
    ? isNeon ? '#22d3ee' : '#e879f9'
    : '#ef4444';

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.5 }}
      style={{
        position: 'absolute',
        inset: 0,
        backgroundColor: 'rgba(0, 0, 0, 0.7)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 20,
        borderRadius: '1rem',
        pointerEvents: 'none',
      }}
    >
      <motion.div
        initial={{ scale: 0.3, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        transition={{ type: 'spring', stiffness: 200, damping: 15, delay: 0.2 }}
        className="text-center"
      >
        <motion.p
          style={{
            fontSize: Math.max(boardSize * 0.07, 18),
            fontWeight: 800,
            color: titleColor,
            textShadow: `0 0 30px ${titleColor}80, 0 0 60px ${titleColor}40`,
            letterSpacing: '0.05em',
          }}
        >
          {isWinner ? '🏆 CHECKMATE' : '💀 CHECKMATE'}
        </motion.p>
        <motion.p
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.6 }}
          style={{
            fontSize: Math.max(boardSize * 0.035, 12),
            color: isWinner ? '#86efac' : '#fca5a5',
            marginTop: 8,
          }}
        >
          {isWinner ? 'Victory!' : 'Defeated'}
        </motion.p>
      </motion.div>

      {/* Winner confetti particles */}
      {isWinner && ready && (
        <div style={{ position: 'absolute', inset: 0, pointerEvents: 'none', zIndex: 21, borderRadius: '1rem', overflow: 'hidden' }}>
          <Particles
            id={`checkmate-confetti-${Date.now()}`}
            options={{
              fullScreen: false,
              fpsLimit: 60,
              particles: {
                number: { value: 0 },
                color: {
                  value: isNeon
                    ? ['#22d3ee', '#06b6d4', '#67e8f9', '#a5f3fc']
                    : ['#e879f9', '#d946ef', '#fbbf24', '#34d399', '#60a5fa'],
                },
                shape: { type: ['circle', 'square'] },
                opacity: {
                  value: { min: 0.5, max: 1 },
                  animation: { enable: true, speed: 0.5, startValue: 'max', destroy: 'min' },
                },
                size: { value: { min: 2, max: 6 } },
                move: {
                  enable: true,
                  speed: { min: 1, max: 4 },
                  direction: 'bottom',
                  gravity: { enable: true, acceleration: 2 },
                  outModes: 'destroy',
                },
                rotate: {
                  value: { min: 0, max: 360 },
                  animation: { enable: true, speed: 30 },
                },
                life: {
                  duration: { value: 2 },
                  count: 1,
                },
              },
              emitters: {
                position: { x: 50, y: 0 },
                rate: { quantity: 8, delay: 0.1 },
                life: { count: 1, duration: 1 },
                size: { width: 100, height: 0 },
              },
            }}
          />
        </div>
      )}
    </motion.div>
  );
};

// ── Neon grid background for experimental boards ──
export const NeonGridOverlay: React.FC<{ theme: BoardTheme }> = ({ theme }) => {
  const isNeon = theme.id === 'neon';
  const lineColor = isNeon ? 'rgba(34, 211, 238, 0.08)' : 'rgba(217, 70, 239, 0.08)';

  return (
    <div
      style={{
        position: 'absolute',
        inset: 0,
        pointerEvents: 'none',
        zIndex: 5,
        backgroundImage: `
          linear-gradient(${lineColor} 1px, transparent 1px),
          linear-gradient(90deg, ${lineColor} 1px, transparent 1px)
        `,
        backgroundSize: '12.5% 12.5%',
        borderRadius: '1rem',
      }}
    />
  );
};
