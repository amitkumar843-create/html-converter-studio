/** @type {import('tailwindcss').Config} */
export default {
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
      },
    },
  },
  plugins: [],
};
