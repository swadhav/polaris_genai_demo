/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        polaris: {
          blue: "#005CB9",
          darkblue: "#003b75",
          accent: "#0080FF",
          dark: "#0F141C",
          card: "#18202C",
          border: "#26354A",
          muted: "#8CA3BA",
        },
      },
    },
  },
  plugins: [],
}
