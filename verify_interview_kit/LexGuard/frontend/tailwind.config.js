/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        legal: {
          50: '#f0f4f8',
          100: '#d9e2ec',
          500: '#334e68',
          800: '#243b53',
          900: '#102a43',
        }
      }
    },
  },
  plugins: [],
}
