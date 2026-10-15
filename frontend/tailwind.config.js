/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ["Inter", "ui-sans-serif", "system-ui", "sans-serif"],
      },
      colors: {
        ink: "#1D2144",
        mute: "#6C7194",
        brand: {
          DEFAULT: "#6E79E6",
          dark: "#5A64D6",
          deep: "#4546A0",
          tint: "#EEF0FE",
        },
        canvas: "#E8EAFB",
      },
      borderRadius: {
        card: "26px",
        chip: "15px",
        pill: "999px",
      },
      boxShadow: {
        card: "0 1px 2px rgba(29,33,68,.04), 0 18px 40px -18px rgba(69,70,160,.22)",
        chip: "0 1px 2px rgba(29,33,68,.05)",
        lift: "0 2px 6px rgba(29,33,68,.05), 0 30px 60px -26px rgba(69,70,160,.34)",
        glow: "0 0 0 1px rgba(255,255,255,.6), 0 24px 60px -24px rgba(110,121,230,.55)",
      },
      keyframes: {
        spinslow: { to: { transform: "rotate(360deg)" } },
        float: {
          "0%,100%": { transform: "translateY(0)" },
          "50%": { transform: "translateY(-12px)" },
        },
      },
      animation: {
        spinslow: "spinslow 26s linear infinite",
        float: "float 9s ease-in-out infinite",
      },
    },
  },
  plugins: [],
};
