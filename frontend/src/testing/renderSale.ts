/**
 * Rendu de l'écran « Nouvelle vente » dans l'application complète, sur la **vraie** passerelle
 * et le faux serveur des ventes (tests seulement).
 */
import { screen, within } from "@testing-library/react";
import type userEvent from "@testing-library/user-event";
import { vi } from "vitest";
import { appGateways } from "../core/gateways/gateways";
import type { RecordSaleCommand } from "../core/gateways/salesContract";
import { formatMoney } from "../shared/format";
import { SHOP_A } from "./fakeApi";
import { PROFILE_KEY } from "../core/profile/savedProfiles";
import { renderApp } from "./renderApp";
import { servedProfile } from "./servedProfile";
import { saleServer, type Routes, type SaleRole } from "./salesServer";

export { SALE_SHOP } from "./salesServer";
export const NEW_SALE_PATH = `/s/${SHOP_A}/nouvelle-vente`;

/** Charge à l'avance les écrans chargés à la demande (sous couverture, l'import est lent). */
export async function preloadSales(): Promise<void> {
  await Promise.all([
    import("../features/sales/NewSaleRoute"),
    import("../features/sales/SalesRoute"),
    import("../features/sales/receipt/ReceiptView"),
  ]);
}

export interface RenderSaleOptions {
  online?: boolean;
  path?: string;
  /** Routes exactes qui remplacent celles du faux serveur. */
  extra?: Routes;
  /** Réglage « Accord du propriétaire sous le prix minimum » (faux par défaut, comme l'API). */
  priceApproval?: boolean;
}

export function renderSale(role: SaleRole = "seller", options: RenderSaleOptions = {}) {
  const { online = true, path = NEW_SALE_PATH, extra = {}, priceApproval = false } = options;
  const server = saleServer(role, extra);
  server.network.online = online;
  server.world.settings.minPriceRequiresApproval = priceApproval;
  // Hors connexion, la boutique a déjà été ouverte sur ce téléphone : son profil est gardé.
  if (!online) {
    window.localStorage.setItem(
      PROFILE_KEY,
      JSON.stringify({ [SHOP_A]: servedProfile("motos", role) }),
    );
  }
  const view = renderApp(path, server.routes);
  const gateways = appGateways(view.services);
  const requestPriceApproval = vi.spyOn(gateways.sales, "requestPriceApproval");
  return {
    ...view,
    server,
    network: server.network,
    gateways,
    recordSale: server.recordSale,
    requestPriceApproval,
  };
}

/** Corps du `index`-ième `POST /sales` reçu par le faux serveur. */
export function sentSale(recordSale: { mock: { calls: unknown[][] } }, index = 0) {
  const call = recordSale.mock.calls[index];
  if (call === undefined) throw new Error(`Aucune vente envoyée n° ${String(index)}`);
  return call[1] as RecordSaleCommand;
}

/** Compte les interactions de l'utilisateur (un geste = un appui ou une saisie). */
export function gestureCounter() {
  let count = 0;
  return {
    get count() {
      return count;
    },
    async run(action: () => Promise<void>) {
      count += 1;
      await action();
    },
  };
}

/** Article proposé dans la liste (plus vendus ou résultats). */
export async function articleButton(name: string): Promise<HTMLElement> {
  const list = await screen.findByRole("list", { name: /Les plus vendus|Articles trouvés/ });
  return within(list).getByRole("button", { name: new RegExp(name) });
}

export function priceField(label = "Prix"): HTMLInputElement {
  const field = screen.getByLabelText(label);
  if (!(field instanceof HTMLInputElement)) throw new Error(`« ${label} » n'est pas un champ`);
  return field;
}

/** Remplace tout le contenu d'un champ en une seule saisie (un geste). */
export async function replaceText(
  user: ReturnType<typeof userEvent.setup>,
  field: HTMLInputElement,
  text: string,
) {
  await user.type(field, text, {
    initialSelectionStart: 0,
    initialSelectionEnd: field.value.length,
  });
}

/** Message d'échec de l'écran (`role="alert"` dans la page, hors zone des toasts). */
export function saleAlert(): Promise<HTMLElement> {
  return within(screen.getByRole("main")).findByRole("alert");
}

export function validateButton(): HTMLElement {
  return screen.getByRole("button", { name: "Valider la vente" });
}

/** Montant tel que Testing Library le lit (espaces insécables normalisées en espaces). */
export function money(amount: number): string {
  return formatMoney(amount).replace(/\s/g, " ");
}

export function plain(text: string): string {
  return text.replace(/\s/g, " ");
}
