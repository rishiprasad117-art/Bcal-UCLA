/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        // UCLA official palette
        'ucla-blue':       '#2774AE',
        'ucla-blue-dark':  '#003B5C',
        'ucla-blue-light': '#8BB8E8',
        'ucla-gold':       '#FFD100',
        'ucla-gold-dark':  '#FFB81C',
      },
    },
  },
  plugins: [],
}
