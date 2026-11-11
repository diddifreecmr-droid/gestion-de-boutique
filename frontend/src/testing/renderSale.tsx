/** Rendu de l'écran « Nouvelle vente » sur la passerelle simulée (tests seulement). */
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";
import type { Role } from "../core/auth/me";
import { createSimulatedGateways } from "../core/gateways/gateways";
import { GatewaysProvider } from "../core/gateways/GatewaysProvider";
import { NewSalePage } from "../features/sales/NewSalePage";
import { formatMoney } from "../shared/format";

export const SALE_SHOP = "shop-garoua";

export interface SaleNetwork {
  online: boolean;
}

export function renderSale(role: Role = "seller", { online = true } = {}) {
  const user = userEvent.setup();
  const network: SaleNetwork = { online };
  const gateways = createSimulatedGateways({
    isOnline: () => network.online,
    roleIn: () => role,
  });
  const recordSale = vi.spyOn(gateways.sales, "recordSale");
  const requestPriceApproval = vi.spyOn(gateways.sales, "requestPriceApproval");
  const view = render(
    <GatewaysProvider gateways={gateways}>
      <main>
        <NewSalePage shopId={SALE_SHOP} role={role} />
      </main>
    </GatewaysProvider>,
  );
  return { ...view, user, network, gateways, recordSale, requestPriceApproval };
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
