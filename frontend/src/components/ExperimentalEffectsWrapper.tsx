/**
 * Lazy-loading wrapper for experimental effects.
 * tsParticles + framer-motion only load when an FX theme is active.
 */
import React, { Suspense } from 'react';
import type { BoardTheme } from '../themes/boardThemes';

interface EffectsLayerProps {
  theme: BoardTheme;
  boardSize: number;
  orientation: 'white' | 'black';
  captureSquare: string | null;
  onCaptureDone: () => void;
  lastMove: { from: string; to: string } | null;
  isCheck: boolean;
  checkSquare: string | null;
  showCheckmate: boolean;
  isWinner: boolean;
}

const EffectsLayerInner = React.lazy(() =>
  import('./ExperimentalEffects').then((mod) => ({
    default: function EffectsLayerImpl(props: EffectsLayerProps) {
      const {
        theme, boardSize, orientation, captureSquare, onCaptureDone,
        lastMove, isCheck, checkSquare, showCheckmate, isWinner,
      } = props;

      if (boardSize === 0) return null;

      return (
        <>
          <mod.NeonGridOverlay theme={theme} />
          {captureSquare && (
            <mod.CaptureExplosion
              square={captureSquare}
              boardSize={boardSize}
              orientation={orientation}
              theme={theme}
              onDone={onCaptureDone}
            />
          )}
          {lastMove && (
            <mod.MoveTrail
              key={`${lastMove.from}-${lastMove.to}-${Date.now()}`}
              fromSquare={lastMove.from}
              toSquare={lastMove.to}
              boardSize={boardSize}
              orientation={orientation}
              theme={theme}
            />
          )}
          {isCheck && checkSquare && (
            <mod.CheckPulse
              key={`check-${checkSquare}`}
              square={checkSquare}
              boardSize={boardSize}
              orientation={orientation}
              theme={theme}
            />
          )}
          {showCheckmate && (
            <mod.CheckmateOverlayFX
              boardSize={boardSize}
              isWinner={isWinner}
              theme={theme}
            />
          )}
        </>
      );
    },
  }))
);

export const EffectsLayer: React.FC<EffectsLayerProps> = (props) => (
  <Suspense fallback={null}>
    <EffectsLayerInner {...props} />
  </Suspense>
);
