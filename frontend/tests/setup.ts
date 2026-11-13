import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach } from "vitest";

afterEach(() => {
  cleanup();
  // Profils gardés des boutiques (src/core/profile/savedProfiles.ts) : propres à chaque test.
  if (typeof window !== "undefined") window.localStorage.removeItem("boutique.shop-profile");
});
