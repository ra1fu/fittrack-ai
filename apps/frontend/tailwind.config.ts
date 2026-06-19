import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#17211d",
        muted: "#69756f",
        canvas: "#f4f2ec",
        panel: "#ffffff",
        line: "#dedbd1",
        action: "#187454",
        coral: "#d65f43",
        amber: "#ad741d",
        mint: "#d9eadf",
        oat: "#ebe6da",
        steel: "#35443e",
      },
      boxShadow: {
        soft: "0 10px 30px rgba(31, 39, 36, 0.08)",
        lift: "0 18px 45px rgba(31, 39, 36, 0.12)",
      },
    },
  },
  plugins: [],
} satisfies Config;
