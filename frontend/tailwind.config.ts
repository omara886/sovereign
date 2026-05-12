import type { Config } from 'tailwindcss'

const config: Config = {
  content: ['./app/**/*.{ts,tsx}', './components/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        // Light theme tokens
        bg:       '#FAFAFA',
        surface:  '#FFFFFF',
        border:   '#E5E7EB',
        'border-strong': '#D1D5DB',
        // Text
        primary:  '#111827',
        secondary:'#374151',
        muted:    '#6B7280',
        disabled: '#9CA3AF',
        // Accent
        indigo:   '#4F46E5',
        'indigo-hover': '#4338CA',
        'indigo-soft':  'rgba(79,70,229,0.08)',
        // Semantic
        success:  '#10B981',
        warning:  '#F59E0B',
        danger:   '#EF4444',
        // Project accents
        therapia:     '#4C1D95',
        qawwi:        '#1D4ED8',
        productbench: '#0F766E',
        sahmalgo:     '#B45309',
        // Legacy (keep for gradual migration)
        obsidian: '#0A0A0A',
        gold:     '#C9A84C',
        'gold-light': '#E8C97A',
        slate:    '#1E293B',
        offwhite: '#F8F6F1',
      },
      fontFamily: {
        sans:    ['Inter', 'system-ui', 'sans-serif'],
        arabic:  ['Noto Sans Arabic', 'sans-serif'],
        mono:    ['IBM Plex Mono', 'monospace'],
        display: ['Inter', 'sans-serif'],
      },
      boxShadow: {
        xs:    '0 1px 2px rgba(0,0,0,0.05)',
        card:  '0 1px 3px rgba(0,0,0,0.08), 0 1px 2px rgba(0,0,0,0.06)',
      },
      borderRadius: {
        sm: '6px',
        md: '8px',
        lg: '10px',
        xl: '12px',
        '2xl': '16px',
      },
    },
  },
  plugins: [],
}
export default config
