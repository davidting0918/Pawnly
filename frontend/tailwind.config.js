/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'pawnly': {
          'bg':      '#1a1a1d',
          'surface': '#27272a',
          'card':    '#18181b',
          'border':  '#3f3f46',
          'green':   '#34d399',
          'accent':  '#10b981',
        },
        'board': {
          'dark':  '#779952',
          'light': '#e9edcc',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
    },
  },
  plugins: [],
}
