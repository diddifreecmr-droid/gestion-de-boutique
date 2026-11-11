import { useId } from "react";

export interface Fact {
  label: string;
  value: string;
}

/** Carte de lecture (design-system.md § 6.3) : titre de section et lignes « libellé — valeur ». */
export function FactsCard({ title, facts }: { title: string; facts: readonly Fact[] }) {
  const titleId = useId();
  return (
    <section
      aria-labelledby={titleId}
      className="flex flex-col gap-2 rounded-lg bg-surface p-4 shadow-card"
    >
      <h2 id={titleId} className="m-0 text-title-sm font-semibold text-text">
        {title}
      </h2>
      <dl className="m-0 flex flex-col gap-2">
        {facts.map((fact, index) => (
          <div
            key={`${fact.label}-${String(index)}`}
            className="flex items-baseline justify-between gap-4"
          >
            <dt className="text-body text-text-muted">{fact.label}</dt>
            <dd className="m-0 text-right text-lead tabular-nums text-text">{fact.value}</dd>
          </div>
        ))}
      </dl>
    </section>
  );
}
