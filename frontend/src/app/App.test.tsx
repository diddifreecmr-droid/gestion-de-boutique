import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { createServices } from "../core/services/createServices";
import { createFakeFetch, NO_SESSION, ROUTES } from "../testing/fakeApi";
import { App } from "./App";

describe("App", () => {
  it("démarre avec le routeur du navigateur et mène à la connexion sans session", async () => {
    const fake = createFakeFetch({ [ROUTES.refresh]: NO_SESSION() });
    render(<App services={createServices({ base: "/api", fetch: fake.fetch })} />);
    expect(await screen.findByRole("heading", { level: 1, name: "Connexion" })).toBeVisible();
    expect(fake.count(ROUTES.refresh)).toBe(1);
  });

  it("refuse de démarrer sans VITE_API_BASE (fail-fast)", () => {
    expect(() => createServices({ base: "" })).toThrow("VITE_API_BASE est absent");
  });
});
