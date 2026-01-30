/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'pawnly-dark': '#262522',     // Pawnly Dark BG
        'pawnly-board': '#302E2B',      // Pawnly Light BG
        'pawnly-green': '#81B64C',      // Chessboard Green
        'pawnly-light': '#E9EDCC',     // Chessboard Light
      },
      boxShadow: {
        '3d': '0 4px 8px rgba(0, 0, 0, 0.15), 0 2px 4px rgba(0, 0, 0, 0.1)',
        '3d-hover': '0 6px 12px rgba(0, 0, 0, 0.2), 0 3px 6px rgba(0, 0, 0, 0.15)',
        '3d-pressed': 'inset 0 2px 4px rgba(0, 0, 0, 0.2)',
      },
    },
  },
  plugins: [],
}
