import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { App } from "./App";

describe("App", () => {
  it("démarre sur l'accueil avec le routeur du navigateur", () => {
    render(<App />);
    expect(screen.getByRole("heading", { level: 1, name: "Gestion de boutique" })).toBeVisible();
  });
});
