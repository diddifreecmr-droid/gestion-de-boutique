import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach } from "vitest";

afterEach(() => {
  cleanup();
  // Modules gardés d'une boutique (src/core/profile/useShopModules.ts) : propres à chaque test.
  if (typeof window !== "undefined") window.localStorage.removeItem("boutique.shop-modules");
});
