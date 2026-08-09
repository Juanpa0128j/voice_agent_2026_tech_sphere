/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        clinical: {
          blue: "#2563eb",
          green: "#16a34a",
          amber: "#d97706",
          red: "#dc2626",
        },
      },
    },
  },
  plugins: [],
};
