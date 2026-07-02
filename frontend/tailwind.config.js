/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        bg: "#0A0A0F",
        surface: "#1A1A24",
        surfaceHover: "#22222E",
        border: "#2A2A38",
        accent: "#E0144C",
        accentMuted: "#7A0D2E",
        text: "#F5F3EE",
        textMuted: "#7C7C8A",
        win: "#34D399",
        loss: "#E0144C",
      },
      fontFamily: {
        display: ["Chakra Petch", "sans-serif"],
        body: ["Inter", "sans-serif"],
        mono: ["JetBrains Mono", "monospace"],
      },
    },
  },
  plugins: [],
};
