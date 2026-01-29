/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'pawnly-dark': '#262522',
        'pawnly-board': '#302E2B',
        'pawnly-green': '#81B64C',
      }
    },
  },
  plugins: [],
}
