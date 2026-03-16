import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        brand: { bg: "#0a0f1e", card: "#111827", border: "#1f2937", surface: "#1a2332", muted: "#6b7280" },
        primary: { DEFAULT: "#3b82f6", hover: "#2563eb", light: "#60a5fa", dark: "#1d4ed8" },
        profit: { DEFAULT: "#10b981", light: "#34d399", dark: "#059669" },
        loss: { DEFAULT: "#ef4444", light: "#f87171", dark: "#dc2626" },
        warning: { DEFAULT: "#f59e0b", light: "#fbbf24", dark: "#d97706" },
        score: { poor: "#ef4444", fair: "#f59e0b", good: "#3b82f6", excellent: "#10b981", outstanding: "#059669" },
      },
      fontFamily: { sans: ["Inter", "system-ui", "sans-serif"], mono: ["JetBrains Mono", "Fira Code", "monospace"] },
      animation: { "pulse-slow": "pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite", "slide-up": "slideUp 0.3s ease-out", "fade-in": "fadeIn 0.2s ease-out" },
      keyframes: {
        slideUp: { "0%": { transform: "translateY(10px)", opacity: "0" }, "100%": { transform: "translateY(0)", opacity: "1" } },
        fadeIn: { "0%": { opacity: "0" }, "100%": { opacity: "1" } },
      },
    },
  },
  plugins: [],
};

export default config;
