import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    setupFiles: ["./tests/setup.ts"],
    include: ["src/**/*.test.{ts,tsx}", "config/**/*.test.ts", "tests/**/*.test.ts"],
    restoreMocks: true,
    coverage: {
      provider: "v8",
      include: ["src/**/*.{ts,tsx}"],
      exclude: ["src/**/*.test.{ts,tsx}", "src/main.tsx", "src/sw.ts", "src/vite-env.d.ts"],
      reporter: ["text", "html"],
      thresholds: {
        "src/shared/**": { lines: 90, functions: 90, branches: 90, statements: 90 },
      },
    },
  },
});
