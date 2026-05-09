import type { Config } from 'tailwindcss'

const config: Config = {
  content: ['./app/**/*.{ts,tsx}', './components/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        obsidian: '#0A0A0A', gold: '#C9A84C', 'gold-light': '#E8C97A', slate: '#1E293B', 'slate-light': '#2D3F55', offwhite: '#F8F6F1'
      },
      fontFamily: { display: ['Cormorant Garamond'], body: ['IBM Plex Sans'], arabic: ['Cairo'], data: ['IBM Plex Mono'] }
    },
  },
  plugins: [],
}
export default config
