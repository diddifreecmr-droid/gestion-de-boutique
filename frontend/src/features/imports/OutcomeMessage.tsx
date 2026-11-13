import type { CancelOutcome } from "./CancelImport";

/** Issue d'une annulation d'import : message, et opérations qui bloquent s'il y en a. */
export function OutcomeMessage({ outcome }: { outcome: CancelOutcome }) {
  const tone = outcome.tone === "success" ? "text-success-text" : "text-danger-text";
  return (
    <div className={`flex flex-col gap-1 text-body ${tone}`}>
      <p className="m-0">{outcome.text}</p>
      {outcome.blocking.length > 0 && (
        <ul aria-label="Opérations qui bloquent" className="m-0 pl-6">
          {outcome.blocking.map((text) => (
            <li key={text}>{text}</li>
          ))}
        </ul>
      )}
    </div>
  );
}
