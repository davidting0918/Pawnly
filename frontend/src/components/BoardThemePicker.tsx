import React from 'react';
import { BOARD_THEMES, type BoardTheme } from '../themes/boardThemes';
import { Palette, Sparkles, X } from 'lucide-react';

interface Props {
  currentThemeId: string;
  onSelect: (theme: BoardTheme) => void;
  onClose: () => void;
}

const BoardThemePicker: React.FC<Props> = ({ currentThemeId, onSelect, onClose }) => {
  return (
    <div className="card">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold text-zinc-400 uppercase tracking-wider flex items-center gap-2">
          <Palette size={14} /> Board Theme
        </h3>
        <button onClick={onClose} className="text-zinc-500 hover:text-white transition-colors">
          <X size={16} />
        </button>
      </div>
      <div className="grid grid-cols-2 gap-2">
        {BOARD_THEMES.map((theme) => (
          <button
            key={theme.id}
            onClick={() => onSelect(theme)}
            className={`relative flex items-center gap-3 p-3 rounded-xl transition-all border-2 text-left ${
              currentThemeId === theme.id
                ? 'border-emerald-500/60 bg-emerald-500/10'
                : 'border-zinc-800 hover:border-zinc-600 bg-zinc-900/40'
            }`}
          >
            {/* Color preview squares */}
            <div className="flex-shrink-0 w-10 h-10 rounded-lg overflow-hidden grid grid-cols-2 grid-rows-2 border border-zinc-700/50">
              <div style={theme.lightSquare} />
              <div style={theme.darkSquare} />
              <div style={theme.darkSquare} />
              <div style={theme.lightSquare} />
            </div>
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-1.5">
                <span className="text-white text-sm font-semibold truncate">{theme.name}</span>
                {theme.experimental && (
                  <span className="flex items-center gap-0.5 text-[10px] font-bold text-cyan-400 bg-cyan-500/10 px-1.5 py-0.5 rounded-full">
                    <Sparkles size={8} /> FX
                  </span>
                )}
              </div>
              <p className="text-zinc-500 text-xs truncate">{theme.description}</p>
            </div>
          </button>
        ))}
      </div>
    </div>
  );
};

export default BoardThemePicker;
