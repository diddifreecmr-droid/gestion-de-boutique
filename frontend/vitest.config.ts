import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [react()],
  define: { __APP_VERSION__: JSON.stringify("0.0.0-test") },
  test: {
    environment: "jsdom",
    setupFiles: ["./tests/setup.ts"],
    include: ["src/**/*.test.{ts,tsx}", "config/**/*.test.ts", "tests/**/*.test.ts"],
    restoreMocks: true,
    coverage: {
      provider: "v8",
      include: ["src/**/*.{ts,tsx}"],
      exclude: [
        "src/**/*.test.{ts,tsx}",
        "src/main.tsx",
        "src/sw.ts",
        "src/vite-env.d.ts",
        "src/testing/**",
      ],
      reporter: ["text", "html"],
      thresholds: {
        "src/shared/**": { lines: 90, functions: 90, branches: 90, statements: 90 },
      },
    },
  },
});
