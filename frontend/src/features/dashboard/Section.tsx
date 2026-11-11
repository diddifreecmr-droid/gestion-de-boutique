import { useId, type ReactNode } from "react";

/** Bloc titré de l'accueil (« Créances », « Stock »…) : titre de section relié à la région. */
export function Section({ title, children }: { title: string; children: ReactNode }) {
  const id = useId();
  return (
    <section aria-labelledby={id} className="flex flex-col gap-2">
      <h2 id={id} className="m-0 text-title-sm font-semibold text-text">
        {title}
      </h2>
      {children}
    </section>
  );
}
