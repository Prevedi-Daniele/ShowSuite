/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        mac: {
          bg: '#18181b',
          surface: '#202024',
          subsurface: '#27272a',
          titlebar: '#1f1f23',
          border: '#38383e',
          text: '#f4f4f5',
          muted: '#a1a1aa',
          accent: '#0a84ff',
          hover: '#2e2e34',
          active: '#3a3a42'
        },
        qlab: {
          go: '#28cd41',
          stop: '#ff3b30',
          pause: '#ff9500',
          accent: '#ff9f0a',
          armed: '#007aff',
          broken: '#ff453a'
        },
        lightkey: {
          accent: '#0a84ff',
          dimmer: '#ffd60a',
          strobe: '#ffffff',
          live: '#30d158'
        }
      },
      fontFamily: {
        sans: [
          '-apple-system',
          'BlinkMacSystemFont',
          '"SF Pro Text"',
          '"Segoe UI"',
          'Roboto',
          'Helvetica',
          'Arial',
          'sans-serif'
        ],
        mono: [
          '"SF Mono"',
          'Menlo',
          'Monaco',
          'Consolas',
          '"Courier New"',
          'monospace'
        ]
      }
    },
  },
  plugins: [],
}
