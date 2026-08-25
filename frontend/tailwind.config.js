/** @type {import('tailwindcss').Config} */
export default {
  darkMode: "class",
  content: [
    "./index.html",
    "./src/**/*.{js,jsx,ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        appBg: "#0F172A",
        appBg2: "#020617",
        appCard: "#111827",
        appCardSoft: "#1E293B",
        appBorder: "#334155",
        appText: "#F8FAFC",
        appMuted: "#CBD5E1",
        primary: "#6366F1",
        primarySoft: "#818CF8",
        secondary: "#8B5CF6",
        accent: "#22D3EE",
        success: "#10B981",
        warning: "#F59E0B",
        danger: "#EF4444",
      },
      fontFamily: {
        sans: ["Inter", "Aptos", "Segoe UI", "Arial", "sans-serif"],
      },
      boxShadow: {
        glow: "0 0 40px rgba(99,102,241,0.25)",
        soft: "0 24px 80px rgba(15,23,42,0.45)",
        magic: "0 0 20px rgba(99,102,241,0.1), inset 0 0 20px rgba(99,102,241,0.05)",
      },
      keyframes: {
        "fade-in-up": {
          "0%": { opacity: 0, transform: "translateY(20px)" },
          "100%": { opacity: 1, transform: "translateY(0)" },
        },
        "fade-in": {
          "0%": { opacity: 0 },
          "100%": { opacity: 1 },
        },
        "float": {
          "0%, 100%": { transform: "translateY(0)" },
          "50%": { transform: "translateY(-5px)" },
        },
        "shimmer": {
          from: { backgroundPosition: "0 0" },
          to: { backgroundPosition: "-200% 0" },
        },
        "pulse-glow": {
          "0%, 100%": { opacity: 1, filter: "brightness(100%)" },
          "50%": { opacity: 0.85, filter: "brightness(120%) drop-shadow(0 0 8px rgba(99,102,241,0.4))" },
        },
        "meteor": {
          "0%": { transform: "rotate(215deg) translateX(0)", opacity: 1 },
          "70%": { opacity: 1 },
          "100%": { transform: "rotate(215deg) translateX(-500px)", opacity: 0 },
        },
        "magic-border": {
          "0%": { backgroundPosition: "0% 50%" },
          "50%": { backgroundPosition: "100% 50%" },
          "100%": { backgroundPosition: "0% 50%" },
        }
      },
      animation: {
        "fade-in-up": "fade-in-up 0.5s ease-out forwards",
        "fade-in": "fade-in 0.4s ease-out forwards",
        "float": "float 4s ease-in-out infinite",
        "shimmer": "shimmer 2s linear infinite",
        "pulse-glow": "pulse-glow 3s ease-in-out infinite",
        "meteor": "meteor 5s linear infinite",
        "magic-border": "magic-border 3s ease infinite",
      },
    },
  },
  plugins: [],
};
