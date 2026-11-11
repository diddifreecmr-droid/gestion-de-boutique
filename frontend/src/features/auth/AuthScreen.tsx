import type { ReactNode } from "react";

/** Mise en page des écrans d'authentification : une colonne de 600 px au plus (§ 4.2). */
export function AuthScreen({
  title,
  intro,
  children,
}: {
  title: string;
  intro?: string;
  children: ReactNode;
}) {
  return (
    <main className="mx-auto flex w-full max-w-150 flex-col gap-5 p-4">
      <header className="flex flex-col gap-2">
        <p className="m-0 text-label font-semibold text-primary">Gestion de boutique</p>
        <h1 className="m-0 text-title font-bold text-text">{title}</h1>
        {intro !== undefined && <p className="m-0 text-body text-text-muted">{intro}</p>}
      </header>
      {children}
    </main>
  );
}
