import { useId, type ReactNode } from "react";

/** Section de la vitrine : un titre (h2) par composant, puis ses états. */
export function GallerySection({ title, children }: { title: string; children: ReactNode }) {
  const id = useId();
  return (
    <section aria-labelledby={id} className="flex flex-col gap-4">
      <h2 id={id} className="m-0 text-title-sm font-semibold">
        {title}
      </h2>
      {children}
    </section>
  );
}

/** Sous-titre d'un état dans une section. */
export function StateLabel({ children }: { children: ReactNode }) {
  return <h3 className="m-0 text-label font-semibold text-text-muted">{children}</h3>;
}
