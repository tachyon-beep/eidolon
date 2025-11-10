/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{vue,js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Severity colors
        'severity-critical': '#DC2626',
        'severity-high': '#F59E0B',
        'severity-medium': '#10B981',
        'severity-low': '#3B82F6',
        // Status colors
        'status-queued': '#6B7280',
        'status-analyzing': '#6366F1',
        'status-complete': '#10B981',
        'status-failed': '#DC2626',
        // Background colors
        'bg-critical': '#FEE2E2',
        'bg-high': '#FEF3C7',
        'bg-medium': '#D1FAE5',
        'bg-low': '#DBEAFE',
        // UI colors
        'primary': '#7C3AED',
        'secondary': '#EC4899',
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'slide-in': 'slideIn 0.3s ease-out',
        'fade-in': 'fadeIn 0.2s ease-out',
      },
      keyframes: {
        slideIn: {
          '0%': { transform: 'translateX(-100%)', opacity: '0' },
          '100%': { transform: 'translateX(0)', opacity: '1' },
        },
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
      },
    },
  },
  plugins: [],
}
