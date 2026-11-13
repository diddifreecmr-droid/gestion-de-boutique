/** Sections repliées du tableau de bord (audit UX du 13/11/2026) : les déplier dans un test. */
import { screen, within } from "@testing-library/react";
import type { UserEvent } from "@testing-library/user-event";

/** Bouton d'en-tête de la section repliable `title` (son nom commence par le titre). */
export async function sectionToggle(title: string): Promise<HTMLElement> {
  const heading = await screen.findByRole("heading", { level: 2, name: new RegExp(`^${title}`) });
  return within(heading).getByRole("button");
}

/**
 * Attend les chiffres, puis ouvre chaque section encore repliée (créances, stock, camions…),
 * comme le propriétaire qui les ouvre une à une.
 */
export async function unfoldSections(user: UserEvent): Promise<void> {
  await screen.findByRole("region", { name: "Chiffres clés" });
  for (const heading of screen.getAllByRole("heading", { level: 2 })) {
    const button = within(heading).queryByRole("button", { expanded: false });
    if (button !== null) await user.click(button);
  }
}
