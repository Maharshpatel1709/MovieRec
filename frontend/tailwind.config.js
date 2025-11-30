/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'cinema': {
          50: '#fef7ee',
          100: '#fcecd6',
          200: '#f8d5ac',
          300: '#f3b878',
          400: '#ed9042',
          500: '#e9731d',
          600: '#da5913',
          700: '#b54312',
          800: '#913617',
          900: '#752f16',
          950: '#3f1509',
        },
        'midnight': {
          50: '#f4f6fb',
          100: '#e8ecf6',
          200: '#cbd7eb',
          300: '#9eb4da',
          400: '#6a8cc4',
          500: '#476dae',
          600: '#365592',
          700: '#2d4577',
          800: '#283c63',
          900: '#1a2744',
          950: '#0f172a',
        }
      },
      fontFamily: {
        'display': ['Playfair Display', 'serif'],
        'sans': ['DM Sans', 'system-ui', 'sans-serif'],
      },
      animation: {
        'fade-in': 'fadeIn 0.5s ease-out',
        'slide-up': 'slideUp 0.5s ease-out',
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideUp: {
          '0%': { opacity: '0', transform: 'translateY(20px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
      },
      backgroundImage: {
        'gradient-radial': 'radial-gradient(var(--tw-gradient-stops))',
        'cinema-gradient': 'linear-gradient(135deg, #0f172a 0%, #1e293b 50%, #0f172a 100%)',
      }
    },
  },
  plugins: [],
}

