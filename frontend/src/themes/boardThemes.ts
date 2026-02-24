import type { CSSProperties } from 'react';

export interface BoardTheme {
  id: string;
  name: string;
  description: string;
  preview: string; // emoji or icon
  darkSquare: CSSProperties;
  lightSquare: CSSProperties;
  boardBorder?: string; // tailwind border class
  effects: boolean; // whether to show tsParticles/framer-motion effects
  experimental?: boolean; // tag it as experimental
}

export const BOARD_THEMES: BoardTheme[] = [
  {
    id: 'classic',
    name: 'Classic',
    description: 'Traditional green & cream',
    preview: '🌿',
    darkSquare: { backgroundColor: '#779952' },
    lightSquare: { backgroundColor: '#e9edcc' },
    boardBorder: 'border-zinc-800',
    effects: false,
  },
  {
    id: 'wood',
    name: 'Wood',
    description: 'Warm wooden tones',
    preview: '🪵',
    darkSquare: { backgroundColor: '#a97a56' },
    lightSquare: { backgroundColor: '#d2b48c' },
    boardBorder: 'border-amber-900/50',
    effects: false,
  },
  {
    id: 'ocean',
    name: 'Ocean',
    description: 'Deep blue sea',
    preview: '🌊',
    darkSquare: { backgroundColor: '#2563eb' },
    lightSquare: { backgroundColor: '#93c5fd' },
    boardBorder: 'border-blue-900/50',
    effects: false,
  },
  {
    id: 'midnight',
    name: 'Midnight',
    description: 'Dark purple elegance',
    preview: '🌙',
    darkSquare: { backgroundColor: '#4c1d95' },
    lightSquare: { backgroundColor: '#a78bfa' },
    boardBorder: 'border-purple-900/50',
    effects: false,
  },
  {
    id: 'neon',
    name: 'Neon Cyber',
    description: 'Sci-fi neon with particle effects',
    preview: '⚡',
    darkSquare: { backgroundColor: '#0f172a' },
    lightSquare: { backgroundColor: '#1e293b' },
    boardBorder: 'border-cyan-500/40',
    effects: true,
    experimental: true,
  },
  {
    id: 'plasma',
    name: 'Plasma Core',
    description: 'Energy plasma with explosions',
    preview: '🔮',
    darkSquare: { backgroundColor: '#1a0a2e' },
    lightSquare: { backgroundColor: '#2d1b4e' },
    boardBorder: 'border-fuchsia-500/40',
    effects: true,
    experimental: true,
  },
];

export const DEFAULT_THEME_ID = 'classic';

export function getThemeById(id: string): BoardTheme {
  return BOARD_THEMES.find((t) => t.id === id) || BOARD_THEMES[0];
}

// localStorage key
const STORAGE_KEY = 'pawnly_board_theme';

export function getSavedThemeId(): string {
  try {
    return localStorage.getItem(STORAGE_KEY) || DEFAULT_THEME_ID;
  } catch {
    return DEFAULT_THEME_ID;
  }
}

export function saveThemeId(id: string): void {
  try {
    localStorage.setItem(STORAGE_KEY, id);
  } catch {
    // ignore
  }
}
