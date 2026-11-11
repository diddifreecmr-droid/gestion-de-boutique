import { screen, within } from "@testing-library/react";
import { beforeAll, beforeEach, describe, expect, it } from "vitest";
import { axeViolations } from "../../testing/axe";
import { json } from "../../testing/fakeApi";
import {
  LIST,
  listing,
  preloadReceivables,
  receivable,
  receivableRoutes,
  RECEIVABLES_PATH,
  route,
} from "../../testing/receivables";
import { renderApp } from "../../testing/renderApp";
import { money, plain } from "../../testing/renderSale";

beforeAll(preloadReceivables);
beforeEach(() => {
  window.localStorage.clear();
});

const LEGACY = receivable({
  id: "rec-old",
  customer: { id: "cust-old", name: "Garba Issa", phone: "+237690000002" },
  origin: "legacy",
  sale_id: null,
  sale_number: null,
  sale_total: null,
  paid_at_sale: 0,
  description: "1 moto Haojue, cahier 2026",
  initial_amount: 300000,
  total_paid: 300000,
  remaining: 0,
  status: "settled",
  last_installment_on: null,
  installments: [],
});

const list = () => screen.findByRole("list", { name: "Liste des créances" });

describe("Liste des créances (UC-CRE-04)", () => {
  it("propriétaire : trois chiffres du serveur, lignes complètes, reste en violet, pastilles", async () => {
    const { container, fake } = renderApp(RECEIVABLES_PATH, {
      ...receivableRoutes("owner"),
      [LIST]: json(200, listing([receivable(), LEGACY], { received_today: 150000 })),
    });
    const rows = within(await list()).getAllByRole("listitem");
    expect(rows).toHaveLength(2);
    const [first, second] = rows;
    if (first === undefined || second === undefined) throw new Error("deux lignes attendues");
    expect(plain(first.textContent)).toContain("Moussa Hamadou");
    expect(plain(first.textContent)).toContain("Vente V-000124");
    expect(plain(first.textContent)).toContain(`Initial ${money(800000)} · versé ${money(200000)}`);
    expect(plain(first.textContent)).toContain("Ouverte le 01/10/2026 (41 jours)");
    expect(plain(first.textContent)).toContain("dernier versement le 01/11/2026");
    expect(within(first).getByText(money(600000), { normalizer: plain })).toHaveClass(
      "text-credit-text",
    );
    expect(within(first).getByText("En cours")).toBeVisible();
    expect(within(second).getByText("Soldée")).toBeVisible();
    expect(plain(second.textContent)).toContain("1 moto Haojue, cahier 2026");
    expect(plain(second.textContent)).toContain("aucun versement");

    expect(screen.getByText("Total à recevoir")).toBeVisible();
    expect(plain(screen.getByText("Clients débiteurs").parentElement?.textContent ?? "")).toBe(
      "Clients débiteurs1 client",
    );
    expect(screen.getByText("Versements reçus aujourd'hui")).toBeVisible();
    expect(screen.getByRole("button", { name: "Créance ancienne" })).toBeVisible();
    expect(fake.count(route("GET", "/members"))).toBe(1);
    expect(await axeViolations(container)).toEqual([]);
  });

  it("filtres : statut, vendeur, ancienneté et suivi deviennent des paramètres d'API", async () => {
    const { user, fake } = renderApp(RECEIVABLES_PATH, {
      ...receivableRoutes("owner"),
      [route("GET", "/receivables?status=written_off")]: json(200, listing([])),
      [route(
        "GET",
        "/receivables?status=written_off&seller_id=01890a5d-ac96-774b-bcce-b302099a8002",
      )]: json(200, listing([])),
      [route(
        "GET",
        "/receivables?status=written_off&seller_id=01890a5d-ac96-774b-bcce-b302099a8002&band=over_90",
      )]: json(200, listing([])),
      [route(
        "GET",
        "/receivables?status=written_off&seller_id=01890a5d-ac96-774b-bcce-b302099a8002&band=over_90&quiet=true",
      )]: json(200, listing([])),
      [route(
        "GET",
        "/receivables?status=written_off&seller_id=01890a5d-ac96-774b-bcce-b302099a8002&band=over_90&reminder_overdue=true",
      )]: json(200, listing([])),
    });
    await list();
    await user.click(screen.getByRole("radio", { name: "En perte" }));
    expect(await screen.findByText("Aucune créance pour ces filtres.")).toBeVisible();
    await user.click(screen.getByRole("button", { name: "Filtres" }));
    await user.click(screen.getByRole("radio", { name: "Ibrahim Sali" }));
    await user.click(screen.getByRole("radio", { name: "Plus de 90 jours" }));
    await user.click(screen.getByRole("radio", { name: "Sans versement depuis 30 jours" }));
    await user.click(screen.getByRole("radio", { name: "Rappel dépassé" }));
    await screen.findByText("Aucune créance pour ces filtres.");
    const urls = fake.calls.map((call) => call.url).filter((url) => url.includes("/receivables"));
    expect(urls.at(-1)).toMatch(/reminder_overdue=true$/);
    expect(urls.some((url) => url.endsWith("quiet=true"))).toBe(true);
  });

  it("vendeur : ses créances seulement, sans filtre vendeur ni créance ancienne ; 360 px", async () => {
    const { container, fake, user } = renderApp(RECEIVABLES_PATH, receivableRoutes("seller"));
    await list();
    expect(screen.queryByRole("button", { name: "Créance ancienne" })).toBeNull();
    await user.click(screen.getByRole("button", { name: "Filtres" }));
    expect(screen.queryByRole("radiogroup", { name: "Vendeur" })).toBeNull();
    expect(fake.count(route("GET", "/members"))).toBe(0);
    expect(container.querySelector("table")).toBeNull();
    expect(container.innerHTML).not.toMatch(/overflow-x|w-max|min-w-max|w-screen/);
    expect(await axeViolations(container)).toEqual([]);
  });

  it("hors connexion : la liste le dit", async () => {
    renderApp(RECEIVABLES_PATH, {
      ...receivableRoutes("owner"),
      [LIST]: new TypeError("Failed to fetch"),
    });
    expect(
      await screen.findByText("Connexion nécessaire pour afficher les créances."),
    ).toBeVisible();
  });

  it.each(["accountant", "driver"] as const)(
    "%s : aucun accès, « Page introuvable », aucun appel aux créances",
    async (role) => {
      const { fake } = renderApp(RECEIVABLES_PATH, receivableRoutes(role));
      expect(await screen.findByRole("heading", { name: "Page introuvable" })).toBeVisible();
      expect(fake.calls.some((call) => call.url.includes("/receivables"))).toBe(false);
    },
  );
});
