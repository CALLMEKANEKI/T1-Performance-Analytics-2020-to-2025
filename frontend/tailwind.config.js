/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        bg: "#05050a",
        surface: "#1e1e2d",
        surfaceAlt: "#151521",
        surfaceHover: "#252538",
        border: "#2b2b40",
        accent: "#e3002b",
        accentMuted: "#7a0018",
        text: "#ffffff",
        textMuted: "#a1a5b7",
        win: "#22c55e",
        loss: "#b42318",
        blue: "#3b82f6",
        redSide: "#e3002b",
        amber: "#f59e0b",
        purple: "#a78bfa",
      },
      fontFamily: {
        display: ["Inter", "Arial", "sans-serif"],
        body: ["Inter", "Arial", "sans-serif"],
        mono: ["JetBrains Mono", "monospace"],
      },
    },
  },
  plugins: [],
};
